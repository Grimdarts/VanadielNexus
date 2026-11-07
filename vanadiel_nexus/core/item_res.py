"""Game data from Windower's res/ folder (items, jobs, bags, weapon skills, job abilities). Qt-free.

Every player has these files, and GearSwap reads the same ones, so matching against them is matching what
GearSwap sees. Each file is parsed once per (path, mtime).
"""
import os
import re
from dataclasses import dataclass

# res/items.lua `slots` bit per GearSwap slot name (statics.lua slot_map)
SLOT_BITS = {'main': 0, 'sub': 1, 'range': 2, 'ammo': 3, 'head': 4, 'body': 5, 'hands': 6, 'legs': 7,
             'feet': 8, 'neck': 9, 'waist': 10, 'ear1': 11, 'ear2': 12, 'ring1': 13, 'ring2': 14, 'back': 15}
_PAIRS = {'ear1': ('ear1', 'ear2'), 'ear2': ('ear1', 'ear2'), 'ring1': ('ring1', 'ring2'),
          'ring2': ('ring1', 'ring2')}
ALL_RACES = 510  # races bitmask on items every race can wear
RARE_FLAG = 0x8000  # resources.lua: flags bit 15 = Rare

_ROW_RE = re.compile(r'^\s*\[\d+\]\s*=\s*\{(.*)\},?\s*$')
_FIELD_RE = re.compile(r'([A-Za-z_]\w*)=("(?:[^"\\]|\\.)*"|-?\d+|true|false)')
_ESCAPE_RE = re.compile(r'\\(\d{1,3}|.)')


@dataclass(frozen=True)
class Item:
    id: int
    en: str
    enl: str = ''
    category: str = ''
    slots: int = 0          # 0 = not equipment
    jobs: int = 0
    level: int = 0
    races: int = 0
    superior_level: int = 0
    flags: int = 0
    skill: int = 0
    shield_size: int = 0

    @property
    def rare(self) -> bool:
        return bool(self.flags & RARE_FLAG)


def _unescape(text: str) -> str:
    def repl(match):
        code = match[1]
        if code.isdigit():
            return chr(int(code))
        return {'n': '\n', 't': '\t', 'r': '\r'}.get(code, code)
    return _ESCAPE_RE.sub(repl, text)


def _value(raw: str):
    if raw.startswith('"'):
        return _unescape(raw[1:-1])
    if raw in ('true', 'false'):
        return raw == 'true'
    return int(raw)


def parse_rows(path: str) -> list[dict]:
    """Every `[n] = {k=v,...}` row of a generated res file, as dicts. Missing file → []."""
    rows = []
    try:
        with open(path, encoding='utf-8', errors='replace') as source:
            for line in source:
                match = _ROW_RE.match(line)
                if match:
                    rows.append({key: _value(raw) for key, raw in _FIELD_RE.findall(match[1])})
    except OSError:
        pass
    return rows


_CACHE = {}  # (kind, normcased path) -> (mtime, value)


def _mtime(path: str):
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_size


def cached(kind: str, windower_dir: str, name: str, build):
    """build(path or None), rebuilt when res/<name> changes (or is cleared)."""
    path = os.path.join(windower_dir or '', 'res', name)
    key = (kind, os.path.normcase(os.path.abspath(path)))
    mtime = _mtime(path)
    hit = _CACHE.get(key)
    if hit and hit[0] == mtime:
        return hit[1]
    value = build(path) if mtime is not None else build(None)
    _CACHE[key] = (mtime, value)
    return value


def clear(windower_dir: str = None) -> None:
    """Drop the parsed res for one Windower folder (or all of them)."""
    if windower_dir is None:
        _CACHE.clear()
        return
    prefix = os.path.normcase(os.path.abspath(os.path.join(windower_dir, 'res')))
    # Called from the Sets reader's worker thread while the GUI thread fills the cache: snapshot the keys.
    for key in [k for k in list(_CACHE) if k[1].startswith(prefix)]:
        _CACHE.pop(key, None)


def all_items(windower_dir: str) -> dict[int, Item]:
    """Every row of res/items.lua (equipment or not)."""
    def build(path):
        result = {}
        for row in parse_rows(path) if path else []:
            if 'id' not in row or 'en' not in row:
                continue
            result[row['id']] = Item(
                id=row['id'], en=row['en'], enl=row.get('enl', ''), category=row.get('category', ''),
                slots=row.get('slots', 0), jobs=row.get('jobs', 0), level=row.get('level', 0),
                races=row.get('races', 0), superior_level=row.get('superior_level', 0), flags=row.get('flags', 0),
                skill=row.get('skill', 0), shield_size=row.get('shield_size', 0))
        return result
    return cached('all_items', windower_dir, 'items.lua', build)


