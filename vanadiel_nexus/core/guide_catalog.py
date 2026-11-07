"""Versioned guide candidate validation and non-mutating compatibility adapters.

No source discovery, automatic adoption, item-stat evaluation or user-file writes.
Production v2 authoring supplies explicit resource/legality evidence; names never
stand in for item IDs. The installed v1 catalog continues through its old picker.
"""
from copy import deepcopy
from datetime import date
import json
from urllib.parse import parse_qs, urlsplit

from .equipment_matching import SLOTS, canonical_slot
from . import item_res

JOBS = ('WAR', 'MNK', 'WHM', 'BLM', 'RDM', 'THF', 'PLD', 'DRK', 'BST', 'BRD',
        'RNG', 'SAM', 'NIN', 'DRG', 'SMN', 'BLU', 'COR', 'PUP', 'DNC', 'SCH', 'GEO', 'RUN')
SOURCE_HOSTS = {'ffxiah': {'www.ffxiah.com', 'ffxiah.com'},
                'bgwiki': {'www.bg-wiki.com', 'bg-wiki.com'},
                'ffxiclopedia': {'ffxiclopedia.fandom.com'}}


class CatalogError(ValueError):
    """A candidate was rejected; the previous artifact is still authoritative."""


def require(condition, location, message):
    if not condition:
        raise CatalogError(f'{location}: {message}')


def text(value, location):
    require(isinstance(value, str) and bool(value.strip()), location, 'nonempty text required')


def integer(value, location, minimum=0):
    require(type(value) is int and value >= minimum, location, f'integer >= {minimum} required')


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, key, 'duplicate JSON key')
        result[key] = value
    return result


def decode_json(raw):
    try:
        return json.loads(raw, object_pairs_hook=object_pairs,
                          parse_constant=lambda v: require(False, v, 'non-finite JSON number'))
    except (ValueError, UnicodeError) as error:
        raise CatalogError(f'JSON: {error}') from error


def records(value, location):
    require(isinstance(value, list), location, 'list required')
    require(all(isinstance(r, dict) for r in value), location, 'object records required')
    return value


def index_records(value, location):
    result = {}
    for n, row in enumerate(records(value, location)):
        key = row.get('id')
        text(key, f'{location}[{n}].id')
        require(key not in result, location, f'duplicate id {key}')
        result[key] = row
    return result


def validate_requirements(value, location):
    require(isinstance(value, dict), location, 'requirements object required')
    require(not set(value) - {'rank', 'path', 'augments'}, location, 'unsupported requirement field')
    if 'rank' in value:
        integer(value['rank'], location + '.rank')
    if 'path' in value:
        require(value['path'] in ('A', 'B', 'C', 'D'), location, 'path must be A-D')
    if 'augments' in value:
        require(isinstance(value['augments'], list), location, 'augment list required')
        for augment in value['augments']:
            text(augment, location + '.augments')


def normalize_slots(value, *, aliases=False):
    """A missing slot remains absent; unknown and empty remain explicit records."""
    result, seen = [], set()
    for n, original in enumerate(records(value, 'slots')):
        row = deepcopy(original)
        slot = canonical_slot(row.get('slot'))
        require(slot not in seen, f'slots[{n}]', f'duplicate canonical slot {slot}')
        require(aliases or row['slot'] == slot, f'slots[{n}]', 'serialize canonical slots only')
        row['slot'] = slot
        seen.add(slot)
        state = row.get('state')
        require(state in ('selected', 'empty', 'unknown'), slot, 'invalid slot state')
        if state == 'selected':
            integer(row.get('item_id'), slot + '.item_id', 1)
            validate_requirements(row.get('requirements'), slot)
            require(row.get('quantity', 1) == 1 and type(row.get('quantity', 1)) is int,
                    slot, 'one copy per selected slot')
        else:
            require(not {'item_id', 'requirements', 'quantity', 'name'} & row.keys(), slot,
                    'non-selected state cannot assert equipment')
            if state == 'unknown':
                text(row.get('diagnostic'), slot + '.diagnostic')
        result.append(row)
    return result


