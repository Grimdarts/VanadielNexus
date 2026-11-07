"""What each GearSwap set needs and whether this character can wear it. Qt-free.

Bag rules, augment matching as GearSwap does it, per-set allocation, purposes, tier upgrades and copy-paste
fix plans. See docs/SET-MANAGER-ENG-REVIEW.md section 5. No function here writes a player's Lua.
"""
import re
from pathlib import Path
from collections import Counter
from dataclasses import dataclass, field, replace

from . import item_res
from .gear_guides import PURPOSES
from .equipment_matching import (identity, split_augments, augment_key, equip_match,
                                 units as _units, maximum_matching as _kuhn)
from .gearswap_reader import SLOT_ORDER, JobRead, Piece, SetRead, normalise_path, strip_comments
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


def _matching(units, piece, ids, game, ignore_bag=False):
    wanted = set(ids)
    designated = bag_key(piece.bag) if piece.bag and not ignore_bag else ''
    rare = any(game.items[i].rare for i in ids if i in game.items)
    return [index for index, row in units
            if row.get('item_id') in wanted
            and (not designated or bag_key(row.get('bag', '')) == designated)
            and equip_match(piece.augments, row.get('augments', ''), rare)]


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
    upgrades: dict[str, list] = field(default_factory=dict)

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
    families = {}
    for row in rows_char:
        item = game.items.get(row.get('item_id'))
        if item is not None:
            families.setdefault(_tier(item.en)[0], []).append(row)
    upgrade_cache = {}

    def upgrades(piece):
        key = piece.name.casefold(), piece.slot
        if key not in upgrade_cache:
            upgrade_cache[key] = tier_upgrades(piece, game, rows_char, game.job_ids.get(job_read.job), _families=families)
        return upgrade_cache[key]

    return [SetView(s, classify(s.keys, ws_names, ja_names),
                    allocate(s, rows_char, rows_all, game, job_read.job, state, job_read.character),
                    {slot: upgrades(piece)
                     for slot, piece in s.pieces.items() if not piece.empty})
            for s in job_read.sets]


def summary_counts(views) -> Counter:
    return Counter(view.purpose for view in views)


# ---------------------------------------------------------------- copy-paste fixes (never writes Lua)

def _tier(name):
    match = re.search(r'\s\+(\d+)$', name)
    return identity(name[:match.start()] if match else name), int(match[1]) if match else 0


def tier_upgrades(piece: Piece, game: GameData, rows_char: list, job_id: int | None, *, _families=None) -> list:
    ids, problem = resolve(piece, game, next((j for j, i in game.job_ids.items() if i == job_id), ''))
    if piece.empty or problem:
        return []
    families = {_tier(game.items[i].en) for i in ids}
    result = []
    pool = rows_char if _families is None else [row for base in {base for base, _tier_number in families}
                                               for row in _families.get(base, [])]
    for row in pool:
        item = game.items.get(row.get('item_id'))
        if item is None or not item_res.fits(item, piece.slot) or (job_id is not None and not item_res.wearable(item, job_id)):
            continue
        base, tier = _tier(item.en)
        if any(base == old_base and tier > old_tier for old_base, old_tier in families):
            result.append(row)
    return sorted(result, key=lambda r: (-_tier(game.items[r['item_id']].en)[1],
                                         not reachable(r.get('bag', '')), bag_key(r.get('bag', ''))))


def lua_str(value: str, quote: str = '"') -> str:
    """A quoted Lua string; three-digit control escapes cannot swallow a following digit."""
    if quote not in ('"', "'"):
        raise ValueError('Lua quote must be single or double')
    escaped = []
    for char in str(value):
        escaped.append('\\' + char if char in ('\\', quote) else
                       {'\n': r'\n', '\r': r'\r', '\t': r'\t'}.get(char, '\\%03d' % ord(char))
                       if ord(char) < 32 or ord(char) == 127 else char)
    return quote + ''.join(escaped) + quote


