"""Independent SCH requirement/context checks using detached public resources."""
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


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


@pytest.fixture
def batch():
    catalog = json.loads((FOLDER / 'gear-guide-t7-candidate.json').read_text(encoding='utf-8'))
    evidence = json.loads((FOLDER / 'gear-guide-t7-resource-evidence.json').read_text(encoding='utf-8'))
    items = {r['id']: Item(**r) for r in evidence['items']}
    source = SourceSnapshot('fictional-public-fixture', (), evidence['fingerprint'],
                            MappingProxyType(items), MappingProxyType({int(k):v for k,v in evidence['descriptions'].items()}),
                            hand_types=hand_types(items))
    return catalog, source


def revision(catalog, key):
    return next(r for r in catalog['revisions'] if r['set_id'] == 'nexus:sch:' + key)


def slots(catalog, key):
    return {s['slot']:s for s in revision(catalog, key)['slots']}


def context(catalog, key):
    return next(s['context'] for s in catalog['sets'] if s['id']=='nexus:sch:' + key)


def test_sch_batch_preserves_all_31_prior_revisions_and_52_sources(batch):
    catalog, _ = batch
    history = catalog['authoring_batches'][2]['baseline_record_hashes']
    assert len(history['sets']) == len(history['revisions']) == 31
    assert len(history['sources']) == 52
    for field in ('sources', 'sets', 'revisions'):
        current = {r['id']:r for r in catalog[field]}
        assert all(digest(current[key]) == fingerprint for key,fingerprint in history[field].items())


def test_sch_full_minimum_compositions_and_remaining_effect_uncertainty(batch):
    catalog, source = batch
    validate_catalog(catalog, items=source.items, hand_types=source.hand_types)
    recommendations = [r for r in catalog['revisions'] if r['set_id'].startswith('nexus:sch:')]
    assert len(recommendations) == 28
    for row in recommendations:
        assert row['origin'] == 'nexus_recommendation' and row['verification']['status'] == 'verified'
        assert row['composition_kind'] == 'loadout' and {s['slot'] for s in row['slots']} == set(SLOTS)
        assert next(s for s in row['slots'] if s['slot']=='range') == {'slot':'range','state':'empty'}
        group = next(g for g in catalog['sets'] if g['id']==row['set_id'])
        for slot in row['slots']:
            if slot['state']=='selected':
                assert slot['name'] == source.items[slot['item_id']].en
        result = evaluate(row['slots'], source, job='SCH', context=group['context'])
        assert not result.diagnostics
        assert result.unresolved  # Composition review does not implement new mechanics.


def test_no_waived_idle_or_niche_engaged_priorities(batch):
    catalog, _ = batch
    rows = {r['priority']:r for r in catalog['coverage'] if r['job']=='SCH'}
    assert set(rows) == {'DT Idle','Refresh Idle','Free nuke','Magic burst','Helix','Healing',
                         'Enhancing / Regen','Magic accuracy','Dark magic','Precast','Niche melee / WS',
                         'Sublimation','Engaged Balanced','Engaged DT','Engaged Accuracy','Physical WS'}
    assert all(r['status']=='included' and r['set_ids'] for r in rows.values())
    assert all(r['status']=='gap' for r in catalog['coverage'] if r['job'] not in ('WHM','SCH','BLM','RDM','GEO','BRD','RNG','SAM','NIN','SMN','BLU','COR','RUN','PLD','DRK','WAR','MNK','THF','DRG','BST','PUP','DNC'))
    assert not any(r['status']=='not_applicable' for r in catalog['coverage'])


def test_illegal_source_is_preserved_and_never_repaired_as_author_composition(batch):
    catalog, source = batch
    packet = json.loads((FOLDER / 'gear-guide-t7-sch-observations.json').read_text(encoding='utf-8'))
    assert len(packet['observations']) == 16
    for row in packet['observations']:
        stamp = row.pop('observation_sha256')
        assert digest(row) == stamp
        assert 'range' in row['omitted_slots'] and 'range' not in row['selected_names']
    conflict = next(r for r in packet['observations'] if r['locator']=='Alternative 80% Fast Cast')
    assert conflict['classification']=='conflicting_loadout'
    assert conflict['selected_names']['main']=='Hvergelmir (Level 119 III)'
    assert conflict['selected_names']['sub']=="Chanter's Shield"
    pair = [dict(slot=slot,state='selected',item_id=i,requirements={}) for slot,i in [('main',22064),('sub',27635)]]
    assert composition_diagnostics(pair,source.items,['SCH'],hand_types=source.hand_types)==['main/sub: incompatible equipment']
    assert slots(catalog,'fast-cast')['main']['item_id']==22100
    assert slots(catalog,'fast-cast')['sub']['item_id']==22218
    assert revision(catalog,'fast-cast')['origin']=='nexus_recommendation'


