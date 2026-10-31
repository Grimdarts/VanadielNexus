"""Guide equipment targets, kept separate from owned equipment and player edits."""
import json
import re
from collections import Counter
from .paths import resource_path


def load_catalog():
    with open(resource_path('gear_guides.json'), encoding='utf-8') as source:
        return json.load(source)


def identity(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).casefold()


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
        observed = row.get('augments', '')
        observed = '\n'.join(observed) if isinstance(observed, list) else str(observed)
        rank_match = re.search(r'\bRank\s*(\d+)\b', observed, re.I)
        rank = row.get('rank', int(rank_match[1]) if rank_match else None)
        path_match = re.search(r'\bPath\s*[: ]\s*([A-D])\b', observed, re.I)
        observed_path = row.get('path', path_match[1] if path_match else '')
        if minimum_rank is not None and (rank is None or rank < minimum_rank):
            continue
        if path and identity(observed_path) != identity(path):
            continue
        if any(identity(aug) not in identity(observed) for aug in augments):
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
