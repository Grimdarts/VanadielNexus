"""Guide equipment targets, kept separate from owned equipment and player edits."""
from collections import Counter
from copy import deepcopy
from .paths import resource_path
from .equipment_matching import identity, RANK_RE, PATH_RE, requirements_match
from .guide_catalog import decode_json, index_records, records, require, text, validate_requirements


# What each guide set is for, in picker order, with one plain line about when GearSwap would wear it.
# tools/classify_guide_sets.py gives every catalog set one of these purposes.
PURPOSES = {
    'Idle': 'Worn while standing around or moving, not fighting (GearSwap idle sets).',
    'Defense': 'Worn to take less damage: physical, magical or both (GearSwap defense / DT sets).',
    'Melee / TP': 'Worn while engaged and building TP (GearSwap engaged sets).',
    'Weapon skill': 'Worn for the moment you use this weapon skill (GearSwap precast weapon skill sets).',
    'Ranged': 'Worn while shooting (GearSwap ranged midcast sets).',
    'Precast': 'Worn as you start a spell, shot or Blood Pact to make it faster (GearSwap precast sets).',
    'Midcast: healing': 'Worn while a Cure or other healing spell lands (GearSwap midcast sets).',
    'Midcast: enhancing': 'Worn while a buff spell lands, for potency or duration (GearSwap midcast sets).',
    'Midcast: enfeebling': 'Worn while a debuff spell lands, for accuracy, potency or duration (GearSwap midcast sets).',
    'Midcast: nuking': 'Worn while a damage spell lands, including magic bursts (GearSwap midcast sets).',
    'Midcast: blue magic': 'Worn while a blue magic spell lands (GearSwap midcast sets).',
    'Midcast: ninjutsu': 'Worn while a ninjutsu spell lands (GearSwap midcast sets).',
    'Job ability': 'Worn for the moment you use this job ability (GearSwap precast job ability sets).',
    'Pet': 'Worn while your pet acts, so its move gets your gear bonuses (GearSwap pet midcast sets).',
    'Gear reference': 'Not a GearSwap set: a full AF, Relic or Empyrean set to check which pieces you own.',
}


def load_catalog(*, windower_dir=''):
    with open(resource_path('gear_guides.json'), encoding='utf-8') as source:
        catalog = decode_json(source.read())
    if isinstance(catalog, dict) and catalog.get('schema_version') == 2:
        from . import item_res
        from .guide_catalog import validate_catalog
        from .equipment_hands import hand_types
        items = item_res.items(windower_dir)
        return validate_catalog(catalog, items=items, hand_types=hand_types(items))
    # Preserve the shipped v1 catalog and its selector policy.
    require(isinstance(catalog, dict) and type(catalog.get('schema_version')) is int
            and catalog['schema_version'] == 1, 'catalog', 'expected legacy schema_version 1')
    text(catalog.get('reviewed_on'), 'catalog.reviewed_on')
    entries = index_records(catalog.get('sets'), 'sets')
    guides = records(catalog.get('guides'), 'guides')
    for guide in guides:
        text(guide.get('job'), 'guide.job')
        text(guide.get('url'), 'guide.url')
    for key, entry in entries.items():
        for field in ('label', 'url', 'purpose', 'target'):
            text(entry.get(field), key + '.' + field)
        require(entry['purpose'] in PURPOSES, key, 'unknown purpose')
        require(type(entry.get('version_rank')) is int and entry['version_rank'] >= 1,
                key, 'version rank required')
        for src in records(entry.get('sources'), key + '.sources'):
            text(src.get('job'), key + '.source.job')
            text(src.get('guide_url'), key + '.source.guide_url')
        for item in records(entry.get('items'), key + '.items'):
            text(item.get('name'), key + '.item.name')
            require(type(item.get('item_id')) is int and item['item_id'] > 0, key, 'item ID required')
            validate_requirements(item.get('requirements', {}), key + '.requirements')
    return catalog


