"""Pure identity, selector and strict-requirement policies; no UI or persistence.

Observations are never normalized in place. Rank text is ignored only by the
GearSwap selector, not by strict guide requirements.
"""
import re
from collections import Counter

RANK_RE = re.compile(r'\bRank\s*(\d+)\b', re.I)
PATH_RE = re.compile(r'\bPath\s*[: ]\s*([A-D])\b', re.I)
SLOTS = ('main', 'sub', 'range', 'ammo', 'head', 'neck', 'ear1', 'ear2',
         'body', 'hands', 'ring1', 'ring2', 'back', 'waist', 'legs', 'feet')
_ALIASES = {**{s: s for s in SLOTS}, 'ranged': 'range',
            'left_ear': 'ear1', 'right_ear': 'ear2', 'learring': 'ear1',
            'rearring': 'ear2', 'lear': 'ear1', 'rear': 'ear2',
            'left_ring': 'ring1', 'right_ring': 'ring2', 'lring': 'ring1', 'rring': 'ring2'}


def identity(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).casefold()


def canonical_slot(value):
    try:
        return _ALIASES[value.casefold()]
    except (KeyError, AttributeError):
        raise ValueError(f'Unknown or ambiguous slot: {value!r}') from None


def split_augments(augments):
    """Selector representation. Preserve the caller's raw observation separately."""
    if isinstance(augments, str):
        parts = [part.strip() for part in augments.split(', ')] if augments.strip() else []
    else:
        parts = [str(part) for part in augments or []]
    return [part for part in parts if part and part != 'none' and not RANK_RE.fullmatch(part.strip())]


def augment_key(augments):
    return frozenset(identity(part).replace('“', "'").replace('”', "'").replace('"', "'")
                     for part in split_augments(augments))


def _aug_strip(text):
    return re.sub(r'[^A-Za-z0-9,\-]', '', text.lower())


def equip_match(goal, copy_augments, rare=False):
    """GearSwap selectability, including its Rare shortcut and synthetic Rank rule."""
    goal = split_augments(goal)
    if not goal or rare:
        return True
    current = Counter(_aug_strip(part) for part in split_augments(copy_augments))
    return not (Counter(_aug_strip(part) for part in goal) - current)


def requirements_match(requirements, row, *, legacy_substrings=False):
    """All strict requirements must be observed on this one copy. No Rare shortcut.

    The legacy guide adapter retains its historical substring behavior; new
    targets compare whole augment parts with multiplicity.
    """
    raw = row.get('augments', '')
    observed = '\n'.join(raw) if isinstance(raw, list) else str(raw)
    rank_match, path_match = RANK_RE.search(observed), PATH_RE.search(observed)
    rank = row.get('rank', int(rank_match[1]) if rank_match else None)
    path = row.get('path', path_match[1] if path_match else '')
    minimum = requirements.get('rank')
    if minimum is not None and (type(rank) is not int or rank < minimum):
        return False
    if requirements.get('path') and identity(path) != identity(requirements['path']):
        return False
    wanted = requirements.get('augments', [])
    if legacy_substrings:
        return all(identity(a) in identity(observed) for a in wanted)
    return not (Counter(identity(a) for a in wanted) -
                Counter(identity(a) for a in split_augments(raw)))


def units(rows):
    for row in rows:
        try:
            count = max(1, int(row.get('count', 1) or 1))
        except (TypeError, ValueError):
            count = 1
        for _ in range(count):
            yield row


def maximum_matching(slots, candidates):
    """Maximum bipartite slot -> physical unit allocation, in supplied order."""
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


def _preferred_matching(slots, candidates, ready):
    """Rectangular assignment: maximize ready slots, then total owned slots.

    Hungarian potentials, with one dummy column per slot for shortages. The
    higher ready reward cannot be outweighed by any number of owned slots.
    Both status flags therefore describe the same feasible physical allocation.
    """
    slots = list(slots)
    physical = sorted({i for values in candidates.values() for i in values})
    n, m = len(slots), len(physical) + len(slots)
    owned_sets = {s: set(candidates[s]) for s in slots}
    ready_sets = {s: set(ready[s]) for s in slots}
    u, v, owner, way = [0] * (n + 1), [0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for row in range(1, n + 1):
        owner[0], column = row, 0
        minimum, used = [float('inf')] * (m + 1), [False] * (m + 1)
        while True:
            used[column] = True
            current_row = owner[column]
            slot = slots[current_row - 1]
            delta, next_column = float('inf'), 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                unit = physical[j - 1] if j <= len(physical) else None
                cost = (-(1 + (n + 1 if unit in ready_sets[slot] else 0))
                        if unit in owned_sets[slot] else n + 2 if unit is not None else 0)
                reduced = cost - u[current_row] - v[j]
                if reduced < minimum[j]:
                    minimum[j], way[j] = reduced, column
                if minimum[j] < delta:
                    delta, next_column = minimum[j], j
            for j in range(m + 1):
                if used[j]:
                    u[owner[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            column = next_column
            if owner[column] == 0:
                break
        while column:
            previous = way[column]
            owner[column] = owner[previous]
            column = previous
    return {slots[owner[j] - 1]: physical[j - 1] for j in range(1, len(physical) + 1)
            if owner[j] and physical[j - 1] in owned_sets[slots[owner[j] - 1]]}


def allocate_requirements(slots, rows, character_key, bindings=(), *, equippable_bag_ids=()):
    """Strict simultaneous ownership and designated-bag readiness, separately.

    Numeric bag IDs must come from the caller's verified resource mapping.
    Returned unit indices are ephemeral evidence, never saved copy identities.
    """
    observed = []
    for row in rows:
        if row.get('character_key') != character_key:
            continue
        count = row.get('count', 1)
        if type(count) is not int or count < 1 or count > 9999:
            raise ValueError('Strict observations require a positive bounded integer count')
        observed.extend([row] * count)
    bags = {b['slot']: b['bag_id'] for b in bindings}
    wanted = {s['slot']: s for s in slots if s['state'] == 'selected'}
    candidates = {slot: [i for i, r in enumerate(observed)
                         if r.get('item_id') == s['item_id']
                         and requirements_match(s.get('requirements', {}), r)]
                  for slot, s in wanted.items()}
    ready = {s: [i for i in ids if observed[i].get('bag_id') in equippable_bag_ids
                 and (s not in bags or observed[i].get('bag_id') == bags[s])]
             for s, ids in candidates.items()}
    allocation = _preferred_matching(wanted, candidates, ready)
    return {s: {'owned': s in allocation, 'ready': allocation.get(s) in ready[s],
                'unit': allocation.get(s), 'ambiguous': len(ready[s] or candidates[s]) > 1}
            for s in wanted}
