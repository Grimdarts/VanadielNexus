"""What each GearSwap set needs and whether this character can wear it. Qt-free.

Reading half (slice 1, commit 1): bag rules, augment matching as GearSwap does it, the per-set allocation of
owned copies to slots, and the purpose of each set. See docs/SET-MANAGER-ENG-REVIEW.md section 5.
"""
import re
from collections import Counter
from dataclasses import dataclass, field

from . import item_res
from .gear_guides import PURPOSES, RANK_RE, identity
from .gearswap_reader import SLOT_ORDER, JobRead, Piece, SetRead
from .item_res import bag_key

# Bags GearSwap can equip from (res/bags.lua equippable=true), as bag_keys.
REACHABLE_BAGS = frozenset({'inventory', 'wardrobe'} | {f'wardrobe{n}' for n in range(2, 9)})
SNAPSHOT_STATES = ('absent', 'empty', 'ok')
SLOT_LABELS = {'main': 'Main', 'sub': 'Sub', 'range': 'Range', 'ammo': 'Ammo', 'head': 'Head', 'neck': 'Neck',
               'ear1': 'Ear 1', 'ear2': 'Ear 2', 'body': 'Body', 'hands': 'Hands', 'ring1': 'Ring 1',
               'ring2': 'Ring 2', 'back': 'Back', 'waist': 'Waist', 'legs': 'Legs', 'feet': 'Feet'}
OTHER = 'Other'


def reachable(bag: str) -> bool:
    return bag_key(bag) in REACHABLE_BAGS


def on_slip(bag: str) -> bool:
    return bag_key(bag).startswith('storageslip')


def snapshot_state(snapshot: dict, character: str) -> str:
    """'absent' (character never logged in with the addon), 'empty' (no rows), or 'ok'."""
    for key, rows in (snapshot or {}).items():
        if not key.startswith('Imported: ') and key.casefold() == (character or '').casefold():
            return 'ok' if rows else 'empty'
    return 'absent'


# ---------------------------------------------------------------- augments

def split_augments(augments) -> list[str]:
    """Snapshot rows join augments with ", "; sets hold lists. Synthetic "Rank N" parts are dropped."""
    if isinstance(augments, str):
        parts = [part.strip() for part in augments.split(', ')] if augments.strip() else []
    else:
        parts = [str(part) for part in augments or []]
    return [part for part in parts if part and part != 'none' and not RANK_RE.fullmatch(part.strip())]


def augment_key(augments) -> frozenset:
    """Groups identical copies (never decides a match): identity per part, "Rank N" dropped, Path kept."""
    return frozenset(identity(part).replace('“', "'").replace('”', "'").replace('"', "'")
                     for part in split_augments(augments))


def _aug_strip(text: str) -> str:
    """extdata.compare_augments: str:lower():gsub('[^%-%w,]', '')."""
    return re.sub(r'[^A-Za-z0-9,\-]', '', text.lower())


def equip_match(goal, copy_augments, rare: bool = False) -> bool:
    """Would GearSwap equip this copy for a piece asking for `goal` augments?

    Mirrors extdata.compare_augments (addons/libs/extdata.lua:2262): every goal augment must be found in the
    copy (duplicates consumed), compared lowercased with everything but letters, digits, '-' and ',' removed.
    An empty goal matches any copy, and Rare items always match (equip_processing.lua:158).
    """
    goal = [g for g in split_augments(goal)]
    if not goal or rare:
        return True
    current = [_aug_strip(part) for part in split_augments(copy_augments)]
    if len(current) < len(goal):
        return False
    for part in goal:
        stripped = _aug_strip(part)
        if stripped not in current:
            return False
        current.remove(stripped)
    return True


# ---------------------------------------------------------------- game data per read