def composition_diagnostics(slots, items, jobs, *, hand_types=None, context=None):
    """Per-item eligibility plus explicitly supported cross-slot constraints.

    hand_types is versioned caller evidence, never a guess from display names.
    A sub weapon also needs an explicit dual_wield context. Unknown constraints
    remain diagnostics and cannot certify a playable composition.
    """
    problems = []
    selected = {s['slot']: s for s in slots if s['state'] == 'selected'}
    for slot, row in selected.items():
        item = items.get(row['item_id'])
        if item is None:
            problems.append(f'{slot}: item resource unavailable')
            continue
        if not item_res.fits(item, slot):
            problems.append(f'{slot}: item is ineligible for slot')
        for job in jobs:
            if not item_res.wearable(item, JOBS.index(job) + 1):
                problems.append(f'{slot}: item is ineligible for {job}')
    main, sub = selected.get('main'), selected.get('sub')
    if sub:
        types = hand_types or {}
        m = types.get(main['item_id']) if main else None
        s = types.get(sub['item_id'])
        if not main or m not in ('one_handed', 'two_handed', 'hand_to_hand') or s not in ('shield', 'grip', 'one_handed'):
            problems.append('main/sub: unresolved weapon legality')
        elif m == 'two_handed' and s != 'grip' or m != 'two_handed' and s == 'grip' or m == 'hand_to_hand':
            problems.append('main/sub: incompatible equipment')
        elif s == 'one_handed' and (context or {}).get('dual_wield') is not True:
            problems.append('main/sub: dual wield is unconfirmed')
    rare_ids = [s['item_id'] for s in selected.values()
                if s['item_id'] in items and items[s['item_id']].rare]
    if len(set(rare_ids)) != len(rare_ids):
        problems.append('slots: duplicate Rare item')
    return problems


def _date(value, location):
    text(value, location)
    try:
        date.fromisoformat(value)
    except ValueError:
        raise CatalogError(f'{location}: ISO date required') from None


