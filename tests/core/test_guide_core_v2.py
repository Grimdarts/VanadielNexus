"""Independent fictional T1 compatibility oracles; never read player snapshots."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import subprocess
import sys

import pytest

from vanadiel_nexus.core.equipment_matching import (
    SLOTS, _preferred_matching, allocate_requirements, equip_match, requirements_match)
from vanadiel_nexus.core.guide_catalog import (
    CatalogError, CatalogStore, JOBS, composition_diagnostics, decode_json,
    materialize_revision, normalize_legacy, normalize_slots, normalize_source_grid,
    resolve_reference, validate_catalog)
from vanadiel_nexus.core.item_res import Item
from vanadiel_nexus.core import gear_workspace as ws


@pytest.fixture
def candidate():
    return {
        'schema_version': 2,
        'sources': [{'id': 'fictional-source', 'kind': 'fixture', 'url': None, 'title': 'Fictional café'}],
        'sets': [{'id': 'fictional-idle', 'jobs': ['RDM'], 'purpose': 'Idle',
                  'target': 'Refresh Idle', 'context': {}, 'default_revision_id': 'r1'}],
        'revisions': [{
            'id': 'r1', 'set_id': 'fictional-idle', 'label': 'Fictional partial recovery',
            'equipment_version': 'Test', 'version_order': 1, 'origin': 'source_adaptation',
            'currency': 'unknown', 'resource_fingerprint': 'fictional-resource-v1',
            'verification': {'status': 'fixture-only', 'checked_on': '2026-11-03', 'scope': 'Fictional test'},
            'source_ids': ['fictional-source'], 'assumptions': ['Fictional condition'],
            'rationale': 'Independent compatibility example', 'composition_kind': 'partial_loadout',
            'slots': [{'slot': 'ring1', 'state': 'selected', 'item_id': 101, 'requirements': {}},
                      {'slot': 'ring2', 'state': 'selected', 'item_id': 101, 'requirements': {}}]}],
        'coverage': []}


@pytest.fixture
def resources():
    return {101: Item(101, 'Fictional Ring', slots=1 << 13, jobs=1 << 5)}


def prepare(candidate, resources):
    return validate_catalog(candidate, items=resources, fixture=True)


def target_workspace(candidate, resources):
    catalog = prepare(candidate, resources)
    target = ws.prepare_target(catalog, 'r1', target_id='target-a', character_key='character-a',
                               bindings=[{'slot': 'ring1', 'bag_id': 8}, {'slot': 'ring2', 'bag_id': 10}])
    return {**ws.empty_workspace(), 'targets': [target]}


@pytest.mark.parametrize('first,second', [('set_manager', 'gear_guides'), ('gear_guides', 'set_manager')])
def test_both_import_orders(first, second):
    code = (f'from vanadiel_nexus.core import {first}, {second}; '
            'from vanadiel_nexus.core import set_manager as s, gear_guides as g; '
            'assert s.identity is g.identity; assert s.equip_match([], [])')
    subprocess.run([sys.executable, '-c', code], check=True, capture_output=True)


def test_alias_collision_and_ambiguous_eligibility(candidate):
    slots = candidate['revisions'][0]['slots']
    slots[0]['slot'], slots[1]['slot'] = 'left_ring', 'RING1'
    with pytest.raises(CatalogError, match='duplicate canonical'):
        normalize_slots(slots, aliases=True)
    slots[1]['slot'] = 'right_ring'
    assert [s['slot'] for s in normalize_slots(slots, aliases=True)] == ['ring1', 'ring2']
    slots[0]['slot'] = 'left_ring/right_ring'
    with pytest.raises(ValueError, match='ambiguous'):
        normalize_slots(slots, aliases=True)


def test_strict_policy_no_rare_rank_shortcut_or_cross_copy_augments():
    requirement = {'rank': 20, 'path': 'B', 'augments': ['A+1', 'B+2']}
    a = {'augments': 'Rank 20, Path: B, A+1'}
    b = {'augments': 'Rank 20, Path: B, B+2'}
    assert equip_match(['A+1', 'B+2', 'Rank 99'], a['augments'], rare=True)
    assert not requirements_match(requirement, a)
    assert not requirements_match(requirement, b)
    combined = {'augments': 'Rank 20, Path: B, A+1, B+2'}
    original = deepcopy(combined)
    assert requirements_match(requirement, combined)
    assert not requirements_match({**requirement, 'rank': 21}, combined)
    assert not requirements_match({**requirement, 'path': 'A'}, combined)
    assert not requirements_match({'augments': ['A+1']}, {'augments': 'A+10'})
    assert not requirements_match({'augments': ['A+1', 'A+1']}, {'augments': 'A+1'})
    assert combined == original


def test_distinct_copies_character_and_designated_bags(candidate):
    slots = candidate['revisions'][0]['slots']
    bindings = [{'slot': 'ring1', 'bag_id': 8}, {'slot': 'ring2', 'bag_id': 10}]
    rows = [{'item_id': 101, 'character_key': 'character-a', 'bag_id': 8},
            {'item_id': 101, 'character_key': 'character-a', 'bag_id': 10}]
    result = allocate_requirements(slots, rows, 'character-a', bindings, equippable_bag_ids={8, 10, 11})
    assert all(r['owned'] and r['ready'] for r in result.values())
    assert {r['unit'] for r in result.values()} == {0, 1}
    result = allocate_requirements(slots, rows[:1], 'character-a', bindings, equippable_bag_ids={8, 10, 11})
    assert sum(r['owned'] for r in result.values()) == 1
    assert result['ring1']['ready'] and not result['ring2']['ready']
    rows[1]['bag_id'] = 11
    result = allocate_requirements(slots, rows, 'character-a', bindings, equippable_bag_ids={8, 10, 11})
    assert all(r['owned'] for r in result.values()) and not result['ring2']['ready']
    assert bindings[1]['bag_id'] == 10
    rows[1]['character_key'] = 'character-b'
    assert sum(r['owned'] for r in allocate_requirements(slots, rows, 'character-a').values()) == 1
    rows = [{'item_id': 101, 'character_key': 'character-a', 'bag_id': 8, 'count': 2}]
    assert all(r['ambiguous'] and r['owned'] for r in allocate_requirements(
        slots, rows, 'character-a', equippable_bag_ids={8}).values())
    assert not any(r['ready'] for r in allocate_requirements(slots, rows, 'character-a').values())
    rows[0]['count'] = 0
    with pytest.raises(ValueError, match='count'):
        allocate_requirements(slots, rows, 'character-a')


def test_ready_and_owned_share_one_feasible_allocation(candidate):
    slots = candidate['revisions'][0]['slots']
    # Both ask for the same copy; only ring2 has the correct saved bag.
    result = allocate_requirements(slots, [{'item_id': 101, 'character_key': 'a', 'bag_id': 8}],
                                   'a', [{'slot': 'ring1', 'bag_id': 10}, {'slot': 'ring2', 'bag_id': 8}],
                                   equippable_bag_ids={8, 10})
    assert not result['ring1']['owned'] and not result['ring1']['ready']
    assert result['ring2']['owned'] and result['ring2']['ready']
    # Ready matching must move to an alternative to preserve the other copy.
    slots[0]['requirements'] = {'augments': ['A+1']}
    rows = [{'item_id': 101, 'character_key': 'a', 'bag_id': 8, 'augments': 'A+1'},
            {'item_id': 101, 'character_key': 'a', 'bag_id': 10}]
    result = allocate_requirements(slots, rows, 'a', equippable_bag_ids={8, 10})
    assert result['ring1']['unit'] == 0 and result['ring2']['unit'] == 1


def test_all_small_allocation_graphs_against_exhaustive_independent_oracle():
    # 729 possible absent/owned/ready graphs, three slots and two physical units.
    # Enumerate every legal assignment independently of the assignment algorithm.
    for edges in product(range(3), repeat=6):
        candidates = {s: [i for i in range(2) if edges[2 * s + i] > 0] for s in range(3)}
        ready = {s: [i for i in range(2) if edges[2 * s + i] == 2] for s in range(3)}
        expected = (-1, -1)
        for assignment in product((None, 0, 1), repeat=3):
            units = [i for i in assignment if i is not None]
            if len(units) != len(set(units)) or any(i is not None and i not in candidates[s]
                                                     for s, i in enumerate(assignment)):
                continue
            expected = max(expected, (sum(i in ready[s] for s, i in enumerate(assignment)), len(units)))
        selected = _preferred_matching(range(3), candidates, ready)
        assert (sum(i in ready[s] for s, i in selected.items()), len(selected)) == expected


@pytest.mark.parametrize('raw', ['{"schema_version":2,"schema_version":2}',
                               '{"a":{"x":1,"x":2}}', '{"a":NaN}', '{broken'])
def test_json_collisions_and_invalid_input(raw):
    with pytest.raises(CatalogError):
        decode_json(raw)


@pytest.mark.parametrize('field,value', [
    ('composition_kind', 'unknown'), ('source_ids', ['absent']), ('set_id', 'absent'),
    ('origin', 'guide-guessed'), ('currency', 'best'), ('resource_fingerprint', ''),
    ('version_order', True), ('verification', {'status': 'verified'}),
    ('assumptions', 'not a list')])
def test_malformed_candidate_never_publishes(candidate, resources, field, value):
    store = CatalogStore()
    original = store.prepare(json.dumps(candidate), items=resources, fixture=True)
    candidate['revisions'][0][field] = value
    with pytest.raises(CatalogError):
        store.prepare(json.dumps(candidate), items=resources, fixture=True)
    assert store.catalog == original
    original['sets'].clear()
    assert store.catalog['sets']


def test_revision_addition_reordering_retirement_and_conflict(candidate, resources):
    store = CatalogStore()
    first = store.prepare(json.dumps(candidate), items=resources, fixture=True)
    saved = ws.prepare_target(first, 'r1', target_id='target-a', character_key='character-a')
    saved_bytes = json.dumps(saved)
    second = deepcopy(candidate['revisions'][0])
    second['id'], second['label'] = 'r2', 'Fictional second revision'
    second['slots'][0]['requirements'] = {'rank': 20}
    candidate['revisions'].insert(0, second)
    candidate['sets'][0]['default_revision_id'] = 'r2'
    current = store.prepare(json.dumps(candidate), items=resources, fixture=True)
    assert resolve_reference(saved, current) == (saved['snapshot'], 'current')
    candidate['revisions'] = [second]
    retired = store.prepare(json.dumps(candidate), items=resources, fixture=True)
    assert resolve_reference(saved, retired) == (saved['snapshot'], 'unavailable_source')
    conflict = deepcopy(first['revisions'][0]); conflict['label'] = 'Changed under same ID'
    candidate['revisions'].append(conflict)
    with pytest.raises(CatalogError, match='immutable'):
        store.prepare(json.dumps(candidate), items=resources, fixture=True)
    assert json.dumps(saved) == saved_bytes
    proposal, delta = ws.prepare_adoption({**ws.empty_workspace(), 'targets': [saved]}, 'target-a', current, 'r2')
    assert delta['before']['revision_id'] == 'r1'
    assert delta['after']['revision_id'] == 'r2'
    assert proposal['targets'][0]['snapshot']['slots'][0]['requirements'] == {'rank': 20}
    assert json.dumps(saved) == saved_bytes


def test_legacy_normalization_never_infers_ring_slots(candidate):
    row = {'id': 'old', 'slot': 'left_ring/right_ring', 'guideTarget': {'item_id': 101}}
    original = deepcopy(row)
    normalized = normalize_legacy(row, candidate['revisions'])
    assert normalized == {'original': row, 'status': 'unresolved', 'revision_id': None}
    normalized['original']['guideTarget']['item_id'] = 999
    assert row == original
    exact = {'set_id': 'fictional-idle', 'snapshot': deepcopy(candidate['revisions'][0])}
    assert normalize_legacy(exact, candidate['revisions'])['status'] == 'proven'
    exact['revision_id'] = 'r1'
    exact['snapshot']['slots'][0]['requirements'] = {'rank': 99}
    assert normalize_legacy(exact, candidate['revisions'])['status'] == 'conflicting'


def test_options_stay_references_and_personal_composition_preserves_origin(candidate, resources):
    revision = candidate['revisions'][0]
    revision['composition_kind'] = 'equipment_options'
    revision['options'] = [{'item_id': 101, 'requirements': {}}, {'item_id': 101, 'requirements': {'rank': 5}}]
    revision['slots'] = []
    catalog = prepare(candidate, resources)
    original = deepcopy(catalog)
    with pytest.raises(CatalogError, match='options'):
        materialize_revision(catalog['revisions'][0])
    with pytest.raises(CatalogError):
        ws.prepare_target(catalog, 'r1', target_id='a', character_key='character-a')
    draft = {'id': 'personal', 'revision': 1, 'character_key': 'character-a', 'mode': 'planning',
             'slots': [{'slot': 'ring1', 'state': 'selected', 'item_id': 101,
                        'requirements': {'rank': 5}, 'requirement_origin': 'assumed'}],
             'bindings': [], 'scenario': {}, 'source_references': [{'source_id': 'fictional-source'}]}
    assert ws.validate_workspace({**ws.empty_workspace(), 'drafts': [draft]})['drafts'] == [draft]
    assert catalog == original
    revision['slots'] = [{'slot': 'ring1', 'state': 'selected', 'item_id': 101, 'requirements': {}}]
    with pytest.raises(CatalogError, match='options'):
        prepare(candidate, resources)


def test_partial_grid_unknown_empty_omitted_and_two_rings(candidate, resources):
    cells = [{'kind': 'omitted'} for _ in range(16)]
    cells[2] = {'kind': 'category', 'label': 'Ranged placeholder'}
    for slot in ('head', 'neck', 'ear1', 'ear2', 'body', 'hands', 'ring1', 'ring2', 'back', 'waist'):
        cells[SLOTS.index(slot)] = {'kind': 'item', 'item_id': 101}
    normalized = normalize_source_grid(cells)
    assert len(normalized) == 10
    assert {s['slot'] for s in normalized if s['item_id'] == 101} >= {'ring1', 'ring2'}
    assert 'range' not in {s['slot'] for s in normalized}
    states = normalize_slots([{'slot': 'main', 'state': 'empty'},
                              {'slot': 'sub', 'state': 'unknown', 'diagnostic': 'source unresolved'}])
    assert states == [{'slot': 'main', 'state': 'empty'},
                      {'slot': 'sub', 'state': 'unknown', 'diagnostic': 'source unresolved'}]
    assert 'range' not in {s['slot'] for s in states}
    # Independent ten-slot eligibility fixture, not real DNC gear.
    for n, slot in enumerate(normalized):
        item_id = 101 if slot['slot'].startswith('ring') else 200 + n
        slot['item_id'] = item_id
        bit = {'head': 4, 'neck': 9, 'ear1': 11, 'ear2': 12, 'body': 5,
               'hands': 6, 'ring1': 13, 'ring2': 14, 'back': 15, 'waist': 10}[slot['slot']]
        resources[item_id] = Item(item_id, 'Fictional gear', slots=1 << bit, jobs=1 << 5)
    candidate['revisions'][0]['slots'] = normalized
    candidate['revisions'][0]['assumptions'] = ['Shell is assumed, not equipment']
    catalog = prepare(candidate, resources)
    assert len(catalog['revisions'][0]['slots']) == 10
    assert catalog['revisions'][0]['assumptions'] == ['Shell is assumed, not equipment']
    assert catalog['revisions'][0]['composition_kind'] == 'partial_loadout'


def test_cross_slot_staff_shield_rejects_and_grip_control_preserves_observations(candidate, resources):
    resources.update({201: Item(201, 'Fictional staff', slots=1, jobs=1 << 5),
                      202: Item(202, 'Fictional shield', slots=2, jobs=1 << 5),
                      203: Item(203, 'Fictional grip', slots=2, jobs=1 << 5)})
    slots = [{'slot': 'main', 'state': 'selected', 'item_id': 201, 'requirements': {}},
             {'slot': 'sub', 'state': 'selected', 'item_id': 202, 'requirements': {}}]
    candidate['revisions'][0]['slots'] = slots
    original = deepcopy(slots)
    hands = {201: 'two_handed', 202: 'shield', 203: 'grip'}
    with pytest.raises(CatalogError, match='incompatible'):
        validate_catalog(candidate, items=resources, hand_types=hands, fixture=True)
    assert slots == original
    assert composition_diagnostics(slots, resources, ['RDM']) == ['main/sub: unresolved weapon legality']
    slots[1]['item_id'] = 203
    assert validate_catalog(candidate, items=resources, hand_types=hands, fixture=True)


def test_production_rejects_fixture_metadata_and_requires_coverage(candidate, resources):
    with pytest.raises(CatalogError, match='source kind'):
        validate_catalog(candidate, items=resources)
    candidate['sources'][0].update(kind='ffxiah', url='https://www.ffxiah.com/item-sets/123',
                                    title='Fictional evidence', locator='Fictional row', accessed_on='2026-11-03')
    with pytest.raises(CatalogError, match='verification'):
        validate_catalog(candidate, items=resources)
    candidate['revisions'][0]['verification']['status'] = 'unresolved'
    with pytest.raises(CatalogError, match='22 jobs'):
        validate_catalog(candidate, items=resources)
    candidate['coverage'] = [{'job': j, 'priority': p, 'status': 'gap', 'reviewed': True,
                              'context': 'Fictional context', 'evidence': 'Fictional review',
                              'reason': 'T7 authoring remains open'}
                             for j in JOBS for p in ('DT Idle', 'Refresh Idle')]
    assert validate_catalog(candidate, items=resources)
    candidate['sources'][0]['url'] = 'https://www.ffxiah.com.evil.example/item-sets/123'
    with pytest.raises(CatalogError, match='URL'):
        validate_catalog(candidate, items=resources)


def test_save_reopen_and_detached_publication(tmp_path, candidate, resources, monkeypatch):
    monkeypatch.setenv('VN_DATA_DIR', str(tmp_path))
    store = ws.WorkspaceStore.for_user(characters={'character-a'})
    assert store.load().status == 'missing'
    assert not store.path.exists()
    proposal = target_workspace(candidate, resources)
    result = store.save(proposal)
    assert result == proposal == store.data
    result['targets'].clear(); proposal['targets'].clear()
    assert len(store.data['targets']) == 1
    reopened = ws.WorkspaceStore(store.path, characters={'character-a'})
    assert reopened.load().status == 'ok'
    assert reopened.data == store.data
    assert reopened.data['targets'][0]['bindings'] == [{'slot': 'ring1', 'bag_id': 8}, {'slot': 'ring2', 'bag_id': 10}]


@pytest.mark.parametrize('failure', ['serialize', 'temp', 'backup', 'replace'])
@pytest.mark.parametrize('entity', ['target', 'draft'])
def test_failed_write_preserves_disk_and_memory(tmp_path, candidate, resources, monkeypatch, failure, entity):
    store = ws.WorkspaceStore(tmp_path / ws.BASENAME)
    store.load(); store.save(target_workspace(candidate, resources))
    before, memory = store.path.read_bytes(), store.data
    proposal = store.data; proposal['targets'][0]['bindings'][0]['bag_id'] = 11
    if entity == 'draft':
        proposal['drafts'] = [{'id': 'draft-a', 'revision': 1, 'character_key': 'character-a', 'mode': 'planning',
                               'slots': [{'slot': 'main', 'state': 'unknown', 'diagnostic': 'Fictional gap'}],
                               'bindings': [], 'scenario': {}, 'source_references': []}]
    def fail(*args, **kwargs):
        raise OSError('Injected ' + failure)
    if failure == 'serialize':
        monkeypatch.setattr(ws.json, 'dumps', fail)
    elif failure == 'temp':
        monkeypatch.setattr(ws, '_write_temp', fail)
    elif failure == 'backup':
        monkeypatch.setattr(ws.shutil, 'copy2', fail)
    else:
        monkeypatch.setattr(ws.os, 'replace', fail)
    with pytest.raises(OSError, match='Injected'):
        store.save(proposal)
    assert store.path.read_bytes() == before
    assert store.data == memory
    assert store.pending == proposal
    assert not list(tmp_path.glob('*.tmp'))


def test_partial_temp_and_backup_failures_preserve_authoritative_primary(tmp_path, monkeypatch):
    store = ws.WorkspaceStore(tmp_path / ws.BASENAME)
    store.load(); store.save(ws.empty_workspace())
    before = store.path.read_bytes()
    def fail_sync(*args):
        raise OSError('partial temp flush')
    with monkeypatch.context() as patch:
        patch.setattr(ws.os, 'fsync', fail_sync)
        with pytest.raises(OSError, match='flush'):
            store.save(ws.empty_workspace())
    assert store.path.read_bytes() == before and not list(tmp_path.glob('*.tmp'))
    def partial_backup(source, destination):
        destination.write_bytes(b'{partial backup')
        raise OSError('partial backup copy')
    with monkeypatch.context() as patch:
        patch.setattr(ws.shutil, 'copy2', partial_backup)
        with pytest.raises(OSError, match='backup'):
            store.save(ws.empty_workspace())
    assert store.backup.read_bytes() == b'{partial backup'
    assert store.path.read_bytes() == before and store.data == ws.empty_workspace()
    assert ws.WorkspaceStore(store.path).load().status == 'ok'
    store.save(ws.empty_workspace())  # a retry under the same unchanged primary is safe


def test_immutable_saved_snapshot_and_explicit_adoption_transaction(tmp_path, candidate, resources, monkeypatch):
    store = ws.WorkspaceStore(tmp_path / ws.BASENAME, characters={'character-a'})
    store.load(); store.save(target_workspace(candidate, resources))
    before = store.data; disk = store.path.read_bytes()
    changed = store.data; changed['targets'][0]['snapshot']['slots'][0]['requirements'] = {'rank': 20}
    with pytest.raises(CatalogError, match='immutable'):
        store.save(changed)
    second = deepcopy(candidate['revisions'][0]); second['id'] = 'r2'
    second['slots'][0]['requirements'] = {'rank': 20}
    candidate['revisions'].append(second)
    proposal, delta = ws.prepare_adoption(store.data, 'target-a', prepare(candidate, resources), 'r2')
    assert store.data == before and store.path.read_bytes() == disk
    with monkeypatch.context() as patch:
        patch.setattr(ws.os, 'replace', lambda *a: (_ for _ in ()).throw(OSError('replace failed')))
        with pytest.raises(OSError):
            store.save(proposal)
    assert store.data == before and store.path.read_bytes() == disk
    store.save(proposal)
    assert store.data['targets'][0]['revision_id'] == 'r2'
    assert store.data['targets'][0]['bindings'] == before['targets'][0]['bindings']
    assert delta['before'] == before['targets'][0]


@pytest.mark.parametrize('primary,backup,status', [
    (None, None, 'missing'), (b'{bad', None, 'corrupt'), (b'{bad', b'{bad', 'corrupt'),
    (b'{bad', b'VALID', 'recovery_available'), (None, b'VALID', 'recovery_available'),
    (b'{"schema_version":2}', b'VALID', 'unsupported'),
    (b'{bad', b'{"schema_version":2}', 'unsupported')])
def test_read_recovery_versions_are_nonmutating(tmp_path, primary, backup, status):
    path = tmp_path / ws.BASENAME
    for file, value in ((path, primary), (path.with_name(path.name + '.bak'), backup)):
        if value is not None:
            file.write_bytes(json.dumps(ws.empty_workspace()).encode() if value == b'VALID' else value)
    # Crash debris is never a committed workspace.
    (tmp_path / (ws.BASENAME + '.leftover.tmp')).write_bytes(b'{"schema_version":1}')
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    store = ws.WorkspaceStore(path)
    assert store.load().status == status
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    if status != 'missing':
        with pytest.raises(ws.WorkspaceError):
            store.save(ws.empty_workspace())
    if status == 'recovery_available':
        assert store.data is None and store.recovery == ws.empty_workspace()
        store.save(store.recovery, accept_recovery=True)
        if primary is not None:
            assert any(p.read_bytes() == primary for p in tmp_path.glob('*.evidence'))
        assert ws.WorkspaceStore(path).load().status == 'ok'


def test_two_writers_stale_generation_and_locked_interleaving(tmp_path):
    path = tmp_path / ws.BASENAME
    a, b = ws.WorkspaceStore(path), ws.WorkspaceStore(path)
    a.load(); b.load(); a.save(ws.empty_workspace())
    with pytest.raises(ws.WorkspaceConflict, match='changed since load'):
        b.save(ws.empty_workspace())
    assert b.pending == ws.empty_workspace()
    assert b.data == ws.empty_workspace()  # its own prior missing generation
    b.load()
    # Actual second process holds the same OS lock while b attempts a save.
    script = ('import sys; from pathlib import Path; '
              'from vanadiel_nexus.core.gear_workspace import writer_lock; '
              'lock=writer_lock(Path(sys.argv[1])); lock.__enter__(); '
              'print("LOCKED", flush=True); sys.stdin.readline(); lock.__exit__(None,None,None)')
    process = subprocess.Popen([sys.executable, '-c', script, str(path) + '.lock'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == 'LOCKED'
        with pytest.raises(ws.WorkspaceConflict, match='another writer'):
            b.save(ws.empty_workspace())
    finally:
        process.communicate('\n', timeout=10)
    b.save(ws.empty_workspace())


@pytest.mark.parametrize('recovery', ['none', 'good_backup', 'both_bad'])
def test_pinned_old_app_writes_and_recovery_preserve_workspace_bytes(tmp_path, candidate, resources, recovery):
    # Legacy modules are unchanged from the pinned handoff. Prove that before
    # exercising them; subprocess source hashes catch accidental future drift.
    from vanadiel_nexus.core.database import Database
    from vanadiel_nexus.core.settings import Settings
    for module in ('database', 'settings', 'jsonfile'):
        relative = f'vanadiel_nexus/core/{module}.py'
        pinned = subprocess.run(['git', 'show', f'5657f20:{relative}'], check=True, capture_output=True).stdout
        assert Path(relative).read_bytes().replace(b'\r\n', b'\n') == pinned.replace(b'\r\n', b'\n')
    workspace = target_workspace(candidate, resources)
    raw = ('  ' + json.dumps(workspace, ensure_ascii=False, indent=3) + '\n').encode('utf-8')
    path = tmp_path / ws.BASENAME; path.write_bytes(raw)
    path.with_name(path.name + '.bak').write_bytes(raw + b'\n')
    path.with_name(path.name + '.unreadable').write_bytes(b'fictional old evidence')
    files = {p: p.read_bytes() for p in tmp_path.iterdir()}
    database_path = tmp_path / 'ffxi_database.json'
    database_path.write_text('{broken' if recovery != 'none' else '{"schema_version":2}', encoding='utf-8')
    if recovery != 'none':
        database_path.with_name(database_path.name + '.bak').write_text(
            '{"schema_version":2,"fictional":"retained"}' if recovery == 'good_backup' else '{broken backup',
            encoding='utf-8')
    (tmp_path / 'settings.json').write_text('{"guide_picks":{"RDM":{"set":"old"}}}', encoding='utf-8')
    db = Database(str(tmp_path))
    db.data['wishlist'].append({'id': 'fictional-wish', 'name': 'Fictional item', 'job': 'RDM'})
    db.save()
    Settings(str(tmp_path)).set('last_page', 'guides')
    for file, original in files.items():
        assert file.read_bytes() == original
    store = ws.WorkspaceStore(path)
    assert store.load().status == 'ok' and store.data == workspace
