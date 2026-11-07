"""Independent WHM authoring checks; public detached evidence, no player data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from vanadiel_nexus.core.equipment_effects import SourceSnapshot, evaluate
from vanadiel_nexus.core.equipment_hands import hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS, allocate_requirements, requirements_match
from vanadiel_nexus.core.guide_catalog import CatalogError, composition_diagnostics, normalize_slots, validate_catalog
from vanadiel_nexus.core.item_res import Item


FOLDER = Path(__file__).resolve().parents[2] / 'docs/catalog'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


@pytest.fixture
def batch():
    catalog = json.loads((FOLDER / 'gear-guide-t7-candidate.json').read_text(encoding='utf-8'))
    evidence = json.loads((FOLDER / 'gear-guide-t7-resource-evidence.json').read_text(encoding='utf-8'))
    items = {r['id']:Item(**r) for r in evidence['items']}
    descriptions = {int(k):v for k,v in evidence['descriptions'].items()}
    source = SourceSnapshot('fictional-public-fixture', (), evidence['fingerprint'],
                            MappingProxyType(items), MappingProxyType(descriptions), hand_types=hand_types(items))
    return catalog, source


def by_key(catalog, key):
    return next(r for r in catalog['revisions'] if r['set_id'] == 'nexus:whm:' + key)


def slots(revision):
    return {r['slot']:r for r in revision['slots']}


def test_previous_source_set_and_revision_records_are_unchanged(batch):
    catalog, _ = batch
    for index, expected in enumerate((8,23)):
        history = catalog['authoring_batches'][index]['baseline_record_hashes']
        assert len(history['revisions']) == expected
        for field in ('sources', 'sets', 'revisions'):
            current = {r['id']:r for r in catalog[field]}
            assert all(digest(current[key]) == fingerprint for key,fingerprint in history[field].items())


def test_verified_nexus_loadouts_are_explicit_and_legally_evaluable(batch):
    catalog, source = batch
    validate_catalog(catalog, items=source.items, hand_types=source.hand_types)
    recommendations = [r for r in catalog['revisions'] if r['origin'] == 'nexus_recommendation'
                       and r['set_id'].startswith('nexus:whm:')]
    assert len(recommendations) == 23
    for revision in recommendations:
        assert revision['set_id'].startswith('nexus:whm:') and revision['verification']['status'] == 'verified'
        assert revision['composition_kind'] == 'loadout'
        assert {r['slot'] for r in revision['slots']} == set(SLOTS)
        assert slots(revision)['range'] == {'slot':'range', 'state':'empty'}
        for row in revision['slots']:
            assert row['state'] != 'unknown'
            if row['state'] == 'selected':
                assert row['name'] == source.items[row['item_id']].en
        # Legality succeeds without enabling unsupported new numeric formulas.
        group = next(s for s in catalog['sets'] if s['id'] == revision['set_id'])
        result = evaluate(revision['slots'], source, job='WHM', context=group['context'])
        assert not result.diagnostics
        assert result.unresolved  # A verified composition is not full effect coverage.


def test_whm_backline_inclusion_does_not_erase_niche_engaged_obligations(batch):
    catalog, _ = batch
    coverage = {r['priority']:r for r in catalog['coverage'] if r['job'] == 'WHM'}
    assert {p for p,r in coverage.items() if r['status']=='included'} == {
        'DT Idle','Refresh Idle','Cure','Status removal / Cursna','Enhancing','Precast',
        'Engaged Balanced','Engaged DT','Engaged Accuracy','Physical WS'}
    assert not {p for p,r in coverage.items() if r['status']=='gap'}
    revisions = {r['set_id']:r for r in catalog['revisions']}
    for row in coverage.values():
        assert row['status'] != 'not_applicable'
        for ref in row['set_ids']:
            assert revisions[ref]['verification']['status'] == 'verified'


def test_exact_requirements_no_potential_augments_or_unity_guesses(batch):
    catalog, source = batch
    fc = slots(by_key(catalog, 'fast-cast'))
    assert fc['head']['requirements'] == {'rank':15, 'path':'D'}
    assert fc['back']['requirements'] == {'augments':['"Fast Cast"+10']}
    assert fc['hands']['item_id'] == 28021 and fc['hands']['name'] == 'Gende. Gages +1'
    assert fc['ear2']['item_id'] == 26088 and fc['ear2']['name'] == 'Malignance Earring'
    assert fc['ring2']['item_id'] == 26188 and fc['ring2']['name'] == 'Kishar Ring'
    assert fc['feet']['item_id'] == 28274 and fc['feet']['requirements'] == {}
    cursna = slots(by_key(catalog, 'cursna'))
    assert cursna['head']['requirements'] == cursna['feet']['requirements'] == {'rank':15,'path':'B'}
    assert cursna['hands']['item_id'] == 27136 and cursna['hands']['requirements'] == {}
    assert 'Fast Cast' not in source.descriptions[27136]
    assert cursna['ear1']['item_id'] == 26098 and cursna['ear1']['name'] == 'Meili Earring'
    assert cursna['ear2']['item_id'] == 25433 and 'Right ear' in source.descriptions[25433]
    refresh_ids = {r.get('item_id') for r in by_key(catalog, 'refresh-idle')['slots']}
    assert not refresh_ids & {11697,28135,28452}  # no Moonshade, Unity legs or Fucho dependency


def test_duration_augments_and_vanya_paths_use_strict_owned_requirements(batch):
    catalog, _ = batch
    duration = slots(by_key(catalog, 'enhancing-duration'))
    for key in ('head','body','hands','legs'):
        requirement = duration[key]['requirements']
        assert requirement == {'augments':['Enh. Mag. eff. dur. +10']}
        assert not requirements_match(requirement, {'augments':'Enh. Mag. eff. dur. +9'})
        assert requirements_match(requirement, {'augments':'Enh. Mag. eff. dur. +10'})
    requirement = slots(by_key(catalog, 'fast-cast'))['head']['requirements']
    assert requirements_match(requirement, {'augments':'Rank 15, Path: D'})
    assert not requirements_match(requirement, {'augments':'Rank 14, Path: D'})
    assert not requirements_match(requirement, {'augments':'Rank 15, Path: B'})


def test_duplicate_rings_and_cure_curaga_status_contexts_remain_distinct(batch):
    catalog, _ = batch
    cursna = by_key(catalog, 'cursna')
    pair = [s for s in cursna['slots'] if s['slot'] in ('ring1','ring2')]
    assert [s['item_id'] for s in pair] == [10790,10790]
    result = allocate_requirements(pair, [{'character_key':'fictional','item_id':10790,'bag_id':8}], 'fictional')
    assert sum(r['owned'] for r in result.values()) == 1
    assert slots(by_key(catalog, 'cure'))['body']['item_id'] == 26903
    assert slots(by_key(catalog, 'curaga'))['body']['item_id'] == 23444
    assert slots(by_key(catalog, 'cure'))['back']['item_id'] == 26248
    assert slots(by_key(catalog, 'curaga'))['back']['item_id'] == 26268
    assert slots(by_key(catalog, 'status-single'))['main']['item_id'] == 22040
    assert slots(by_key(catalog, 'status-yagrush75'))['main']['item_id'] == 18973
    assert slots(by_key(catalog, 'divine-caress'))['hands']['item_id'] == 23556


def test_source_conflicting_heads_and_omissions_stay_observations():
    packet = json.loads((FOLDER / 'gear-guide-t7-whm-observations.json').read_text(encoding='utf-8'))
    assert len(packet['observations']) == 13
    for row in packet['observations']:
        saved = deepcopy(row)
        fingerprint = saved.pop('observation_sha256')
        assert digest(saved) == fingerprint
    conflict = next(r for r in packet['observations'] if r['id'] == '373991')
    assert [s['item_id'] for s in conflict['macro_rows'] if s['slot']=='head'] == [26797,23422]
    assert [s['item_id'] for s in conflict['gear_rows'] if s['slot']=='head'] == [23422]
    with pytest.raises(CatalogError, match='duplicate canonical slot'):
        normalize_slots([{**s,'state':'selected','requirements':{}} for s in conflict['macro_rows']])
    fc = next(r for r in packet['observations'] if r['id'] == '373971')
    assert 'main' not in {s['slot'] for s in fc['macro_rows']}
    assert 'sub' in {s['slot'] for s in fc['macro_rows']}


@pytest.mark.parametrize('query', [
    'title=Vanya_Hood&oldid=0', 'title=&oldid=600769', 'title=Vanya_Hood&oldid=-1',
    'title=Vanya_Hood&oldid=600769&action=edit', 'title=Vanya_Hood',
    'title=Vanya_Hood&oldid=1&oldid=2', 'title=Vanya_Hood&oldid=latest'])
def test_mediawiki_only_exact_read_only_permalink_shape_is_admitted(batch, query):
    catalog, source = batch
    candidate = deepcopy(catalog)
    row = next(r for r in candidate['sources'] if r['kind']=='bgwiki')
    row['url'] = 'https://www.bg-wiki.com/index.php?' + query
    with pytest.raises(CatalogError, match='URL path'):
        validate_catalog(candidate, items=source.items, hand_types=source.hand_types)


def test_exact_mediawiki_revision_url_is_retained_in_source_actions(batch):
    catalog, source = batch
    prepared = validate_catalog(catalog, items=source.items, hand_types=source.hand_types)
    row = next(r for r in prepared['sources'] if r['id'].startswith('whm:t7b2:community:'))
    assert row['url'] == 'https://www.bg-wiki.com/index.php?title=Community_White_Mage_Guide&oldid=781508'
    assert by_key(prepared, 'cursna')['source_ids'].count(row['id']) == 1


def test_niche_dual_wield_is_declared_and_fails_without_that_context(batch):
    catalog, source = batch
    revision = by_key(catalog, 'tp-dual')
    group = next(s for s in catalog['sets'] if s['id']==revision['set_id'])
    assert group['context']['dual_wield'] is True and group['context']['subjob']=='NIN'
    assert group['context']['subjob_level'] == 49
    assert slots(revision)['main']['item_id']==22031 and slots(revision)['sub']['item_id']==22040
    assert composition_diagnostics(revision['slots'], source.items, ['WHM'], hand_types=source.hand_types) == ['main/sub: dual wield is unconfirmed']
    assert not composition_diagnostics(revision['slots'], source.items, ['WHM'], hand_types=source.hand_types, context=group['context'])
    assert slots(by_key(catalog, 'tp-shield'))['sub']['item_id']==27645
    assert slots(by_key(catalog, 'tp-shield'))['back']['requirements'] == {'augments':['DEX+20','"Dbl.Atk."+10']}
    assert slots(revision)['back']['requirements'] == {'augments':['DEX+20','"Dual Wield"+10']}


def test_niche_accuracy_and_black_halo_exact_rank_copy_and_weapon_requirements(batch):
    catalog, _ = batch
    accuracy = slots(by_key(catalog,'tp-accuracy-shield'))
    assert accuracy['hands']['item_id']==27151 and accuracy['hands']['requirements']=={'rank':15}
    assert not requirements_match(accuracy['hands']['requirements'], {'rank':14})
    assert [accuracy[s]['item_id'] for s in ('ring1','ring2')]==[26182,26182]
    pair=[accuracy[s] for s in ('ring1','ring2')]
    copies=[{'character_key':'fictional','item_id':26182,'bag_id':8}]
    assert sum(r['owned'] for r in allocate_requirements(pair,copies,'fictional').values())==1
    for key in ('black-halo-shield','black-halo-dual'):
        ws = slots(by_key(catalog,key))
        assert ws['main']['item_id']==22031
        assert ws['ear1']['item_id']==27537  # fixed Ishvara, no assumed Moonshade TP augment
        assert ws['back']['requirements']=={'augments':['MND+20','Weapon skill damage +10%']}
        for slot in ('head','body','hands','legs','feet'):
            assert ws[slot]['requirements']=={'rank':15,'path':'B'}
            assert not requirements_match(ws[slot]['requirements'],{'rank':15,'path':'A'})