def _replacement(piece, new_row, bag_names=None, table=False):
    augments = split_augments(new_row.get('augments', ''))
    assert equip_match(augments, new_row.get('augments', ''))
    name = lua_str(new_row['name'])
    if not (table or augments or piece.priority is not None or piece.bag):
        return name
    fields = ['name=' + name]
    if augments:
        fields.append('augments={' + ','.join(lua_str(a, "'") for a in augments) + '}')
    if piece.priority is not None:
        fields.append(f'priority={int(piece.priority)}')
    if piece.bag:
        key = bag_key(new_row.get('bag', ''))
        defaults = {'inventory': 'Inventory', 'wardrobe': 'Wardrobe',
                    **{f'wardrobe{n}': f'Wardrobe {n}' for n in range(2, 9)}}
        bag = (bag_names or {}).get(key, defaults.get(key, new_row.get('bag', '')))
        if not reachable(bag):
            raise ValueError('Move this copy to an inventory bag before making a designated-bag fix')
        fields.append('bag=' + lua_str(bag))
    return '{ ' + ', '.join(fields) + ' }'


def fix_snippet(piece: Piece, new_row: dict, bag_names=None) -> str:
    # gstack-shortcut(dec-4891397d): snippets instead of writing hand-written sets,
    # upgrade when copy-paste fixes feel too tedious (Approach B).
    key = piece.original_key
    if not re.fullmatch(r'[A-Za-z_]\w*', key):
        key = '[' + lua_str(key) + ']'
    return key + '=' + _replacement(piece, new_row, bag_names) + ','


@dataclass
class Location:
    candidates: list[tuple[str, int]] = field(default_factory=list)

    @property
    def verified(self):
        return len(self.candidates) == 1

    @property
    def file(self):
        return self.candidates[0][0] if self.verified else ''

    @property
    def line(self):
        return self.candidates[0][1] if self.verified else None