def validate_catalog(value, *, items, hand_types=None, previous=None, fixture=False):
    """Prepare a detached v2 candidate in full before it can be published.

    fixture=True admits only explicitly fictional source/evidence metadata, not
    missing structure or illegal compositions. Production coverage covers 22
    jobs, with explicit reviewed gaps allowed during the T7 authoring stage.
    """
    value = deepcopy(value)
    require(isinstance(value, dict), 'catalog', 'object required')
    require(type(value.get('schema_version')) is int and value['schema_version'] == 2,
            'catalog', 'supported schema_version is 2')
    sources = index_records(value.get('sources'), 'sources')
    sets = index_records(value.get('sets'), 'sets')
    revisions = index_records(value.get('revisions'), 'revisions')
    for key, source in sources.items():
        kind, url = source.get('kind'), source.get('url')
        if fixture and kind == 'fixture' and url is None:
            continue
        require(kind in SOURCE_HOSTS, key, 'unsupported public source kind')
        require(isinstance(url, str), key, 'public URL required')
        parsed = urlsplit(url)
        require(parsed.scheme == 'https' and parsed.hostname in SOURCE_HOSTS[kind]
                and not parsed.username and not parsed.password and parsed.port in (None, 443)
                and bool(parsed.path.strip('/')), key, 'invalid source URL/kind')
        prefixes = {'ffxiah': ('/node/', '/item-sets/', '/forum/topic/', '/item/'),
                    'bgwiki': ('/ffxi/', '/bg/'), 'ffxiclopedia': ('/wiki/',)}
        # MediaWiki's own Permanent link uses index.php, rather than /ffxi/.
        # Admit only the read-only title + exact positive revision form.
        query = parse_qs(parsed.query, keep_blank_values=True)
        permalink = (kind == 'bgwiki' and parsed.path == '/index.php'
                     and set(query) == {'title', 'oldid'}
                     and all(len(values) == 1 for values in query.values())
                     and bool(query['title'][0].strip())
                     and query['oldid'][0].isascii() and query['oldid'][0].isdigit()
                     and bool(query['oldid'][0].strip('0')))
        require(parsed.path.startswith(prefixes[kind]) or permalink,
                key, 'URL path does not match source kind')
        for field in ('title', 'locator'):
            text(source.get(field), key + '.' + field)
        _date(source.get('accessed_on'), key + '.accessed_on')
    for key, group in sets.items():
        jobs = group.get('jobs')
        require(isinstance(jobs, list) and jobs and all(j in JOBS for j in jobs)
                and len(set(jobs)) == len(jobs), key, 'explicit valid jobs required')
        for field in ('purpose', 'target'):
            text(group.get(field), key + '.' + field)
        require(isinstance(group.get('context'), dict), key, 'explicit context required')
        if previous:
            old = next((s for s in previous['sets'] if s['id'] == key), None)
            require(old is None or {k: v for k, v in old.items() if k != 'default_revision_id'} ==
                    {k: v for k, v in group.items() if k != 'default_revision_id'},
                    key, 'conceptual identity/context conflict; use a new set ID')
    for key, revision in revisions.items():
        group = sets.get(revision.get('set_id'))
        require(group is not None, key, 'unknown conceptual set')
        refs = revision.get('source_ids')
        require(isinstance(refs, list) and refs and all(isinstance(r, str) and r in sources for r in refs)
                and len(set(refs)) == len(refs), key, 'valid distinct source references required')
        for field in ('label', 'equipment_version', 'rationale', 'resource_fingerprint'):
            text(revision.get(field), key + '.' + field)
        integer(revision.get('version_order'), key + '.version_order', 1)
        require(revision.get('origin') in ('source_adaptation', 'nexus_recommendation'), key, 'invalid origin')
        require(revision.get('currency') in ('current', 'older', 'unknown'), key, 'invalid currency')
        evidence = revision.get('verification')
        require(isinstance(evidence, dict), key, 'verification evidence required')
        require(evidence.get('status') in (('verified', 'unresolved', 'fixture-only') if fixture else
                                          ('verified', 'unresolved')), key, 'invalid verification status')
        _date(evidence.get('checked_on'), key + '.checked_on')
        text(evidence.get('scope'), key + '.scope')
        require(isinstance(revision.get('assumptions'), list) and
                all(isinstance(a, str) and a.strip() for a in revision['assumptions']), key, 'assumptions list required')
        kind = revision.get('composition_kind')
        require(kind in ('loadout', 'partial_loadout', 'equipment_options'), key, 'composition_kind required')
        if kind == 'equipment_options':
            require(not revision.get('slots'), key, 'options are not a slot loadout')
            options = records(revision.get('options'), key + '.options')
            require(bool(options), key, 'options required')
            for option in options:
                integer(option.get('item_id'), key + '.option.item_id', 1)
                require(option['item_id'] in items, key, 'unknown option resource')
                validate_requirements(option.get('requirements'), key + '.option')
        else:
            slots = normalize_slots(revision.get('slots'))
            revision['slots'] = slots
            require(bool(slots), key, 'slot records required')
            if kind == 'loadout':
                require({s['slot'] for s in slots} == set(SLOTS), key, 'full loadout must declare 16 slots')
            else:
                require(len(slots) < len(SLOTS), key, 'partial loadout must retain omissions')
            problems = composition_diagnostics(slots, items, group['jobs'], hand_types=hand_types,
                                               context=group['context'])
            require(not problems, key, '; '.join(problems))
            require(not any(s['state'] == 'unknown' for s in slots) or evidence['status'] == 'unresolved',
                    key, 'unknown slots cannot be verified')
        if previous:
            old = next((r for r in previous['revisions'] if r['id'] == key), None)
            require(old is None or old == revision, key, 'immutable revision conflict')
            old_group = next((s for s in previous['sets'] if s['id'] == revision['set_id']), None)
            require(old is None or {k: v for k, v in old_group.items() if k != 'default_revision_id'} ==
                    {k: v for k, v in group.items() if k != 'default_revision_id'},
                    key, 'immutable revision context conflict')
            if old:
                old_sources = {s['id']: s for s in previous['sources']}
                require(all(old_sources.get(ref) == sources[ref] for ref in refs), key,
                        'immutable revision source conflict')
    for key, group in sets.items():
        own = [r for r in revisions.values() if r['set_id'] == key]
        require(bool(own), key, 'conceptual set has no revisions')
        if 'default_revision_id' in group:
            require(group['default_revision_id'] in {r['id'] for r in own}, key, 'invalid default revision')
    coverage = records(value.get('coverage'), 'coverage')
    seen = set()
    for row in coverage:
        job, priority = row.get('job'), row.get('priority')
        require(job in JOBS, 'coverage', 'invalid job')
        text(priority, 'coverage.priority')
        require((job, priority) not in seen, 'coverage', 'duplicate job/priority')
        seen.add((job, priority))
        require(row.get('status') in ('included', 'gap', 'not_applicable') and row.get('reviewed') is True,
                'coverage', 'reviewed coverage disposition required')
        for field in ('context', 'evidence'):
            text(row.get(field), 'coverage.' + field)
        refs = row.get('set_ids', [])
        require(isinstance(refs, list) and all(isinstance(s, str) and s in sets and job in sets[s]['jobs'] for s in refs),
                'coverage', 'invalid set references')
        if row['status'] == 'included':
            require(bool(refs), 'coverage', 'included sets required')
        else:
            text(row.get('reason'), 'coverage.reason')
    if not fixture:
        require(all((j, p) in seen for j in JOBS for p in ('DT Idle', 'Refresh Idle')),
                'coverage', 'all 22 jobs require explicit idle dispositions')
        require(all(r['status'] != 'not_applicable' for r in coverage if r['priority'] == 'DT Idle'),
                'coverage', 'DT Idle has no blanket exception')
    # Derived, never persisted: which revisions are history only, and their current head.
    value['_retirements'] = retirements(value)
    return value