@dataclass
class GameData:
    """The res lookups one Sets-page read needs (parent process only)."""
    items: dict
    by_name: dict
    job_ids: dict      # 'BLU' -> 16
    bag_names: dict    # bag_key -> GearSwap name

    @classmethod
    def load(cls, windower_dir: str) -> 'GameData':
        return cls(item_res.items(windower_dir), item_res.by_name(windower_dir),
                   {short: value[0] for short, value in item_res.jobs(windower_dir).items()},
                   item_res.bags(windower_dir))


def resolve(piece: Piece, game: GameData, job: str) -> tuple[list[int], str]:
    """(ids GearSwap would accept for this slot and job, problem). problem is '' when at least one id fits
    and the job can wear it; else 'unknown' (not in game data), 'wrong_slot' or 'not_wearable'."""
    ids = game.by_name.get(piece.name.casefold(), [])
    if not ids:
        return [], 'unknown'
    fitting = [i for i in ids if item_res.fits(game.items[i], piece.slot)]
    if not fitting:
        return [], 'wrong_slot'
    job_id = game.job_ids.get(job)
    wearable = [i for i in fitting if job_id is None or item_res.wearable(game.items[i], job_id)]
    if not wearable:
        return fitting, 'not_wearable'
    return wearable, ''


# ---------------------------------------------------------------- allocation

@dataclass
class SlotStatus:
    kind: str                     # owned unreachable missing other_character unknown no_snapshot empty not_set
    bag: str = ''                 # the bag of the copy taken
    detail: str = ''              # the caption word: "Mog Safe 1", "only 1 owned", "On Aynon"...
    row: dict | None = None       # the snapshot row taken
    note: str = ''                # requirements GearSwap checks that the app can't: race, superior level
    piece: Piece | None = None


ATTENTION = ('unreachable', 'missing', 'other_character', 'unknown')


def _units(rows):
    for row in rows:
        try:
            count = max(1, int(row.get('count', 1) or 1))
        except (TypeError, ValueError):
            count = 1
        for _ in range(count):
            yield row


def _matching(units, piece, ids, game, ignore_bag=False):
    wanted = set(ids)
    designated = bag_key(piece.bag) if piece.bag and not ignore_bag else ''
    rare = any(game.items[i].rare for i in ids if i in game.items)
    return [index for index, row in units
            if row.get('item_id') in wanted
            and (not designated or bag_key(row.get('bag', '')) == designated)
            and equip_match(piece.augments, row.get('augments', ''), rare)]


def _kuhn(slots, candidates):
    """Maximum bipartite matching slot → unit, trying candidates in the order given (augmenting paths)."""
    owner = {}

    def augment(slot, seen):
        for unit in candidates[slot]:
            if unit in seen:
                continue
            seen.add(unit)
            if unit not in owner or augment(owner[unit], seen):
                owner[unit] = slot
                return True
        return False

    for slot in slots:
        augment(slot, set())
    return {slot: unit for unit, slot in owner.items()}


def _requirements_note(item_ids, game) -> str:
    notes = []
    items = [game.items[i] for i in item_ids if i in game.items]
    if items and all(item_res.race_limited(item) for item in items):
        notes.append('race-limited: check your race')
    levels = [item.superior_level for item in items if item.superior_level]
    if items and len(levels) == len(items):
        notes.append(f'needs superior level {min(levels)}')
    return ' · '.join(notes)