def items(windower_dir: str) -> dict[int, Item]:
    """Equipment rows only (rows with `slots=`)."""
    return cached('items', windower_dir, 'items.lua',
                   lambda _path: {i: item for i, item in all_items(windower_dir).items() if item.slots})


def by_name(windower_dir: str) -> dict[str, list[int]]:
    """Casefolded `en` and `enl` → equipment ids, in id order."""
    def build(_path):
        names = {}
        for item_id, item in sorted(items(windower_dir).items()):
            for name in {item.en.casefold(), item.enl.casefold()} - {''}:
                names.setdefault(name, []).append(item_id)
        return names
    return cached('by_name', windower_dir, 'items.lua', build)


def equipment_names(windower_dir: str) -> dict[str, Item]:
    """`en` as the game spells it → the first equipment row with that name (for name suggestions)."""
    def build(_path):
        names = {}
        for _item_id, item in sorted(items(windower_dir).items()):
            names.setdefault(item.en, item)
        return names
    return cached('equipment_names', windower_dir, 'items.lua', build)


# Wishlist-style slot names: an earring or ring fits either side, so each pair reads as one word.
_SLOT_WORDS = (('Main', ('main',)), ('Sub', ('sub',)), ('Range', ('range',)), ('Ammo', ('ammo',)),
               ('Head', ('head',)), ('Neck', ('neck',)), ('Earring', ('ear1', 'ear2')), ('Body', ('body',)),
               ('Hands', ('hands',)), ('Ring', ('ring1', 'ring2')), ('Back', ('back',)), ('Waist', ('waist',)),
               ('Legs', ('legs',)), ('Feet', ('feet',)))


def slot_label(item: Item) -> str:
    """'Earring', 'Main / Sub', … from the item's slot bits; '' for non-equipment."""
    return ' / '.join(word for word, slots in _SLOT_WORDS
                      if any(item.slots >> SLOT_BITS[s] & 1 for s in slots))


def jobs(windower_dir: str) -> dict[str, tuple[int, str]]:
    """`ens` → (id, en) from res/jobs.lua, e.g. 'BLU' → (16, 'Blue Mage')."""
    return cached('jobs', windower_dir, 'jobs.lua', lambda path: {
        row['ens']: (row['id'], row.get('en', '')) for row in (parse_rows(path) if path else []) if 'ens' in row})


def normalise_action(name: str) -> str:
    """Casefold and drop spaces, ', :, . and - ("Savage Blade" → "savageblade")."""
    return re.sub(r"[\s':.\-]", '', str(name or '')).casefold()


def ws_names(windower_dir: str) -> set[str]:
    return cached('ws', windower_dir, 'weapon_skills.lua', lambda path: {
        normalise_action(row['en']) for row in (parse_rows(path) if path else []) if row.get('en')})


def ja_names(windower_dir: str) -> set[str]:
    """Job abilities only (type="JobAbility"), so Blood Pacts and Ready moves don't count."""
    return cached('ja', windower_dir, 'job_abilities.lua', lambda path: {
        normalise_action(row['en']) for row in (parse_rows(path) if path else [])
        if row.get('en') and row.get('type') == 'JobAbility'})


def bag_key(name: str) -> str:
    """One key per bag however it's written: lowercase, no spaces, "Wardrobe 1" ≡ "Wardrobe".

    GearSwap looks bags up as lower(nospace(name)) in res/bags.lua, where bag 8 is "Wardrobe"; the inventory
    snapshot calls the same bag "Wardrobe 1".
    """
    key = re.sub(r'\s+', '', str(name or '')).casefold()
    return 'wardrobe' if key == 'wardrobe1' else key


def bags(windower_dir: str) -> dict[str, str]:
    """bag_key → the name GearSwap accepts in `bag="…"` (res/bags.lua `en`), e.g. 'wardrobe' → 'Wardrobe'."""
    return cached('bags', windower_dir, 'bags.lua', lambda path: {
        bag_key(row['en']): row['en'] for row in (parse_rows(path) if path else []) if row.get('en')})


def fits(item: Item, slot: str) -> bool:
    """Can the item go in this slot? ear1/ear2 and ring1/ring2 accept either bit of their pair."""
    return any(item.slots & (1 << SLOT_BITS[s]) for s in _PAIRS.get(slot, (slot,)) if s in SLOT_BITS)


def wearable(item: Item, job_id: int, level: int = 99) -> bool:
    """Job and level only. Race and superior level are noted, not checked (eng review D10)."""
    return bool(item.jobs & (1 << job_id)) and item.level <= level


def race_limited(item: Item) -> bool:
    return bool(item.slots) and item.races != ALL_RACES