_SOURCE_TOKEN = re.compile(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\[(=*)\[.*?\]\1\]|[A-Za-z_]\w*|\d+|[^\s]''', re.S)


def _string_value(token):
    if token.startswith(('"', "'")):
        escapes = {'n': '\n', 'r': '\r', 't': '\t', 'a': '\a', 'b': '\b', 'f': '\f', 'v': '\v'}
        return re.sub(r'\\(\d{1,3}|.)', lambda m: chr(int(m[1])) if m[1].isdigit()
                      else escapes.get(m[1], m[1]), token[1:-1])
    match = re.match(r'\[(=*)\[', token)
    return token[match.end():-(len(match[1]) + 2)].lstrip('\n') if match else None


def _table_fields(tokens, values, start, end):
    """Literal table fields as (key position, key, value start, value end), excluding nested fields."""
    i = start + 1
    while i < end and tokens[i][0] != '}':
        if tokens[i][0] in (',', ';'):
            i += 1
            continue
        key_pos, key, equal = i, tokens[i][0], i + 1
        if key == '[' and i + 3 < end and values[i+1] is not None and tokens[i+2][0] == ']':
            key, equal = values[i+1], i + 3
        named = equal < end and tokens[equal][0] == '='
        value_start = equal + 1 if named else i
        j, stack = value_start, []
        while j < end:
            token = tokens[j][0]
            if not stack and token in (',', ';', '}'):
                break
            if token in ('{', '(', '['):
                stack.append(token)
            elif token in ('}', ')', ']'):
                if stack:
                    stack.pop()
                else:
                    break
            j += 1
        if named:
            yield key_pos, key, value_start, j
        i = max(j, i + 1)


def _literal_item_name(tokens, values, start, end, old_name):
    if end == start + 1:
        return values[start] is not None and identity(values[start]) == identity(old_name)
    if start < end and tokens[start][0] == '{':
        names = [(a, b) for _pos, key, a, b in _table_fields(tokens, values, start, end) if key == 'name']
        return len(names) == 1 and _literal_item_name(tokens, values, *names[0], old_name)
    return False


def _slot_field_positions(tokens, values, start, end, slot, old_name):
    # Only the set literal itself or literal arguments to set_combine are verified. Dynamic builders and
    # function bodies cannot prove where the runtime value came from, so they retain ambiguous guidance.
    if any(t == 'function' for t, _pos in tokens[start:end]):
        return []
    literal = tokens[start][0] == '{'
    combine = tokens[start][0] == 'set_combine'
    if not literal and not combine:
        return []
    arguments = [(start, end)]
    if combine:
        arguments, stack, first = [], [], start + 2
        for i in range(first, end - 1):
            token = tokens[i][0]
            if token == ',' and not stack:
                arguments.append((first, i))
                first = i + 1
            elif token in ('{', '(', '['):
                stack.append(token)
            elif token in ('}', ')', ']') and stack:
                stack.pop()
        arguments.append((first, end - 1))
    found = []
    for a, b in arguments:
        if a >= b or tokens[a][0] != '{' or tokens[b-1][0] != '}':
            found = []  # A later unresolved argument may override any earlier literal slot.
            continue
        for pos, key, value_start, value_end in _table_fields(tokens, values, a, b):
            if identity(key) == identity(slot):
                found = [pos] if _literal_item_name(tokens, values, value_start, value_end, old_name) else []
    return found


def find_line(files, set_path: str, old_name: str, old_augments=(), *, slot: str = '', _sources=None) -> Location:
    """Verify one source location, or retain candidates without guessing (eng D22).

    A tiny lexer keeps strings out of path/brace matching. Shared item definitions must contain the name
    and every old augment in one item table, never just a common first augment in a neighbouring table.
    Slot fixes also verify the original slot field; another slot's matching item is never its destination.
    """
    candidates = []
    slot_reassigned = False
    set_assignments = 0
    for filename in dict.fromkeys(files):
        cached = _sources.get(filename) if _sources is not None else None
        if cached is None:
            try:
                source = strip_comments(Path(filename).read_text(encoding='utf-8-sig', errors='replace'))
            except OSError:
                continue
            tokens = [(m[0], m.start()) for m in _SOURCE_TOKEN.finditer(source)]
            values = [_string_value(t) for t, _ in tokens]
            cached = source, tokens, values
            if _sources is not None:
                _sources[filename] = cached
        source, tokens, values = cached
        if not set_path and not any(identity(v) == identity(old_name) for v in values if v is not None):
            continue
        if set_path:
            assignments = []
            for i, (token, pos) in enumerate(tokens):
                if token != 'sets' or (i and tokens[i-1][0] in ('.', ':')):
                    continue
                j = i + 1
                while j < len(tokens):
                    if tokens[j][0] == '.' and j + 1 < len(tokens) and re.fullmatch(r'[A-Za-z_]\w*', tokens[j+1][0]):
                        j += 2
                    elif tokens[j][0] == '[' and j + 2 < len(tokens) and tokens[j+2][0] == ']':
                        j += 3
                    else:
                        break
                if j < len(tokens) and tokens[j][0] == '=' and (j+1 == len(tokens) or tokens[j+1][0] != '='):
                    assignments.append((i, j, normalise_path(source[pos:tokens[j][1]], case_sensitive=True)))
            # A field snippet cannot replace a standalone assignment, and its presence means an earlier
            # set-literal field may be overwritten. Across includes the execution order is not provable.
            prefix = normalise_path(set_path, case_sensitive=True) + '.'
            set_assignments += sum(path == prefix[:-1] for _i, _j, path in assignments)
            if slot and any(path.startswith(prefix) and identity(path[len(prefix):]) == identity(slot)
                            for _i, _j, path in assignments):
                slot_reassigned = True
            for n, (i, j, path) in enumerate(assignments):
                end = assignments[n+1][0] if n+1 < len(assignments) else len(tokens)
                if path != normalise_path(set_path, case_sensitive=True) or j + 1 >= end:
                    continue
                # Bound the RHS expression: an unrelated string later in the function is not evidence.
                first = j + 1
                if tokens[first][0] in ('{', '('):
                    opening = first
                elif first + 1 < end and tokens[first + 1][0] == '(':
                    opening = first + 1  # e.g. set_combine(...)
                else:
                    opening = None
                    end = first + 1
                if opening is not None:
                    stack = []
                    for k in range(opening, end):
                        token = tokens[k][0]
                        if token in ('{', '('):
                            stack.append(token)
                        elif token in ('}', ')'):
                            if stack:
                                stack.pop()
                            if not stack:
                                end = k + 1
                                break
                if slot:
                    positions = _slot_field_positions(tokens, values, first, end, slot, old_name)
                else:
                    positions = [k for k in range(first, end) if values[k] is not None
                                 and identity(values[k]) == identity(old_name)]
                candidates.extend((filename, source.count('\n', 0, tokens[k][1]) + 1) for k in positions)
        else:
            stack = []
            for i, (token, pos) in enumerate(tokens):
                if token == '{':
                    stack.append(i)
                elif token == '}' and stack:
                    start = stack.pop()
                    # Only a direct name= field identifies an item table (not its outer registry).
                    depth, named = 0, False
                    for j in range(start + 1, i - 1):
                        t = tokens[j][0]
                        if t == '{':
                            depth += 1
                        elif t == '}':
                            depth -= 1
                        elif depth == 0 and t == 'name' and tokens[j+1][0] == '=' and identity(values[j+2]) == identity(old_name):
                            named = True
                    strings = Counter(v for v in values[start+1:i] if v is not None)
                    if named and not (Counter(split_augments(old_augments)) - strings):
                        candidates.append((filename, source.count('\n', 0, tokens[start][1]) + 1))
    # Multiple whole-set assignments can replace a matching literal with a dynamic table. Without an
    # execution trace, a single surviving name literal does not prove which definition is active.
    unique = list(dict.fromkeys(candidates))
    if slot_reassigned or (slot and set_assignments > 1 and len(unique) == 1):
        return Location()
    return Location(unique)


@dataclass
class FixTarget:
    key: tuple
    path: str
    slot: str
    snippet: str
    affected_sets: list[str]
    location: Location
    blocked_reason: str = ''


@dataclass
class FixPlan:
    old_name: str
    new_name: str
    targets: list[FixTarget] = field(default_factory=list)

    @property
    def copyable_targets(self):
        return [target for target in self.targets if target.snippet and not target.blocked_reason]

    def text(self):
        # Comments must stay on one line even when player-supplied names/paths contain controls.
        clean = lambda s: str(s).replace('\r', ' ').replace('\n', ' ')
        lines = [f'-- Vana\'diel Nexus: {clean(self.old_name)} → {clean(self.new_name)} ({len(self.copyable_targets)} places)']
        for target in self.targets:
            where = (f'{target.location.file}, line {target.location.line}' if target.location.verified else
                     f'Location ambiguous: search your files for {target.path or self.old_name}')
            lines.append(f'-- {clean(target.path or "shared definition")} ({clean(where)})')
            lines.append('-- Skipped: ' + clean(target.blocked_reason) if target.blocked_reason else target.snippet)
        return '\n'.join(lines)


def slot_fix_plan(job_read: JobRead, selected: SetRead, piece: Piece, new_row: dict, game: GameData) -> FixPlan:
    """An explicitly selected correction for an unknown name; never guess matching items or registry edits."""
    plan = FixPlan(piece.name, new_row['name'])
    item = game.items.get(new_row.get('item_id'))
    job_id = game.job_ids.get(job_read.job)
    if item is None or not item_res.fits(item, piece.slot) or (job_id is not None and not item_res.wearable(item, job_id)):
        return plan
    sets = {s.path: s for s in job_read.sets}
    affected = [selected.path]
    for s in job_read.sets:
        path, seen = s.path, set()
        while path in sets and path not in seen and path != selected.path:
            seen.add(path)
            p = sets[path].pieces.get(piece.slot)
            path = p.inherited_from if p else ''
        if path == selected.path and s.path != selected.path:
            affected.append(s.path)
    location = (Location() if selected.odd_path else
                find_line(job_read.files, selected.path, piece.name, slot=piece.original_key))
    plan.targets = [FixTarget(('set', selected.path, piece.slot), selected.path, piece.slot,
                             fix_snippet(piece, new_row, game.bag_names), affected, location)]
    return plan


def fix_plan(job_read: JobRead, old_item_id: int, old_aug_key, new_row: dict, game: GameData) -> FixPlan:
    """Deduplicate paste destinations, tracing inherited slots to their verified root first."""
    old_item = game.items.get(old_item_id)
    replacement = game.items.get(new_row.get('item_id'))
    plan = FixPlan(old_item.en if old_item else '', new_row['name'])
    job_id = game.job_ids.get(job_read.job)
    if old_item is None or replacement is None or (job_id is not None and not item_res.wearable(replacement, job_id)):
        return plan
    sets = {s.path: s for s in job_read.sets}
    direct = {}
    incompatible_tables = set()
    for s in job_read.sets:
        for p in s.pieces.values():
            if p.table_id and not item_res.fits(replacement, p.slot):
                incompatible_tables.add(p.table_id)
            if p.table_id and not p.origin_path and not p.inherited_from:
                direct.setdefault(p.table_id, set()).add(s.path)
    targets = {}
    sources = {}  # Source text/tokens are read once per plan, never cached across file changes.
    for s in job_read.sets:
        for slot, piece in s.pieces.items():
            ids, problem = resolve(piece, game, job_read.job)
            if (piece.empty or problem or old_item_id not in ids or not item_res.fits(replacement, slot)
                    or (piece.augments and augment_key(piece.augments) != old_aug_key)):
                continue
            root = sets.get(piece.origin_path or piece.inherited_from, s)
            base = root.pieces.get(slot, piece)
            shared = bool(base.table_id and base.table_id not in incompatible_tables
                          and len(direct.get(base.table_id, ())) > 1)
            key = ('table', base.table_id) if shared else ('set', root.path, slot)
            if key not in targets:
                blocked_reason = ''
                try:
                    snippet = (_replacement(base, new_row, game.bag_names, table=True) if shared else
                               fix_snippet(base, new_row, game.bag_names))
                except ValueError as error:
                    snippet, blocked_reason = '', str(error)
                location = (find_line(job_read.files, '', base.name, base.augments, _sources=sources) if shared else
                            Location() if root.odd_path else
                            find_line(job_read.files, root.path, base.name, slot=base.original_key, _sources=sources))
                targets[key] = FixTarget(key, '' if shared else root.path, slot, snippet, [], location, blocked_reason)
            if s.path not in targets[key].affected_sets:
                targets[key].affected_sets.append(s.path)
    plan.targets = list(targets.values())
    return plan


def copy_shortages(job_read: JobRead, targets: list[FixTarget], new_row: dict, rows_char: list, game: GameData) -> list[str]:
    """Warn when the proposed edit asks paired slots to share too few matching physical copies."""
    warnings = []
    for original in job_read.sets:
        pieces = dict(original.pieces)
        changed = False
        for target in targets:
            if target.blocked_reason or original.path not in target.affected_sets:
                continue
            for slot, piece in original.pieces.items():
                applies = piece.table_id == target.key[1] if target.key[0] == 'table' else slot == target.slot
                if applies:
                    pieces[slot] = replace(piece, name=new_row['name'], augments=split_augments(new_row.get('augments', '')),
                                           bag=new_row.get('bag', '') if piece.bag else '', empty=False)
                    changed = True
        if not changed:
            continue
        related = {slot: piece for slot, piece in pieces.items()
                   if not piece.empty and new_row['item_id'] in resolve(piece, game, job_read.job)[0]}
        if len(related) < 2:
            continue
        ids = {item_id for piece in related.values() for item_id in resolve(piece, game, job_read.job)[0]}
        rows = [row for row in rows_char if row.get('item_id') in ids]
        statuses = allocate(replace(original, pieces=related), rows, [], game, job_read.job, 'ok', job_read.character)
        if any(status.kind == 'missing' and status.detail.startswith('only ') for status in statuses.values()):
            slots = ' / '.join(SLOT_LABELS[slot] for slot in related)
            warnings.append(f'{original.path}: not enough matching copies for {slots}.')
    return warnings