def allocate(set_read: SetRead, rows_char: list, rows_all: list, game: GameData, job: str,
             state: str, character: str = '') -> dict[str, SlotStatus]:
    """One status per slot in SLOT_ORDER. Each owned copy serves at most one slot of this set.

    Copies are matched to slots as a maximum matching (D20): first among reachable bags (what GearSwap can
    equip), then the remaining slots among stored copies. Within each, plain copies are tried first for pieces
    that name no augments, then copies by bag name.
    """
    result = {}
    needs = {}
    for slot in SLOT_ORDER:
        piece = set_read.pieces.get(slot)
        if piece is None:
            result[slot] = SlotStatus('not_set')
        elif piece.empty:
            result[slot] = SlotStatus('empty', piece=piece)
        elif state == 'absent':
            result[slot] = SlotStatus('no_snapshot', detail='No snapshot', piece=piece)
        else:
            ids, problem = resolve(piece, game, job)
            if problem == 'unknown':
                result[slot] = SlotStatus('unknown', detail='Unknown item', piece=piece)
            elif problem == 'wrong_slot':
                result[slot] = SlotStatus('unknown', detail='Wrong slot', piece=piece)
            elif problem == 'not_wearable':
                result[slot] = SlotStatus('missing', detail=f"{job} can't wear this", piece=piece)
            else:
                needs[slot] = (piece, ids)

    units = list(enumerate(_units(rows_char)))
    candidates = {slot: _matching(units, piece, ids, game) for slot, (piece, ids) in needs.items()}

    def ordered(slot, pool):
        plain_first = not needs[slot][0].augments

        def preference(unit):
            row = units[unit][1]
            augmented = plain_first and bool(split_augments(row.get('augments', '')))
            return augmented, bag_key(row.get('bag', '')), unit
        return sorted((u for u in candidates[slot] if u in pool), key=preference)

    reachable_units = {u for u, row in units if reachable(row.get('bag', ''))}
    taken = _kuhn(list(needs), {slot: ordered(slot, reachable_units) for slot in needs})
    stored_units = {u for u, _ in units} - reachable_units
    rest = [slot for slot in needs if slot not in taken]
    taken.update(_kuhn(rest, {slot: ordered(slot, stored_units) for slot in rest}))

    for slot, (piece, ids) in needs.items():
        if slot in taken:
            row = units[taken[slot]][1]
            bag = row.get('bag', '')
            if reachable(bag):
                result[slot] = SlotStatus('owned', bag, bag, row, _requirements_note([row.get('item_id')], game), piece)
            else:
                detail = 'on a slip' if on_slip(bag) else bag
                result[slot] = SlotStatus('unreachable', bag, detail, row, '', piece)
            continue
        own = identity(character or (rows_char[0].get('character') if rows_char else ''))
        rare = any(game.items[i].rare for i in ids if i in game.items)
        others = [row for row in rows_all
                  if identity(row.get('character')) != own and row.get('item_id') in set(ids)
                  and equip_match(piece.augments, row.get('augments', ''), rare)]
        if others:
            result[slot] = SlotStatus('other_character', detail=f"On {others[0].get('character', '?')}", piece=piece)
            continue
        copies = len(candidates[slot])
        if copies:
            detail = f'only {copies} owned'
        elif _matching(units, piece, ids, game, ignore_bag=True):
            detail = f'not in {piece.bag}'
        elif [u for u, row in units if row.get('item_id') in set(ids)]:
            detail = 'augments differ'
        else:
            detail = 'Not owned'
        result[slot] = SlotStatus('missing', detail=detail, piece=piece)
    return result


def attention_count(statuses: dict) -> int:
    return sum(1 for status in statuses.values() if status.kind in ATTENTION)


# ---------------------------------------------------------------- purposes

