"""Runtime retirement of superseded guide revisions (GEAR-GUIDE-T7-RUNTIME-RETIREMENT-DESIGN.md).

Fictional catalogs prove each rule; the actual candidate is read, never written.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from vanadiel_nexus.core import gear_guides, gear_workspace as ws
from vanadiel_nexus.core.equipment_hands import hand_types
from vanadiel_nexus.core.guide_catalog import (
    CatalogError, effective_revision_id, resolve_reference, retirements, validate_catalog)
from vanadiel_nexus.core.item_res import Item

CATALOG = Path(__file__).resolve().parents[2] / 'docs/catalog'
ITEMS = {101: Item(101, 'Fictional Ring', slots=1 << 13, jobs=1 << 5),
         102: Item(102, 'Fictional Band', slots=1 << 13, jobs=1 << 5)}


def revision(rid, order, *, set_id='s', item=101, augments=None, kind='partial_loadout'):
    row = {'id': rid, 'set_id': set_id, 'label': 'Fictional', 'equipment_version': 'Tier',
           'version_order': order, 'origin': 'nexus_recommendation', 'currency': 'current',
           'resource_fingerprint': 'fictional',
           'verification': {'status': 'fixture-only', 'checked_on': '2026-11-05', 'scope': 'Fictional'},
           'source_ids': ['src'], 'assumptions': ['Fictional'], 'rationale': 'Fictional',
           'composition_kind': kind}
    if kind == 'equipment_options':
        row['options'] = [{'item_id': item, 'requirements': {}}]
    else:
        requirements = {'augments': augments} if augments else {}
        row['slots'] = [{'slot': 'ring1', 'state': 'selected', 'item_id': item, 'requirements': requirements},
                        {'slot': 'head', 'state': 'empty'}]
    return row


def amendment(retired, successor, set_id='s'):
    return {'set_id': set_id, 'retired_revision_id': retired, 'successor_revision_id': successor,
            'reason': 'Fictional correction'}


def catalog(revisions=None, amendments=None, *, default=None, extra_sets=()):
    group = {'id': 's', 'jobs': ['RDM'], 'purpose': 'Idle', 'target': 'Fictional idle', 'context': {}}
    if default:
        group['default_revision_id'] = default
    value = {'schema_version': 2, 'coverage': [],
             'sources': [{'id': 'src', 'kind': 'fixture', 'url': None, 'title': 'Fictional',
                          'locator': 'Row', 'accessed_on': '2026-11-05'}],
             'sets': [group, *extra_sets],
             'revisions': revisions if revisions is not None else
             [revision('s:v1', 1, augments=['DEX+30']), revision('s:v2', 2, augments=['DEX+20', 'AGI+10'])]}
    if amendments is not False:
        value['authoring_amendments'] = [{'id': 'fictional-fix-2026-11-05',
                                          'amendments': amendments or [amendment('s:v1', 's:v2')]}]
    return value


def prepare(value):
    return validate_catalog(value, items=ITEMS, fixture=True)


@pytest.fixture(scope='module')
def actual():
    raw = json.loads((CATALOG / 'gear-guide-t7-candidate.json').read_text(encoding='utf-8'))
    evidence = json.loads((CATALOG / 'gear-guide-t7-resource-evidence.json').read_text(encoding='utf-8'))
    items = {r['id']: Item(**r) for r in evidence['items']}
    return raw, validate_catalog(raw, items=items, hand_types=hand_types(items))


# 1
def test_actual_candidate_has_27_retired_ids_and_25_effective_heads(actual):
    raw, prepared = actual
    found = retirements(raw)
    assert prepared['_retirements'] == found
    assert len(found) == 27
    assert len({r['set_id'] for r in found.values()}) == 25
    heads = {r['effective'] for r in found.values()}
    assert len(heads) == 25 and not heads & set(found)
    assert {r['batch'] for r in found.values()} == {
        'brd-augment-parts-2026-11-04', 'bst-provenance-2026-11-05', 'bst-ear-labels-2026-11-05',
        'scope-fallback-2026-11-05'}
    by_id = {r['id']: r for r in raw['revisions']}
    for set_id in ('nexus:bst:engaged-balanced', 'nexus:bst:engaged-accuracy'):
        chain = [k for k, v in found.items() if v['set_id'] == set_id]
        assert len(chain) == 2
        assert {by_id[found[k]['effective']]['version_order'] for k in chain} == {3}
    stored = sum(r['verification']['status'] == 'verified' for r in raw['revisions'])
    effective = sum(r['verification']['status'] == 'verified' and r['id'] not in found for r in raw['revisions'])
    assert (stored, effective) == (539, 512)


# 2
@pytest.mark.parametrize('case', ['unknown_retired', 'unknown_successor', 'set_mismatch', 'not_newer',
                                  'two_successors', 'cycle', 'options_head', 'retired_default',
                                  'two_unretired_no_default', 'missing_field', 'not_a_list', 'empty_batch',
                                  'duplicate_batch'])
def test_malformed_amendments_fail_closed(case):
    revisions = [revision('s:v1', 1), revision('s:v2', 2)]
    amendments = [amendment('s:v1', 's:v2')]
    extra, default = (), None
    if case == 'unknown_retired':
        amendments = [amendment('s:missing', 's:v2')]
    elif case == 'unknown_successor':
        amendments = [amendment('s:v1', 's:missing')]
    elif case == 'set_mismatch':
        extra = [{'id': 't', 'jobs': ['RDM'], 'purpose': 'Idle', 'target': 'Other', 'context': {}}]
        revisions.append(revision('t:v1', 3, set_id='t'))
        amendments = [amendment('s:v1', 't:v1')]
    elif case == 'not_newer':
        revisions[1]['version_order'] = 1
    elif case == 'two_successors':
        revisions.append(revision('s:v3', 3))
        amendments = [amendment('s:v1', 's:v2'), amendment('s:v1', 's:v3'), amendment('s:v2', 's:v3')]
    elif case == 'cycle':
        revisions.append(revision('s:v3', 3))
        # v2 -> v3 -> v1 -> v2. Strict version ordering already rejects any cycle;
        # the chain walk is a second guard, so this only proves the result fails closed.
        revisions[0]['version_order'] = 4
        amendments = [amendment('s:v2', 's:v3'), amendment('s:v3', 's:v1'), amendment('s:v1', 's:v2')]
    elif case == 'options_head':
        revisions[1] = revision('s:v2', 2, kind='equipment_options')
    elif case == 'retired_default':
        default = 's:v1'
    elif case == 'two_unretired_no_default':
        revisions.append(revision('s:v3', 3))
    value = catalog(revisions, amendments, default=default, extra_sets=extra)
    if case == 'missing_field':
        del value['authoring_amendments'][0]['amendments'][0]['reason']
    elif case == 'not_a_list':
        value['authoring_amendments'] = {'id': 'x'}
    elif case == 'empty_batch':
        value['authoring_amendments'][0]['amendments'] = []
    elif case == 'duplicate_batch':
        value['revisions'].append(revision('s:v3', 3))
        value['authoring_amendments'].append({'id': 'fictional-fix-2026-11-05',
                                              'amendments': [amendment('s:v2', 's:v3')]})
    with pytest.raises(CatalogError):
        prepare(value)


def test_two_unretired_revisions_with_an_effective_default_are_admitted():
    value = catalog([revision('s:v1', 1), revision('s:v2', 2), revision('s:v3', 3)], default='s:v3')
    prepared = prepare(value)
    assert prepared['_retirements']['s:v1']['effective'] == 's:v2'
    assert [r['id'] for r in gear_guides.revision_tree(prepared, 'RDM')['Idle']['s']] == ['s:v3', 's:v2']


# 3
def test_no_amendments_gives_empty_map_and_unchanged_tree():
    value = catalog([revision('s:v1', 1), revision('s:v2', 2)], amendments=False)
    prepared = prepare(value)
    assert prepared['_retirements'] == {} and retirements(value) == {}
    assert [r['id'] for r in gear_guides.revision_tree(prepared, 'RDM')['Idle']['s']] == ['s:v1', 's:v2']


# 4
def test_actual_tree_lists_only_effective_heads(actual):
    _, prepared = actual
    found = prepared['_retirements']
    listed = {}
    for job in {j for s in prepared['sets'] for j in s['jobs']}:
        for groups in gear_guides.revision_tree(prepared, job).values():
            for set_id, revisions in groups.items():
                listed[set_id] = [r['id'] for r in revisions]
    assert not {rid for ids in listed.values() for rid in ids} & set(found)
    for info in found.values():
        assert listed[info['set_id']] == [info['effective']]
    assert all(len(ids) == 1 for ids in listed.values())


def test_chain_reviews_straight_to_the_head():
    value = catalog([revision('s:v1', 1), revision('s:v2', 2), revision('s:v3', 3)],
                    [amendment('s:v1', 's:v2'), amendment('s:v2', 's:v3')])
    prepared = prepare(value)
    assert {k: v['effective'] for k, v in prepared['_retirements'].items()} == {'s:v1': 's:v3', 's:v2': 's:v3'}
    assert prepared['_retirements']['s:v1']['successor'] == 's:v2'
    assert effective_revision_id(prepared, 's:v1') == 's:v3'
    assert effective_revision_id(prepared, 's:v3') == 's:v3'


# 5
def test_resolve_reference_status_order():
    prepared = prepare(catalog())
    old = ws.prepare_target(prepared, 's:v1', target_id='t', character_key='Alice')
    new = ws.prepare_target(prepared, 's:v2', target_id='t', character_key='Alice')
    assert resolve_reference(old, prepared) == (old['snapshot'], 'retired')
    assert effective_revision_id(prepared, old['revision_id']) == 's:v2'
    assert resolve_reference(new, prepared) == (new['snapshot'], 'current')
    changed = deepcopy(prepared)
    changed['revisions'][0]['rationale'] = 'Edited in place'
    assert resolve_reference(old, changed)[1] == 'conflicting_revision'
    missing = deepcopy(prepared)
    missing['revisions'] = missing['revisions'][1:]
    assert resolve_reference(old, missing)[1] == 'unavailable_source'


# 6
def test_adoption_from_retired_keeps_personal_choices_and_removed_slot_still_blocks():
    prepared = prepare(catalog())
    target = ws.prepare_target(prepared, 's:v1', target_id='t', character_key='Alice',
                               bindings=[{'slot': 'ring1', 'bag_id': 8}])
    target['overrides'] = [{'slot': 'ring1', 'requirements': {'rank': 3}}]
    workspace = {**ws.empty_workspace(), 'targets': [target]}
    proposal, delta = ws.prepare_adoption(workspace, 't', prepared, effective_revision_id(prepared, 's:v1'))
    adopted = proposal['targets'][0]
    assert adopted['revision_id'] == 's:v2' and delta['before']['revision_id'] == 's:v1'
    assert adopted['bindings'] == target['bindings'] and adopted['overrides'] == target['overrides']
    removed = deepcopy(catalog())
    removed['revisions'][1]['slots'] = [{'slot': 'head', 'state': 'empty'}]
    removed = prepare(removed)
    with pytest.raises(ValueError):
        ws.prepare_adoption(workspace, 't', removed, 's:v2')


# 7
def test_validation_is_idempotent_and_derived_key_never_persists(tmp_path):
    once = prepare(catalog())
    assert prepare(once) == once
    assert '_retirements' not in catalog()
    target = ws.prepare_target(once, 's:v1', target_id='t', character_key='Alice')
    store = ws.WorkspaceStore(tmp_path / ws.BASENAME)
    store.load()
    store.save({**ws.empty_workspace(), 'targets': [target]})
    assert '_retirements' not in store.path.read_text(encoding='utf-8')
    # Revision immutability compares revisions only; the derived map is not part of it.
    from vanadiel_nexus.core.guide_catalog import CatalogStore
    history = CatalogStore()
    history.prepare(json.dumps(catalog()), items=ITEMS, fixture=True)
    later = catalog()
    later['authoring_amendments'][0]['amendments'][0]['reason'] = 'Reworded reason'
    assert history.prepare(json.dumps(later), items=ITEMS, fixture=True)['_retirements']['s:v1']['reason'] == 'Reworded reason'


def test_authoring_save_never_writes_the_derived_map(actual):
    from tools import prepare_guide_catalog as authoring
    raw, prepared = actual
    stored = json.loads(authoring.serialize(prepared))
    assert '_retirements' not in stored
    assert set(stored) == set(raw)