def retirements(catalog):
    """{retired_id: {successor, effective, set_id, batch, reason}} from authoring_amendments.

    Fails closed: a malformed record raises CatalogError, so the app never guesses
    which revision is current. A catalog without amendments retires nothing.
    """
    batches = catalog.get('authoring_amendments', [])
    location = 'authoring_amendments'
    require(isinstance(batches, list), location, 'list required')
    revisions = {r['id']: r for r in catalog['revisions']}
    sets = {s['id']: s for s in catalog['sets']}
    result, batch_ids = {}, set()
    for batch in batches:
        require(isinstance(batch, dict), location, 'object batches required')
        text(batch.get('id'), location + '.id')
        where = f"{location}.{batch['id']}"
        require(batch['id'] not in batch_ids, where, 'duplicate batch id')
        batch_ids.add(batch['id'])
        amendments = batch.get('amendments')
        require(isinstance(amendments, list) and bool(amendments), where, 'nonempty amendments list required')
        for amendment in amendments:
            require(isinstance(amendment, dict), where, 'object amendments required')
            for field in ('set_id', 'retired_revision_id', 'successor_revision_id', 'reason'):
                text(amendment.get(field), f'{where}.{field}')
            old_id, new_id = amendment['retired_revision_id'], amendment['successor_revision_id']
            old, new = revisions.get(old_id), revisions.get(new_id)
            require(old is not None, where, f'unknown retired revision {old_id}')
            require(new is not None, where, f'unknown successor revision {new_id}')
            require(old['set_id'] == new['set_id'] == amendment['set_id'], where,
                    f'{old_id} and {new_id} must both belong to {amendment["set_id"]}')
            require(new['version_order'] > old['version_order'], where, f'successor {new_id} is not newer than {old_id}')
            require(old_id not in result, where, f'{old_id} is retired more than once')
            result[old_id] = {'successor': new_id, 'set_id': amendment['set_id'], 'batch': batch['id'],
                              'reason': amendment['reason']}
    for old_id, info in result.items():
        head, seen = info['successor'], {old_id}
        while head in result:
            require(head not in seen, location, f'retirement cycle through {head}')
            seen.add(head)
            head = result[head]['successor']
        require(revisions[head]['composition_kind'] != 'equipment_options', location,
                f'{old_id} resolves to equipment options {head}')
        info['effective'] = head
    for set_id in {info['set_id'] for info in result.values()}:
        group = sets.get(set_id)
        require(group is not None, location, f'unknown conceptual set {set_id}')
        default = group.get('default_revision_id')
        require(default not in result, set_id, f'default revision {default} is retired')
        unretired = [r for r in revisions.values() if r['set_id'] == set_id and r['id'] not in result]
        require(len(unretired) == 1 or default is not None, set_id,
                'more than one unretired revision; an explicit default_revision_id is required')
    return result