_SHORT_WORD_SPLIT = re.compile(r'[^a-z0-9]+')
RULES = (
    ('Weapon skill', {'ws'}, {'weaponskill'}, set(), 'ws'),
    ('Job ability', {'ja'}, {'jobability', 'buff'}, set(), 'ja'),
    ('Idle', set(), {'idle', 'perp', 'town', 'kite'}, set(), None),
    ('Pet', set(), {'pet', 'pact', 'avatar', 'ready', 'spirit'}, set(), None),
    ('Precast', {'fc'}, {'precast', 'fastcast'}, set(), None),
    ('Defense', {'dt', 'pdt', 'mdt', 'meva'}, {'defense', 'damagetaken'}, set(), None),
    ('Melee / TP', {'tp'}, {'engaged', 'melee'}, set(), None),
    ('Ranged', set(), {'ranged', 'snapshot'}, {'ra'}, None),
    ('Midcast: blue magic', set(), {'bluemagic'}, set(), None),
    ('Midcast: ninjutsu', set(), {'ninjutsu', 'utsusemi'}, set(), None),
    ('Midcast: healing', set(), {'cure', 'cura', 'healing', 'waltz'}, set(), None),
    ('Midcast: enhancing', set(), {'enhancing'}, set(), None),
    ('Midcast: enfeebling', set(), {'enfeebl'}, set(), None),
    ('Midcast: nuking', {'mab'}, {'nuke', 'elemental', 'magical', 'burst'}, set(), None),
)
# Long tokens that count only when some key in the path contains "midcast".
GATED_LONG = {'Midcast: enhancing': {'refresh', 'regen', 'haste', 'phalanx', 'stoneskin', 'aquaveil', 'protect',
                                     'shell', 'storm', 'barspell'},
              'Midcast: enfeebling': {'slow', 'paralyze', 'silence', 'sleep', 'dispel'}}


def key_words(key) -> list[str]:
    """`OneHandedTP` → ['one', 'handed', 'tp']; `DTRefresh` → ['dt', 'refresh']."""
    text = str(key)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
    text = re.sub(r'(\d+)', r' \1 ', text)
    return [word for word in _SHORT_WORD_SPLIT.split(text.casefold()) if word]


def joined_key(key) -> str:
    return re.sub(r'[^0-9a-z]', '', str(key).casefold())


def classify(path_keys, ws_names=frozenset(), ja_names=frozenset()) -> str:
    """The purpose of a set from its path keys (rules in order, first match wins)."""
    keys = [k for k in path_keys if isinstance(k, str)]
    words = [set(key_words(k)) for k in keys]
    joined = [joined_key(k) for k in keys]
    midcast = any('midcast' in j for j in joined)
    for purpose, short, long, gated_short, names in RULES:
        if any(short & w for w in words):
            return purpose
        if midcast and any(gated_short & w for w in words):
            return purpose
        tokens = long | (GATED_LONG.get(purpose, set()) if midcast else set())
        if any(token in j for token in tokens for j in joined):
            return purpose
        lookup = ws_names if names == 'ws' else ja_names if names == 'ja' else ()
        if lookup and any(j in lookup for j in joined):
            return purpose
    return OTHER


PURPOSE_ORDER = [p for p in PURPOSES if p != 'Gear reference'] + [OTHER]


# ---------------------------------------------------------------- the page's view of a read

@dataclass
class SetView:
    set_read: SetRead
    purpose: str
    statuses: dict[str, SlotStatus] = field(default_factory=dict)

    @property
    def attention(self) -> int:
        return attention_count(self.statuses)

    @property
    def filled(self) -> int:
        return sum(1 for status in self.statuses.values() if status.kind != 'not_set')


def build_views(job_read: JobRead, snapshot: dict, windower_dir: str, ws_names=None, ja_names=None) -> list[SetView]:
    """Statuses and purposes for every set in a read, against the inventory snapshot (no Lua runs here)."""
    game = GameData.load(windower_dir)
    ws_names = item_res.ws_names(windower_dir) if ws_names is None else ws_names
    ja_names = item_res.ja_names(windower_dir) if ja_names is None else ja_names
    state = snapshot_state(snapshot, job_read.character)
    rows_char = []
    rows_all = []
    for key, rows in (snapshot or {}).items():
        if key.startswith('Imported: '):
            continue
        for row in rows or []:
            row = {**row, 'character': row.get('character') or key}
            rows_all.append(row)
            if key.casefold() == job_read.character.casefold():
                rows_char.append(row)
    return [SetView(s, classify(s.keys, ws_names, ja_names),
                    allocate(s, rows_char, rows_all, game, job_read.job, state, job_read.character))
            for s in job_read.sets]


def summary_counts(views) -> Counter:
    return Counter(view.purpose for view in views)
