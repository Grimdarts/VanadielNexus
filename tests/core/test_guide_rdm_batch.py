"""Independent RDM action, recipient, buff and physical-copy checks."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from vanadiel_nexus.core.equipment_effects import SourceSnapshot, evaluate
from vanadiel_nexus.core.equipment_hands import hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS, allocate_requirements, requirements_match
from vanadiel_nexus.core.guide_catalog import composition_diagnostics, validate_catalog
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
    source = SourceSnapshot('fictional-rdm-public-fixture', (), packet['fingerprint'],
                            MappingProxyType(items), MappingProxyType({int(k): v for k, v in packet['descriptions'].items()}),
                            hand_types=hand_types(items))
    return catalog, source


def revision(catalog, key):
    return next(r for r in catalog['revisions'] if r['set_id'] == 'nexus:rdm:' + key)


def slots(catalog, key):
    return {s['slot']: s for s in revision(catalog, key)['slots']}


def context(catalog, key):
    return next(s['context'] for s in catalog['sets'] if s['id'] == 'nexus:rdm:' + key)


def test_rdm_preserves_all_81_prior_revisions_and_107_sources(batch):
    catalog, _ = batch
    baseline = catalog['authoring_batches'][4]['baseline_record_hashes']
    assert len(baseline['sets']) == len(baseline['revisions']) == 81
    assert len(baseline['sources']) == 107
    for field in ('sets', 'revisions', 'sources'):
        current = {r['id']: r for r in catalog[field]}
        assert all(digest(current[key]) == stamp for key, stamp in baseline[field].items())


def test_full_rdm_compositions_do_not_imply_complete_effects(batch):
    catalog, source = batch
    validate_catalog(catalog, items=source.items, hand_types=source.hand_types)
    rows = [r for r in catalog['revisions'] if r['set_id'].startswith('nexus:rdm:')]
    assert len(rows) == 38
    for row in rows:
        assert row['origin'] == 'nexus_recommendation' and row['verification']['status'] == 'verified'
        assert {s['slot'] for s in row['slots']} == set(SLOTS)
        assert next(s for s in row['slots'] if s['slot'] == 'range') == {'slot': 'range', 'state': 'empty'}
        for slot in row['slots']:
            if slot['state'] == 'selected':
                assert slot['name'] == source.items[slot['item_id']].en
        result = evaluate(row['slots'], source, job='RDM', context=context(catalog, row['set_id'].split(':')[-1]))
        assert not result.diagnostics
        assert result.unresolved


def test_all_accepted_rdm_priorities_and_other_job_gaps_remain(batch):
    catalog, _ = batch
    rows = [r for r in catalog['coverage'] if r['job'] == 'RDM']
    assert len(rows) == 18 and all(r['status'] == 'included' and r['set_ids'] for r in rows)
    assert {'DT Idle', 'Refresh Idle', 'Engaged Balanced', 'Engaged DT', 'Engaged Accuracy',
            'Enspell', 'WS', 'Enfeebling potency', 'Enfeebling accuracy', 'Enhancing', 'Precast'} <= {r['priority'] for r in rows}
    gaps = [r for r in catalog['coverage'] if r['job'] not in ('WHM', 'SCH', 'BLM', 'RDM', 'GEO', 'BRD', 'RNG', 'SAM', 'NIN', 'SMN', 'BLU', 'COR', 'RUN', 'PLD', 'DRK', 'WAR', 'MNK', 'THF', 'DRG', 'BST', 'PUP', 'DNC')]
    assert len(gaps) == 0 and all(r['status'] == 'gap' for r in gaps)
    assert not any(r['status'] == 'not_applicable' for r in catalog['coverage'])


def test_source_turtle_options_and_seraph_conflict_are_not_repaired_as_authorship(batch):
    catalog, _ = batch
    rows = read('gear-guide-t7-rdm-observations.json')['observations']
    assert len(rows) == 33
    for row in rows:
        stamp = row.pop('observation_sha256')
        assert digest(row) == stamp
        if row['item_set'] in (404156, 375670, 404364):
            # Preserve the deficient initial capture; the append-only correction
            # below records every repeated/conflicting macro line explicitly.
            assert row['occupied_slot_count'] == len(row['selected_names']) + 1
        else:
            assert row['occupied_slot_count'] == len(row['selected_names'])
        assert set(row['omitted_slots']) == set(SLOTS) - set(row['selected_names'])
    tables = {r['item_set']: r for r in rows}
    assert tables[402064]['classification'] == 'equipment_options'
    assert tables[402064]['selected_names']['head'] == 'Sworn Crown'
    assert tables[399008]['classification'] == 'main_hand_action_conflict'
    assert tables[399008]['selected_names']['main'] == 'Daybreak'
    assert tables[399008]['selected_names']['sub'] == 'Crocea Mors'
    assert slots(catalog, 'dt-idle')['head']['item_id'] == 23761
    assert slots(catalog, 'seraph')['main']['item_id'] == 21621
    assert slots(catalog, 'seraph')['sub']['item_id'] == 22040
    assert revision(catalog, 'seraph')['origin'] == 'nexus_recommendation'


def test_ordered_macro_corrections_preserve_conflicts_and_old_source_records(batch):
    catalog, _ = batch
    packet = read('gear-guide-t7-rdm-observations.json')
    originals = {r['item_set']: r for r in packet['observations']}
    corrections = {r['item_set']: r for r in packet['corrections']}
    assert set(corrections) == {404156, 375670, 404364}
    for key, row in corrections.items():
        stamp = row.pop('observation_sha256')
        assert digest(row) == stamp
        assert row['supersedes_observation_sha256'] == originals[key]['observation_sha256']
        assert len(row['macro_selections']) == row['macro_line_count']
        assert row['occupied_slot_count'] == len(row['slot_options'])
        assert set(row['omitted_slots']) == set(SLOTS) - set(row['slot_options'])
    assert corrections[404156]['slot_options']['ammo'] == ['Pemphredo Tathlum', 'Ghastly Tathlum +1']
    assert 'ammo' not in corrections[404156]['selected_names']
    assert corrections[404364]['slot_options']['waist'] == ['Grunfeld Rope', 'Sailfi Belt +1']
    assert 'waist' not in corrections[404364]['selected_names']
    assert corrections[375670]['slot_options']['legs'] == ['Shedir Seraweels']
    assert corrections[375670]['duplicate_slots']['legs'] == 2
    sources = {r['id']: r for r in catalog['sources']}
    rdm_amendments = [r for r in catalog['source_observation_amendments'] if r['source_id'].startswith('rdm:')]
    assert len(rdm_amendments) == 3
    for row in rdm_amendments:
        assert row['source_id'] in sources and row['supersedes_source_id'] in sources
        assert row['related_revision_ids']
    assert slots(catalog, 'burst')['ammo']['name'] == 'Pemphredo Tathlum'
    assert slots(catalog, 'tp-balanced')['waist']['name'] == 'Grunfeld Rope'


def test_refresh_avoids_unreported_random_augments_and_conditional_recovery(batch):
    catalog, _ = batch
    rows = slots(catalog, 'refresh-idle')
    assert rows['head']['item_id'] == 23402 and rows['body']['item_id'] == 23491
    assert rows['ammo']['item_id'] == 22268 and rows['main']['item_id'] == 22040
    assert rows['ring1']['item_id'] == rows['ring2']['item_id'] == 26184
    assert not {s['item_id'] for s in rows.values() if s['state'] == 'selected'} & {11697, 28452}
    assert all(s.get('requirements', {}) == {} for s in rows.values())


@pytest.mark.parametrize('key', ['tp-balanced-dw', 'tp-dt-dw', 'tp-accuracy-dw', 'savage-dw', 'seraph', 'sanguine', 'enspell'])
def test_dual_wield_is_an_explicit_usable_trait_assumption(batch, key):
    catalog, source = batch
    row = revision(catalog, key)
    declared = context(catalog, key)
    assert declared['dual_wield'] is True and '99/49' in declared['job']
    assert not composition_diagnostics(row['slots'], source.items, ['RDM'], hand_types=source.hand_types, context=declared)
    missing = deepcopy(declared)
    missing.pop('dual_wield')
    assert 'main/sub: dual wield is unconfirmed' in composition_diagnostics(row['slots'], source.items, ['RDM'], hand_types=source.hand_types, context=missing)


def test_single_wield_sets_do_not_inherit_dw_gear_or_offhand_protection(batch):
    catalog, _ = batch
    for key in ('tp-balanced', 'tp-dt', 'tp-accuracy'):
        assert slots(catalog, key)['sub']['item_id'] == 27645
        assert context(catalog, key).get('dual_wield') is not True
    assert slots(catalog, 'tp-dt')['back']['item_id'] == 26268
    assert slots(catalog, 'tp-dt-dw')['back']['item_id'] == 26250
    assert slots(catalog, 'tp-dt-dw')['back']['requirements']['augments'][-1] == '"Dual Wield"+10'


def test_enspell_snapshot_and_normal_melee_are_not_zero_tp_strategy(batch):
    catalog, _ = batch
    rows = slots(catalog, 'enspell')
    assert rows['main']['item_id'] == 20614 and rows['main']['requirements'] == {}
    assert rows['head']['item_id'] == 27721 and rows['back']['item_id'] == 28621
    assert 'Tier-I' in context(catalog, 'enspell')['spell']
    assert 'not tier-II' in revision(catalog, 'enhancing-skill')['rationale']
    assert 'zero-TP-feed' in revision(catalog, 'enspell')['rationale']


def test_spell_gifts_and_recipient_conditions_remain_explicit(batch):
    catalog, _ = batch
    assert '550-JP' in context(catalog, 'enfeebling-skill')['spell']
    assert '1200-JP' in context(catalog, 'enhancing-skill')['spell']
    assert '1200-JP' in context(catalog, 'refresh-others')['spell']
    assert 'RDM/SCH 99/49' in context(catalog, 'cursna')['spell']
    assert 'Addendum: White' in context(catalog, 'cursna')['spell']


def test_saboteur_and_stat_specific_capes_cannot_be_conflated(batch):
    catalog, _ = batch
    assert slots(catalog, 'enfeebling-mnd')['hands']['item_id'] == 25827
    assert slots(catalog, 'saboteur-mnd')['hands']['item_id'] == 23558
    assert slots(catalog, 'saboteur-int')['hands']['item_id'] == 23558
    assert context(catalog, 'enfeebling-mnd')['saboteur'] == 'Inactive'
    assert 'Active' in context(catalog, 'saboteur-mnd')['saboteur']
    mnd = slots(catalog, 'saboteur-mnd')['back']['requirements']
    actual_int = slots(catalog, 'saboteur-int')['back']['requirements']
    assert not requirements_match(mnd, actual_int)
    assert not requirements_match(actual_int, mnd)


def test_duration_vs_immunobreak_keeps_gear_tradeoff(batch):
    catalog, _ = batch
    assert slots(catalog, 'enfeebling-duration')['legs']['item_id'] == 23625
    assert slots(catalog, 'enfeebling-immunobreak')['legs']['item_id'] == 25844
    assert slots(catalog, 'enfeebling-immunobreak')['legs']['requirements'] == {}
    assert 'not guaranteed' in revision(catalog, 'enfeebling-immunobreak')['rationale']


def test_self_and_other_composure_duration_membership_differ(batch):
    catalog, _ = batch
    assert context(catalog, 'enhancing-self')['target'] == 'Self'
    assert context(catalog, 'enhancing-others')['target'] == 'Other player'
    assert context(catalog, 'enhancing-others')['composure'] == 'Active'
    assert slots(catalog, 'enhancing-self')['body']['item_id'] == 23469
    assert slots(catalog, 'enhancing-others')['body']['item_id'] == 23491
    assert slots(catalog, 'enhancing-others')['hands']['item_id'] == 23513
    for slot in ('head', 'legs'):
        target = slots(catalog, 'enhancing-self')[slot]['requirements']
        assert target == {'augments': ['Enh. Mag. eff. dur. +10']}
        assert not requirements_match(target, {'augments': 'Enh. Mag. eff. dur. +9'})


def test_refresh_self_received_waist_is_not_passed_to_other_target(batch):
    catalog, _ = batch
    assert slots(catalog, 'refresh-self')['waist']['name'] == 'Gishdubar Sash'
    assert slots(catalog, 'refresh-others')['waist']['name'] == 'Embla Sash'
    for key in ('refresh-self', 'refresh-others'):
        assert slots(catalog, key)['body']['item_id'] == 23446
        assert slots(catalog, key)['legs']['item_id'] == 23625


def test_phalanx_received_is_self_only_and_per_physical_copy(batch):
    catalog, _ = batch
    rows = slots(catalog, 'phalanx-self')
    assert rows['main']['item_id'] == 21637 and rows['main']['requirements'] == {}
    for slot in ('head', 'hands', 'feet'):
        assert rows[slot]['requirements'] == {'augments': ['Phalanx +3']}
        assert not requirements_match(rows[slot]['requirements'], {'augments': 'Phalanx +2'})
    other = slots(catalog, 'phalanx-others')
    assert other['main']['item_id'] == 20614
    assert not any('Phalanx' in a for row in other.values() for a in row.get('requirements', {}).get('augments', []))
    assert context(catalog, 'phalanx-others')['target'] == 'Other player'


def test_sword_vs_club_ws_and_noncrocea_stat_capes_are_explicit(batch):
    catalog, _ = batch
    assert slots(catalog, 'black-halo')['main']['item_id'] == 22031
    assert slots(catalog, 'black-halo')['back']['requirements']['augments'][0] == 'MND+20'
    assert slots(catalog, 'savage')['main']['item_id'] == 21621
    assert slots(catalog, 'savage')['back']['requirements']['augments'][0] == 'STR+20'
    assert slots(catalog, 'sanguine')['back']['requirements']['augments'][0] == 'INT+20'
    assert slots(catalog, 'seraph')['back']['requirements']['augments'][0] == 'MND+20'
    for key in ('savage', 'savage-dw', 'black-halo', 'sanguine', 'seraph'):
        assert slots(catalog, key)['body']['requirements'] == {'rank': 15, 'path': 'B'}
    assert 'non-Crocea' in revision(catalog, 'sanguine')['rationale']


@pytest.mark.parametrize('key', ['refresh-idle', 'enhancing-skill', 'enfeebling-accuracy', 'tp-balanced-dw', 'cursna'])
def test_paired_rings_cannot_reuse_one_owned_copy(batch, key):
    catalog, _ = batch
    row = slots(catalog, key)
    pair = [row['ring1'], row['ring2']]
    assert pair[0]['item_id'] == pair[1]['item_id']
    owned = [{'character_key': 'fictional', 'item_id': pair[0]['item_id'], 'bag_id': 8}]
    assert sum(r['owned'] for r in allocate_requirements(pair, owned, 'fictional').values()) == 1


def test_sird_and_fast_cast_cape_requirements_are_distinct(batch):
    catalog, _ = batch
    fc = slots(catalog, 'fast-cast')['back']['requirements']
    sird = slots(catalog, 'sird')['back']['requirements']
    assert fc == {'augments': ['"Fast Cast"+10']}
    assert sird == {'augments': ['Spell interruption rate down -10%']}
    assert not requirements_match(fc, sird) and not requirements_match(sird, fc)


def test_new_hand_records_match_only_exact_reviewed_classifications(batch):
    _, source = batch
    for item_id in (21621, 20614, 21637):
        item = source.items[item_id]
        assert source.hand_types[item_id] == 'one_handed'
        assert not hand_types({item_id: replace(item, skill=11)})
        assert not hand_types({item_id: replace(item, slots=1)})
        assert not hand_types({999999: replace(item, id=999999)})


def test_new_public_card_hashes_and_names_match_detached_evidence():
    packet = read('gear-guide-t7-rdm-item-evidence.json')
    resources = read('gear-guide-t7-resource-evidence.json')
    assert len(packet['items']) == 42
    assert '403' in packet['source_access']['bgwiki']
    for row in packet['items']:
        stamp = row.pop('observation_sha256')
        assert digest(row) == stamp
        assert row['public_card_name'] == row['resource_name']
        assert len(row['public_card_sha256']) == 64
        assert hashlib.sha256(resources['descriptions'][str(row['item_id'])].encode()).hexdigest() == row['resource_description_sha256']
