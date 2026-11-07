"""Read-only adapters from inspected GearSwap declarations to evidenced effects.

No implicit equipment base, player-data discovery, persistence, or Lua execution.
Snapshot names and bag names are resolved only through supplied evidence.
"""
from copy import deepcopy
from dataclasses import dataclass

from . import item_res
from .equipment_matching import SLOTS, allocate_requirements, identity, split_augments, units


@dataclass(frozen=True)
class Selection:
    slots: tuple
    bindings: tuple
    diagnostics: tuple


def name_index(items, cancelled=lambda: False):
    result = {}
    for item in items.values():
        if cancelled():
            raise ValueError('Equipment preparation cancelled')
        for name in {identity(item.en), identity(item.enl)} - {''}:
            result.setdefault(name, []).append(item.id)
    return result


def declared_selection(set_read, source, names, job, bags=()):
    """Resolved reader pieces have already applied set_combine precedence.

    Ambiguous names stay unknown; missing slots stay absent. Explicit augments
    remain requirements, not observed effects. No GearSwap Rare shortcut here.
    """
    from .guide_catalog import JOBS as jobs
    job_id = jobs.index(job) + 1 if job in jobs else None
    slots, bindings, problems = [], [], []
    bag_ids = {item_res.bag_key(b['en']): b['id'] for b in bags}
    for slot in SLOTS:
        piece = set_read.pieces.get(slot)
        if piece is None:
            continue
        if piece.empty:
            slots.append({'slot': slot, 'state': 'empty'})
            continue
        candidates = [i for i in names.get(identity(piece.name), ())
                      if item_res.fits(source.items[i], slot)
                      and job_id is not None and item_res.wearable(source.items[i], job_id)]
        if len(candidates) != 1:
            slots.append({'slot': slot, 'state': 'unknown',
                          'diagnostic': 'Item name/slot/job identity is unresolved'})
            continue
        slots.append({'slot': slot, 'state': 'selected', 'item_id': candidates[0],
                      'requirements': {'augments': split_augments(piece.augments)} if piece.augments else {}})
        if piece.bag:
            bag_id = bag_ids.get(item_res.bag_key(piece.bag))
            if bag_id is None:
                problems.append(f'{slot}: designated bag mapping unavailable; contribution excluded')
                slots[-1] = {'slot': slot, 'state': 'unknown', 'diagnostic': problems[-1]}
            else:
                bindings.append({'slot': slot, 'bag_id': bag_id})
    return Selection(tuple(slots), tuple(bindings), tuple(problems))


def observations(snapshot, character, bags=()):
    """Detach one character's snapshot. Absent and explicitly empty differ."""
    bag_ids = {item_res.bag_key(b['en']): b['id'] for b in bags}
    matches = [rows for name, rows in snapshot.items()
               if not name.startswith('Imported: ') and identity(name) == identity(character)]
    if len(matches) != 1:
        return (), False
    if not isinstance(matches[0], list):
        raise ValueError('Snapshot rows are unavailable or malformed')
    result = []
    for raw in matches[0] or []:
        if not isinstance(raw, dict):
            raise ValueError('Snapshot observation is malformed')
        row = deepcopy(raw)
        if row.get('character') and identity(row['character']) != identity(character):
            continue
        count = row.get('count', 1)
        if type(count) is not int or not 1 <= count <= 9999:
            raise ValueError('Snapshot copy quantity is invalid; refresh inventory evidence')
        row['character_key'] = character
        row['item_id'] = row.get('item_id', row.get('id'))
        if type(row.get('bag_id')) is not int:
            row['bag_id'] = bag_ids.get(item_res.bag_key(row.get('bag')))
        # A structured observed rank/path is evidence to display, never a
        # supported magnitude. Pass it through the engine's unresolved channel.
        raw_augments = row.get('augments') or ()
        augments = raw_augments.split(', ') if isinstance(raw_augments, str) else list(raw_augments)
        if row.get('rank') is not None:
            augments.append(f"Observed Rank {row['rank']} (magnitude unsupported)")
        if row.get('path'):
            augments.append(f"Observed Path {row['path']} (magnitude unsupported)")
        row['augments'] = augments
        result.append(row)
    return tuple(result), True


def allocated_copy(selection, inventory, character, slot, equippable=()):
    """An ephemeral observation, never a persistent physical-copy identifier."""
    allocation = allocate_requirements(selection.slots, inventory, character,
                                       selection.bindings, equippable_bag_ids=equippable)
    match = allocation.get(slot)
    if not match or not match['owned']:
        return None, 'Distinct observed copy unavailable'
    if match['ambiguous']:
        return None, 'Matching copies remain ambiguous; inspect observations separately'
    return list(units(inventory))[match['unit']], 'Saved observation; current readiness unconfirmed'


def comparable_rows(selected, baseline=None):
    """Only compare identical semantic keys; an absent key is never zero."""
    left = {(c.recipient, c.stat, c.unit): c for c in selected.contributions}
    right = {(c.recipient, c.stat, c.unit): c for c in baseline.contributions} if baseline else {}
    return tuple((key, left.get(key), right.get(key),
                  left[key].known - right[key].known if key in left and key in right else None)
                 for key in sorted(left.keys() | right.keys()))