def test_live_healing_tier_does_not_rewrite_historical_snapshot(batch):
    catalog, _ = batch
    packet = json.loads((FOLDER / 'gear-guide-t7-sch-observations.json').read_text(encoding='utf-8'))
    assert packet['live_healing_difference']['hands_id']==24027
    assert packet['live_healing_difference']['old_bg_hands_id']==23551
    assert slots(catalog,'cure')['hands']['item_id']==23551
    old = next(r for r in catalog['revisions'] if r['set_id']=='ffxiah:378846:sch')
    assert old['verification']['status']=='unresolved'


def test_explicit_vanya_and_telchine_paths_cannot_cross_satisfy(batch):
    catalog, _ = batch
    healing = slots(catalog,'cure')['head']['requirements']
    casting = slots(catalog,'fast-cast')['head']['requirements']
    assert healing=={'rank':15,'path':'B'} and casting=={'rank':15,'path':'D'}
    assert not requirements_match(casting,{'rank':15,'path':'B'})
    assert not requirements_match(casting,{'rank':14,'path':'D'})
    for slot in ('head','legs','feet'):
        requirement=slots(catalog,'enhancing-duration')[slot]['requirements']
        assert requirement=={'augments':['Enh. Mag. eff. dur. +10']}
        assert not requirements_match(requirement,{'augments':'Enh. Mag. eff. dur. +9'})
    assert slots(catalog,'regen')['head']['item_id']==23439
    assert slots(catalog,'regen-duration')['head']['item_id']!=23439
    assert slots(catalog,'regen')['back']['item_id']==26265
    assert slots(catalog,'regen')['back']['requirements']=={}


@pytest.mark.parametrize('key', ['cure','enhancing-duration','enfeebling','tp-balanced','tp-accuracy'])
def test_paired_slots_need_two_actual_copies(batch,key):
    catalog, _ = batch
    rows = slots(catalog,key)
    pair=[rows['ring1'],rows['ring2']]
    assert pair[0]['item_id']==pair[1]['item_id']
    inventory=[{'character_key':'fictional','item_id':pair[0]['item_id'],'bag_id':8}]
    assert sum(r['owned'] for r in allocate_requirements(pair,inventory,'fictional').values())==1


def test_arts_stratagem_weather_and_sublimation_are_separate_contexts(batch):
    catalog, _ = batch
    assert 'inactive' in context(catalog,'grimoire-precast')['stratagems']
    assert 'Alacrity' in context(catalog,'celerity-alacrity-precast')['stratagems']
    assert slots(catalog,'grimoire-precast')['head']['item_id']==23417
    assert slots(catalog,'celerity-alacrity-precast')['head']['item_id']!=23417
    assert slots(catalog,'celerity-alacrity-precast')['feet']['item_id']==23685
    assert slots(catalog,'cure')['main']['item_id']==22040
    assert slots(catalog,'cure-weather')['main']['item_id']==18633
    assert slots(catalog,'cure-weather')['back']['item_id']==16259
    assert slots(catalog,'rapture-cure')['head']['item_id']==23439
    assert slots(catalog,'ebullience-burst')['head']['item_id']==23439
    assert 'Charging' in context(catalog,'sublimation')['sublimation']
    assert slots(catalog,'sublimation')['head']['item_id']==23395
    assert slots(catalog,'sublimation')['body']['item_id']==23484
    assert slots(catalog,'sublimation')['ear2']['item_id']==11722


def test_magic_and_melee_minimums_do_not_inherit_source_maximums(batch):
    catalog, _ = batch
    free=slots(catalog,'free-nuke')
    assert free['head']['requirements']=={} and free['ring2']['requirements']=={}
    assert free['ammo']['item_id']==22271  # fixed Pemphredo, not R15 Ghastly
    assert free['back']['requirements']=={'augments':['INT+20','Mag. Acc+20 /Mag. Dmg.+20','"Mag.Atk.Bns."+10']}
    assert slots(catalog,'helix-free')['waist']['item_id']!=28419  # no Hachirin weather shortcut
    assert slots(catalog,'helix-burst')['waist']==slots(catalog,'helix-free')['waist']
    assert slots(catalog,'tp-balanced')['hands']['requirements']=={'rank':15}
    ws=slots(catalog,'shattersoul')
    assert ws['main']['item_id']==22100 and ws['sub']['item_id']==22218
    for slot in ('head','body','hands','legs','feet'):
        assert ws[slot]['requirements']=={'rank':15,'path':'B'}
    assert '357' in context(catalog,'shattersoul')['ability']