def picker_tree(catalog, job):
    """{purpose: {target: [sets, best version first]}} for one job, purposes in PURPOSES order, targets A-Z."""
    tree = {}
    for entry in catalog['sets']:
        if any(src['job'] == job for src in entry['sources']):
            tree.setdefault(entry.get('purpose', 'Gear reference'), {}).setdefault(
                entry.get('target') or entry['label'], []).append(entry)
    ordered = {}
    for purpose in [p for p in PURPOSES if p in tree] + [p for p in tree if p not in PURPOSES]:
        ordered[purpose] = {target: sorted(sets, key=lambda e: (e.get('version_rank', 1), e['label']))
                            for target, sets in sorted(tree[purpose].items(), key=lambda kv: kv[0].casefold())}
    return ordered


def candidates(target, inventory, character=''):
    names = {identity(target['name']), *(identity(n) for n in target.get('aliases', []))}
    return [row for row in inventory
            if (not character or identity(row.get('character')) == identity(character))
            and ((target.get('item_id') and row.get('item_id', row.get('id')) == target['item_id'])
                 or identity(row.get('name')) in names)]


def equipment_status(target, inventory, character='', required_count=1):
    """One physical copy must satisfy all requirements; never combine different copies' augments."""
    matching = candidates(target, inventory, character)
    total = sum(int(row.get('count', 1)) for row in matching)
    if total < required_count:
        relatives=[]
        for relative in target.get('tier_family', []):
            if candidates(relative, inventory, character):
                relatives.append(relative['name'])
        if not matching and relatives:
            return 'Upgrade tier', 'Other tiers owned: '+', '.join(relatives)+'. Exact target tier still needed or must be reviewed.'
        elsewhere = candidates(target, inventory) if character else []
        if not matching and elsewhere:
            return 'Other character', 'Owned elsewhere; not available on this character.'
        return 'Missing', f'{total}/{required_count} copies in the selected character snapshot.'
    requirements = target.get('requirements', {})
    minimum_rank = requirements.get('rank')
    augments = requirements.get('augments', [])
    path = requirements.get('path')
    if not (minimum_rank is not None or augments or path):
        if target.get('augmentable'):
            return 'Verify augments', 'Base piece owned. Guide path, rank and augments are not confirmed.'
        return 'Owned', f'{total}/{required_count} copies found.'
    complete = 0
    for row in matching:
        if not requirements_match(requirements, row, legacy_substrings=True):
            continue
        complete += int(row.get('count', 1))
    if complete >= required_count:
        return 'Owned', 'Observed rank/path/augments meet the explicit target.'
    return 'Upgrade / verify', 'Base piece owned; required rank/path/augments are unmet or unreported.'


def set_rows(equipment_set, inventory, character=''):
    counts = Counter(item['item_id'] for item in equipment_set['items'])
    result = []
    for item in equipment_set['items']:
        status, detail = equipment_status(item, inventory, character, counts[item['item_id']])
        result.append({**item, 'status': status, 'detail': detail,
                       'requirement': item.get('requirement_note', 'See linked guide; assumptions may differ by set.')})
    return result


def track_set(db, equipment_set, job):
    """Explicitly add targets without replacing personal wishlist/goals or duplicating imports."""
    added = 0
    for target in equipment_set['items']:
        key = f"guide-{job}-{equipment_set['id']}-{target['item_id']}"
        if any(row.get('id') == key for row in db['wishlist']):
            continue
        db['wishlist'].append({'id': key, 'name': target['name'], 'job': job,
            'slot': target.get('slot', ''), 'sourceType': 'Guide target',
            'obtainHow': target.get('requirement_note', 'Check the guide for augments and conditions.'),
            'wikiUrl': equipment_set['url'], 'guideSet': equipment_set['id'],
            'guideItemId': target['item_id'], 'guideTarget': dict(target), 'pinned': False})
        added += 1
    return added


def revision_tree(catalog, job):
    """The existing purpose/set/version picker, with immutable revision identities.

    Retired revisions are history only: they are never listed, selected or proposed.
    """
    tree = {}
    retired = catalog.get('_retirements') or {}
    for group in catalog['sets']:
        if job not in group['jobs']:
            continue
        revisions = [dict(r, group=deepcopy(group)) for r in catalog['revisions']
                     if r['set_id'] == group['id'] and r['id'] not in retired]
        revisions.sort(key=lambda r: (r['id'] != group.get('default_revision_id'), r['version_order'], r['label']))
        # IDs, rather than titles, distinguish two conceptual contexts with equal labels.
        tree.setdefault(group['purpose'], {})[group['id']] = revisions
    return tree


