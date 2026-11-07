"""BLM context/prerequisite regressions using detached public resources only."""
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from vanadiel_nexus.core.equipment_effects import SourceSnapshot, evaluate
from vanadiel_nexus.core.equipment_hands import hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS, allocate_requirements, requirements_match
from vanadiel_nexus.core.guide_catalog import validate_catalog
from vanadiel_nexus.core.item_res import Item

FOLDER = Path(__file__).resolve().parents[2] / 'docs/catalog'


def read(name):
    return json.loads((FOLDER / name).read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


@pytest.fixture
def batch():
    catalog = read('gear-guide-t7-candidate.json')
    packet = read('gear-guide-t7-resource-evidence.json')
    items = {r['id']: Item(**r) for r in packet['items']}
    source = SourceSnapshot('fictional-public-fixture', (), packet['fingerprint'],
                            MappingProxyType(items), MappingProxyType({int(k): v for k, v in packet['descriptions'].items()}),
                            hand_types=hand_types(items))
    return catalog, source


def revision(catalog, key):
    return next(r for r in catalog['revisions'] if r['set_id'] == 'nexus:blm:' + key)


def slots(catalog, key):
    return {r['slot']: r for r in revision(catalog, key)['slots']}


def context(catalog, key):
    return next(s['context'] for s in catalog['sets'] if s['id'] == 'nexus:blm:' + key)


def test_blm_preserves_all_59_previous_revisions_and_57_sources(batch):
    catalog, _ = batch
    baseline = catalog['authoring_batches'][3]['baseline_record_hashes']
    assert len(baseline['sets']) == len(baseline['revisions']) == 59
    assert len(baseline['sources']) == 57
    for field in ('sets', 'revisions', 'sources'):
        current = {r['id']: r for r in catalog[field]}
        assert all(digest(current[key]) == fingerprint for key, fingerprint in baseline[field].items())


def test_blm_full_compositions_remain_numerically_incomplete(batch):
    catalog, source = batch
    validate_catalog(catalog, items=source.items, hand_types=source.hand_types)
    rows = [r for r in catalog['revisions'] if r['set_id'].startswith('nexus:blm:')]
    assert len(rows) == 22
    for row in rows:
        assert row['origin'] == 'nexus_recommendation' and row['verification']['status'] == 'verified'
        assert {s['slot'] for s in row['slots']} == set(SLOTS)
        assert next(s for s in row['slots'] if s['slot'] == 'range') == {'slot': 'range', 'state': 'empty'}
        for slot in row['slots']:
            if slot['state'] == 'selected':
                assert slot['name'] == source.items[slot['item_id']].en
        result = evaluate(row['slots'], source, job='BLM', context=context(catalog, row['set_id'].split(':')[-1]))
        assert not result.diagnostics
        assert result.unresolved  # Composition authoring never implements new numeric rules.


def test_blm_coverage_keeps_other_jobs_open(batch):
    catalog, _ = batch
    rows = [r for r in catalog['coverage'] if r['job'] == 'BLM']
    assert len(rows) == 15 and all(r['status'] == 'included' and r['set_ids'] for r in rows)
    assert {'Mana Wall', 'Death MP staging', 'Myrkr', 'Occult Acumen', 'Engaged Balanced',
            'Engaged DT', 'Engaged Accuracy', 'Physical WS'} <= {r['priority'] for r in rows}
    assert all(r['status'] == 'gap' for r in catalog['coverage'] if r['job'] not in ('WHM', 'SCH', 'BLM', 'RDM', 'GEO', 'BRD', 'RNG', 'SAM', 'NIN', 'SMN', 'BLU', 'COR', 'RUN', 'PLD', 'DRK', 'WAR', 'MNK', 'THF', 'DRG', 'BST', 'PUP', 'DNC'))
    assert not any(r['status'] == 'not_applicable' for r in catalog['coverage'])


def test_observations_keep_omissions_and_live_changes_distinct():
    rows = read('gear-guide-t7-blm-observations.json')['observations']
    assert len(rows) == 13
    for row in rows:
        stamp = row.pop('observation_sha256')
        assert digest(row) == stamp
        assert row['occupied_slot_count'] == len(row['selected_names']) == 15
        assert row['omitted_slots'] == ['range']
    tables = {r['item_set']: r for r in rows}
    assert tables[347384]['selected_names']['feet'] == 'Wicce Sabots +1'
    assert tables[351869]['selected_names']['main'] == "Bunzi's Rod"
    assert tables[351869]['selected_names']['hands'] == "Agwu's Gages"
    assert tables[402041]['selected_names']['main'] == 'Khatvanga'
    assert tables[402042]['selected_names']['ear1'] == 'Moonshade Earring'


def test_mana_wall_retention_is_separate_from_ordinary_idle(batch):
    catalog, _ = batch
    wall = slots(catalog, 'mana-wall')
    assert wall['feet']['item_id'] == 23691 and wall['back']['item_id'] == 26249
    assert wall['back']['requirements'] == {}  # Mana Wall is base cape effect.
    assert 'active' in context(catalog, 'mana-wall')['buff']
    assert slots(catalog, 'dt-idle')['feet']['item_id'] == 23789
    refresh = slots(catalog, 'refresh-idle')
    assert refresh['body']['item_id'] == 23490
    assert refresh['hands']['item_id'] != 27141 and refresh['feet']['item_id'] != 27497
    assert refresh['ring1']['item_id'] == refresh['ring2']['item_id'] == 26184


def test_elemental_conversion_does_not_silently_apply_to_death(batch):
    catalog, _ = batch
    for key in ('free-nuke-mp', 'burst-mp'):
        assert slots(catalog, key)['body']['item_id'] == 23445
        assert 'elemental' in context(catalog, key)['spell']
    assert slots(catalog, 'death-burst')['body']['item_id'] != 23445
    assert '1200 JP' in context(catalog, 'death-burst')['spell']
    assert 'MP continuity' in context(catalog, 'death-precast')['mp']
    assert 'General spell' in context(catalog, 'fast-cast')['spell']


def test_comet_and_death_keep_school_and_burst_contexts(batch):
    catalog, _ = batch
    for key in ('comet-free', 'comet-burst', 'death-burst'):
        assert slots(catalog, key)['head']['item_id'] == 26696
        assert slots(catalog, key)['ring2']['item_id'] == 11674
    assert 'no burst' in context(catalog, 'comet-free')['spell']
    assert 'burst' in context(catalog, 'comet-burst')['spell']
    assert 'Dark Magic Death' in revision(catalog, 'death-burst')['rationale']


def test_mp_and_fc_requirements_must_exist_on_same_cape(batch):
    catalog, _ = batch
    target = slots(catalog, 'death-precast')['back']['requirements']
    assert set(target['augments']) == {'MP+80', '"Fast Cast"+10'}
    assert not requirements_match(target, {'augments': 'MP+80'})
    assert not requirements_match(target, {'augments': '"Fast Cast"+10'})
    assert requirements_match(target, {'augments': ['MP+80', '"Fast Cast"+10']})
    for key in ('death-burst', 'myrkr'):
        for slot in ('body', 'legs', 'feet'):
            assert slots(catalog, key)[slot]['requirements'] == {'augments': ['MP+80']}


def test_occult_acumen_minimums_do_not_inherit_source_tp_breakpoints(batch):
    catalog, _ = batch
    rows = slots(catalog, 'occult-acumen')
    for slot in ('body', 'hands', 'feet'):
        assert rows[slot]['requirements'] == {'augments': ['"Occult Acumen"+11']}
        assert not requirements_match(rows[slot]['requirements'], {'augments': '"Occult Acumen"+10'})
    assert rows['main']['item_id'] == 22100 and rows['sub']['item_id'] == 22218
    assert 'No 1000TP' in context(catalog, 'occult-acumen')['mp']
    assert rows['back']['item_id'] == 26274


@pytest.mark.parametrize('key', ['refresh-idle', 'enfeebling', 'tp-balanced', 'tp-accuracy'])
def test_duplicate_ring_slots_require_two_copies(batch, key):
    catalog, _ = batch
    rows = slots(catalog, key)
    pair = [rows['ring1'], rows['ring2']]
    assert pair[0]['item_id'] == pair[1]['item_id']
    owned = [{'character_key': 'fictional', 'item_id': pair[0]['item_id'], 'bag_id': 8}]
    assert sum(r['owned'] for r in allocate_requirements(pair, owned, 'fictional').values()) == 1


def test_melee_and_ws_have_distinct_rank_and_access_prerequisites(batch):
    catalog, _ = batch
    assert slots(catalog, 'tp-balanced')['hands']['requirements'] == {'rank': 15}
    assert slots(catalog, 'tp-dt')['hands']['item_id'] == 23775
    assert slots(catalog, 'tp-dt')['ring1']['item_id'] == 13566
    for slot in ('head', 'body', 'hands', 'legs', 'feet'):
        assert slots(catalog, 'shattersoul')[slot]['requirements'] == {'rank': 15, 'path': 'B'}
    assert '357' in context(catalog, 'shattersoul')['ability']
    assert 'permanently unlocked' in context(catalog, 'myrkr')['ability']


def test_new_public_item_packet_does_not_claim_browser_or_augment_reads():
    packet = read('gear-guide-t7-blm-item-evidence.json')
    assert len(packet['items']) == 33
    assert 'not read' in packet['source_access']['bgwiki']
    assert 'disabled' in packet['source_access']['browser']
    assert all('No augment/rank effects' in r['scope'] for r in packet['items'])
    assert all(len(r['resource_description_sha256']) == 64 for r in packet['items'])
    resources = read('gear-guide-t7-resource-evidence.json')
    for row in packet['items']:
        stamp = row.pop('observation_sha256')
        assert digest(row) == stamp
        assert row['public_card_name'] == row['resource_name']
        assert len(row['public_card_sha256']) == 64
        assert hashlib.sha256(resources['descriptions'][str(row['item_id'])].encode()).hexdigest() == row['resource_description_sha256']