def effective_revision_id(catalog, revision_id):
    """The current head for a revision id: itself unless retired."""
    info = (catalog.get('_retirements') or {}).get(revision_id)
    return info['effective'] if info else revision_id


class CatalogStore:
    """In-memory candidate publication. Failed preparation leaves state intact."""
    def __init__(self):
        self._catalog = None
        self._history = {'revisions': [], 'sets': [], 'sources': []}

    @property
    def catalog(self):
        return deepcopy(self._catalog)

    def prepare(self, raw, **validation):
        try:
            candidate = validate_catalog(decode_json(raw), previous=self._history, **validation)
        except (TypeError, KeyError, AttributeError) as error:
            raise CatalogError(f'catalog: malformed candidate ({error})') from error
        for field in ('revisions', 'sets', 'sources'):
            known = {r['id'] for r in self._history[field]}
            self._history[field].extend(deepcopy(r) for r in candidate[field] if r['id'] not in known)
        self._catalog = candidate
        return self.catalog


def materialize_revision(revision):
    require(revision.get('composition_kind') != 'equipment_options', revision.get('id'),
            'equipment options cannot become a simultaneous target')
    return deepcopy(revision)


def resolve_reference(target, catalog):
    """Saved snapshots win; latest ordering never retargets personal work.

    Status order: unavailable_source, conflicting_revision, retired, current.
    For retired, effective_revision_id(catalog, revision_id) names the head to review.
    """
    snapshot = deepcopy(target['snapshot'])
    found = next((r for r in catalog['revisions'] if r['id'] == target['revision_id']
                  and r['set_id'] == target['set_id']), None)
    if found is None:
        return snapshot, 'unavailable_source'
    if found != snapshot:
        return snapshot, 'conflicting_revision'
    return snapshot, 'retired' if target['revision_id'] in (catalog.get('_retirements') or {}) else 'current'


def normalize_legacy(target, revisions=()):
    """Display-only association. No slot guessing and no source-file mutations.

    Only a complete exact revision snapshot proves an association. Old per-item
    guideTarget rows, even with matching IDs, cannot establish full set identity.
    """
    original = deepcopy(target)
    snapshot = target.get('snapshot')
    matches = [r for r in revisions if snapshot == r and r.get('set_id') == target.get('set_id')]
    explicit = target.get('revision_id')
    conflicting = explicit and any(r['id'] == explicit for r in revisions) and not matches
    return {'original': original, 'status': 'proven' if len(matches) == 1 else
            'conflicting' if conflicting or len(matches) > 1 else 'unresolved',
            'revision_id': matches[0]['id'] if len(matches) == 1 else None}


def normalize_source_grid(cells):
    """Source 4x4 order; category placeholders omit slots rather than invent empties."""
    require(isinstance(cells, list) and len(cells) == 16, 'grid', '16 source cells required')
    result = []
    for slot, cell in zip(SLOTS, cells):
        require(isinstance(cell, dict), slot, 'source cell object required')
        if cell.get('kind') in ('category', 'omitted'):
            continue
        require(cell.get('kind') == 'item', slot, 'unknown source cell kind')
        result.append({'slot': slot, 'state': 'selected', 'item_id': cell.get('item_id'),
                       'requirements': deepcopy(cell.get('requirements', {}))})
    return normalize_slots(result)