def effective_slots(revision, target=None):
    slots = deepcopy(revision.get('slots', []))
    overrides = {o['slot']: o['requirements'] for o in (target or {}).get('overrides', [])}
    for slot in slots:
        if slot['slot'] in overrides:
            slot['requirements'] = deepcopy(overrides[slot['slot']])
    return slots


def requirement_text(requirements):
    parts = []
    if 'rank' in requirements:
        parts.append(f"Rank ≥ {requirements['rank']}")
    if requirements.get('path'):
        parts.append('Path ' + requirements['path'])
    parts.extend(requirements.get('augments', []))
    return '; '.join(parts) or 'No explicit augment requirement'


def revision_rows(revision, inventory, character, *, target=None, items=None, bags=(), snapshot_available=False):
    """Strict simultaneous comparison against one named snapshot; never name-match IDs.

    Bag records come from res/bags.lua. Unknown locations cannot establish readiness.
    Observations and personal requirements are detached from curated revisions.
    """
    from .equipment_matching import SLOTS, allocate_requirements, units
    from .item_res import bag_key
    items = items or {}
    bag_names = {b['id']: b['en'] for b in bags}
    bag_ids = {bag_key(b['en']): b['id'] for b in bags}
    equippable = {b['id'] for b in bags if b.get('equippable') is True}
    observed = []
    for row in inventory:
        if identity(row.get('character')) != identity(character):
            continue
        bag_id = row.get('bag_id')
        # Unknown numeric IDs stay unknown, never infer reachability from names alone.
        if type(bag_id) is not int:
            bag_id = bag_ids.get(bag_key(row.get('bag')))
        observed.append({**row, 'character_key': character, 'item_id': row.get('item_id', row.get('id')),
                         'bag_id': bag_id})
    slots = effective_slots(revision, target)
    bindings = (target or {}).get('bindings', [])
    allocation = allocate_requirements(slots, observed, character, bindings,
                                       equippable_bag_ids=equippable) if snapshot_available else {}
    expanded = list(units(observed))
    binding_map = {b['slot']: b['bag_id'] for b in bindings}
    slot_map = {s['slot']: s for s in slots}
    result = []
    for slot in SLOTS:
        record = slot_map.get(slot, {'slot': slot, 'state': 'omitted'})
        state = record['state']
        name = {'empty': 'Intentional empty', 'unknown': 'Unknown equipment', 'omitted': 'Not specified'}.get(state)
        item_id = record.get('item_id')
        if state == 'selected':
            resource = items.get(item_id)
            name = resource.en if resource else f'Item #{item_id} (name unavailable)'
            match = allocation.get(slot)
            if match is None:
                status, detail = 'Unverified', 'No inventory snapshot for this character.'
            elif match['owned']:
                unit = expanded[match['unit']]
                location = bag_names.get(unit.get('bag_id'), unit.get('bag') or 'unknown bag')
                status = 'Ready in snapshot' if match['ready'] else 'Owned · check bag'
                detail = f'Observed: {location}.'
                if match['ambiguous']:
                    detail += ' Multiple indistinguishable matching copies; exact copy unresolved.'
            else:
                base = any(r['item_id'] == item_id for r in observed)
                status = 'Upgrade / verify' if base else 'Missing'
                detail = ('Required copy/rank/path/augments unmet, unreported or allocated to another slot.'
                          if base else 'No matching item ID in this character snapshot.')
        else:
            status = state.capitalize()
            detail = {'empty': 'Explicitly empty; no item allocated.', 'unknown': 'Source selection is unresolved.',
                      'omitted': 'Outside this source composition; no empty slot inferred.'}[state]
            if state == 'unknown' and record.get('diagnostic'):
                detail += ' ' + record['diagnostic']
        requirement = requirement_text(record.get('requirements', {})) if state == 'selected' else ''
        if slot in binding_map:
            requirement += ' · Designated: ' + bag_names.get(binding_map[slot], f"bag #{binding_map[slot]} (unverified)")
        result.append({**record, 'id': slot, 'name': name, 'item_id': item_id, 'status': status,
                       'detail': detail, 'requirement': requirement,
                       'slot': {'ring1': 'Ring 1', 'ring2': 'Ring 2', 'ear1': 'Ear 1', 'ear2': 'Ear 2'}.get(slot, slot.title()),
                       'canonical_slot': slot})
    return result
