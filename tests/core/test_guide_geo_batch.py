"""GEO evidence, recipient and eligibility regressions; fictional persistence only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType

import pytest
from vanadiel_nexus.core.equipment_effects import SourceSnapshot, evaluate
from vanadiel_nexus.core.equipment_hands import hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS, allocate_requirements
from vanadiel_nexus.core.guide_catalog import composition_diagnostics, validate_catalog
from vanadiel_nexus.core.item_res import Item

F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(name): return json.loads((F/name).read_text(encoding='utf-8'))
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

@pytest.fixture
def batch():
    c=read('gear-guide-t7-candidate.json'); p=read('gear-guide-t7-resource-evidence.json')
    items={r['id']:Item(**r) for r in p['items']}
    source=SourceSnapshot('fictional-geo-public-fixture',(),p['fingerprint'],MappingProxyType(items),
        MappingProxyType({int(k):v for k,v in p['descriptions'].items()}),hand_types=hand_types(items))
    return c,source

def revision(c,key): return next(r for r in c['revisions'] if r['set_id']=='nexus:geo:'+key)
def slots(c,key): return {s['slot']:s for s in revision(c,key)['slots']}
def context(c,key): return next(r['context'] for r in c['sets'] if r['id']=='nexus:geo:'+key)

def test_geo_preserves_119_existing_revisions_and_188_sources(batch):
    c,s=batch
    history=c['authoring_batches'][5]['baseline_record_hashes']
    assert len(history['sets'])==len(history['revisions'])==119 and len(history['sources'])==188
    for field in ('sets','revisions','sources'):
        current={r['id']:r for r in c[field]}
        assert all(digest(current[k])==h for k,h in history[field].items())
    validate_catalog(c,items=s.items,hand_types=s.hand_types)

@pytest.mark.parametrize('key',[
 'dt-idle','refresh-idle','refresh-jse','geomancy-skill','indi-duration','entrust',
 'geocolure','luopan-durability','luopan-recovery','fast-cast','fast-cast-defense',
 'free-nuke','free-nuke-jse','magic-burst','magic-accuracy','enfeebling-mnd','enfeebling-int'])
def test_geo_base_compositions_do_not_certify_complete_numeric_effects(batch,key):
    c,s=batch; r=revision(c,key)
    assert r['origin']=='nexus_recommendation' and r['currency']=='unknown'
    assert r['verification']['status']=='verified'
    assert {x['slot'] for x in r['slots']}==set(SLOTS)
    assert not composition_diagnostics(r['slots'],s.items,['GEO'],hand_types=s.hand_types,context=context(c,key))
    assert all(x['requirements']=={} and s.items[x['item_id']].en==x['name'] for x in r['slots'] if x['state']=='selected')
    result=evaluate(r['slots'],s,job='GEO',context=context(c,key))
    assert not result.diagnostics and result.unresolved
    assert 'No complete effects' in r['verification']['scope']

def test_refresh_rejects_homiliary_and_preserves_handbell_empty_ammo(batch):
    c,s=batch; r=slots(c,'refresh-idle')
    assert r['range']['item_id']==21372 and r['ammo']=={'slot':'ammo','state':'empty'}
    assert not {x.get('item_id') for x in r.values()} & {22268,11697,28452}
    bad=deepcopy(revision(c,'refresh-idle')['slots'])
    bad=[dict(slot='ammo',state='selected',item_id=22268,name='Homiliary',requirements={}) if x['slot']=='ammo' else x for x in bad]
    assert 'ammo: item is ineligible for GEO' in composition_diagnostics(bad,s.items,['GEO'],hand_types=s.hand_types)

def test_precast_does_not_invent_fi_follet_or_solstice_augments(batch):
    c,_=batch
    for key in ('fast-cast','fast-cast-defense'):
        r=slots(c,key)
        assert r['main']['item_id']==21085 and r['main']['requirements']=={}
        assert r['legs']['item_id']==23597
        assert 27610 not in {x.get('item_id') for x in r.values()}
    assert slots(c,'fast-cast')['back']['item_id']==28637
    assert slots(c,'fast-cast')['sub']['item_id']==27635
    assert slots(c,'fast-cast-defense')['sub']['item_id']==27645

def test_entrust_and_geo_creation_are_distinct_recipient_contexts(batch):
    c,_=batch
    assert context(c,'indi-duration')['recipient'].startswith('Self')
    assert context(c,'entrust')['recipient']=='Eligible party member'
    assert 'no Bolster/Geomancy+' in context(c,'entrust')['ability']
    assert context(c,'geocolure')['recipient']=='New luopan'
    assert slots(c,'indi-duration')['back']['item_id']==26266
    assert slots(c,'geocolure')['back']['item_id']==28637
    assert slots(c,'geocolure')['legs']['item_id']==23782

def test_pet_effects_do_not_transfer_to_master_or_inherit_idris(batch):
    c,s=batch
    for key in ('luopan-durability','luopan-recovery'):
        r=slots(c,key)
        assert r['main']['item_id']==21085 and r['sub']['item_id']==27645
        assert r['range']['item_id']==21372 and r['hands']['item_id']==23530
        assert r['waist']['item_id']==28451 and r['feet']['item_id']==23686
        assert r['head']['item_id']==23440 and r['back']['item_id']==26268
        assert 'non-Idris' in context(c,key)['luopan']
        result=evaluate(list(r.values()),s,job='GEO')
        assert not any(x.recipient=='master' and x.item_id in {21372,28451}
                       for contribution in result.contributions for x in contribution.trace)
    assert slots(c,'luopan-durability')['body']['item_id']==23768
    assert slots(c,'luopan-recovery')['body']['item_id']==23463

def test_source_reader_hashes_order_and_partial_pet_observation():
    caps=read('gear-guide-t7-geo-source-captures.json')['captures']
    by_id={r['capture_id']:r for r in caps}
    for r in caps:
        assert hashlib.sha256(r['provider_output'].encode()).hexdigest()==r['response_sha256']
    observations=read('gear-guide-t7-geo-observations.json')['observations']
    assert len(observations)==13
    for row in observations:
        stamp=row['observation_sha256']; clean={k:v for k,v in row.items() if k!='observation_sha256'}
        assert digest(clean)==stamp
        source=by_id[row['capture_id']]['provider_output']
        positions=[source.index(e['locator']+':') for e in row['ordered_macro_entries']]
        assert positions==sorted(positions)
        assert all(e['source_text'] in source for e in row['ordered_macro_entries'])
    pet=next(r for r in observations if r['item_set']==333672)
    assert pet['occupied_entry_count']==10 and len(pet['omitted_slots'])==6
    assert next(e['name'] for e in pet['ordered_macro_entries'] if e['slot']=='sub')=='Idris'
    assert pet['conflicts']

def test_su3_and_two_physical_ring_copies_remain_explicit(batch):
    c,_=batch
    assert '500 Job Points' in context(c,'magic-burst')['access']
    r=slots(c,'geomancy-skill'); pair=[r['ring1'],r['ring2']]
    assert pair[0]['item_id']==pair[1]['item_id']==26184
    owned=[{'character_key':'fictional','item_id':26184,'bag_id':8}]
    assert sum(x['owned'] for x in allocate_requirements(pair,owned,'fictional').values())==1

def test_geo_coverage_is_eight_bounded_priorities_with_16_other_jobs_open(batch):
    c,_=batch
    rows=[r for r in c['coverage'] if r['job']=='GEO']
    assert len(rows)==8 and all(r['status']=='included' and r['set_ids'] for r in rows)
    assert len([r for r in c['revisions'] if r['set_id'].startswith('nexus:geo:')])==17
    gaps=[r for r in c['coverage'] if r['status']=='gap']
    assert len(gaps)==0 and len({r['job'] for r in gaps})==0
    assert not any(r['status']=='not_applicable' for r in c['coverage'])
