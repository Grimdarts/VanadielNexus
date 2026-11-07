"""RUN evidence conflicts, hand failures, distinct copies and conditional contexts."""
from copy import deepcopy
from dataclasses import replace
import hashlib,json
from pathlib import Path
import pytest
from vanadiel_nexus.core.equipment_hands import hand_types
from vanadiel_nexus.core.equipment_matching import requirements_match,allocate_requirements
from vanadiel_nexus.core.guide_catalog import validate_catalog,composition_diagnostics
from vanadiel_nexus.core.item_res import Item
F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(n):return json.loads((F/n).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
@pytest.fixture
def batch():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json');items={r['id']:Item(**r) for r in p['items']}
 return c,p,items,hand_types(items)
def rev(c,key):return next(r for r in c['revisions'] if r['set_id']=='nexus:run:'+key)
def slots(c,key):return {s['slot']:s for s in rev(c,key)['slots']}
def ctx(c,key):return next(s['context'] for s in c['sets'] if s['id']=='nexus:run:'+key)
def test_prior_history_and_deferred_issues_remain(batch):
 c,p,items,hands=batch;b=next(b for b in c['authoring_batches'] if b['id']=='run-2026-11-04')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':312,'revisions':323,'sources':629}
 for f,history in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in history.items())
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 drg=[r for r in c['coverage'] if r['job']=='DRG'];assert len(drg)==8 and all(r['status']=='included' for r in drg)
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and retired<={r['id'] for r in c['revisions']}
 validate_catalog(c,items=items,hand_types=hands)
@pytest.mark.parametrize('key',['dt-idle','refresh-idle','engaged-balanced','engaged-dt','engaged-accuracy','dimidiation','resolution','enmity-ja','flash-enmity','precast','sird-completion','enhancing-skill','self-phalanx','self-refresh','enhancing-duration','vallation','valiance','gambit','rayke','vivacious-pulse'])
def test_contextual_compositions_are_legal_but_missing_hand_evidence_fails(batch,key):
 c,_,items,hands=batch;r=rev(c,key);context=ctx(c,key)
 assert not composition_diagnostics(r['slots'],items,['RUN'],hand_types=hands,context=context)
 assert len(r['slots'])==16 and slots(c,key)['range']=={'slot':'range','state':'empty'}
 main=slots(c,key)['main']['item_id'];assert main==(21694 if key=='resolution' else 20761)
 broken=deepcopy(items);broken[main]=replace(items[main],skill=12)
 assert main not in hand_types(broken)
 assert composition_diagnostics(r['slots'],broken,['RUN'],hand_types=hand_types(broken),context=context)
 assert r['currency']=='unknown' and r['origin']=='nexus_recommendation'
def test_source_errors_are_observations_and_recommendation_repairs_attributed(batch):
 c,_,_,_=batch;o=read('gear-guide-t7-run-observations.json');by={r['item_set_id']:r for r in o['table_observations']}
 assert by[372679]['grid']['ear1']==['Erilaz Earring +1']
 assert by[372999]['grid']['ring2']==["Gurebu's Ring"] and by[372999]['competing_macro_values']['ring2']==['Stikini Ring +1',"Gurebu's Ring"]
 assert by[372673]['omitted_slots'] and len(by[372673]['omitted_slots'])==12
 assert all(s.get('item_id')!=25547 for s in rev(c,'engaged-dt')['slots'])
 assert slots(c,'refresh-idle')['ring1']['name']==slots(c,'refresh-idle')['ring2']['name']=='Stikini Ring +1'
 assert 'source final ring2' in rev(c,'refresh-idle')['rationale']
 assert 'BG403' in o['access'] and 'disabled' in o['access']
def test_fixed_weapons_and_distinct_spell_recipient_conditions(batch):
 c,_,_,_=batch
 assert slots(c,'dt-idle')['main']['item_id']==slots(c,'precast')['main']['item_id']==slots(c,'self-phalanx')['main']['item_id']==20761
 assert slots(c,'dt-idle')['sub']['item_id']==slots(c,'precast')['sub']['item_id']==21417
 assert '500 job points' in ctx(c,'engaged-dt')['access_extra']
 assert '550JP' in ctx(c,'enhancing-skill')['access_extra']
 assert 'self recipient' in ctx(c,'vallation')['action'] and 'party recipients' in ctx(c,'valiance')['action']
 assert 'recipient at resolution' in ctx(c,'self-phalanx')['action']
 assert 'initiation only' in ctx(c,'precast')['action'] and 'completion' in ctx(c,'sird-completion')['action']
 assert 'three actually harbored Tenebrae' in ctx(c,'vivacious-pulse')['action']
@pytest.mark.parametrize('key,slot,copy',[
 ('engaged-balanced','back',{'augments':['DEX+20','Accuracy+20 Attack+20','DEX+10','"Dbl.Atk."+10','Damage taken-5%']}),
 ('dimidiation','back',{'augments':['DEX+20','Accuracy+20 Attack+20','DEX+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('resolution','back',{'augments':['STR+20','Accuracy+20 Attack+20','STR+10','"Dbl.Atk."+10','Damage taken-5%']}),
 ('precast','back',{'augments':['HP+60','"Fast Cast"+10']}),
 ('dimidiation','ear1',{'augments':['Attack+4','TP Bonus +250']})])
def test_independent_literal_copy_accepts_native_parts_rejects_missing(batch,key,slot,copy):
 c,_,_,_=batch;r=slots(c,key)[slot]['requirements']
 assert requirements_match(r,copy)
 assert not requirements_match(r,{'augments':copy['augments'][:-1]})
def test_observation_digests_and_exact_card_evidence(batch):
 c,p,items,_=batch;o=read('gear-guide-t7-run-observations.json');cards=read('gear-guide-t7-run-item-evidence.json')['items']
 assert len(o['table_observations'])==20 and len(cards)==43
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert all(r['independent_public_card_verified'] for r in cards)
 assert 25547 not in items
 for r in cards:assert any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources'])

@pytest.mark.parametrize('key,name',[('refresh-idle','Stikini Ring +1'),('engaged-accuracy','Chirich Ring +1'),('precast','Moonlight Ring')])
def test_duplicate_rings_cannot_share_one_physical_copy(batch,key,name):
 c,_,_,_=batch;requirements=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(requirements)==2
 item_id=requirements[0]['item_id']
 one=allocate_requirements(requirements,[dict(item_id=item_id,character_key='fictional',count=1)],'fictional')
 two=allocate_requirements(requirements,[dict(item_id=item_id,character_key='fictional',count=2)],'fictional')
 assert sum(r['owned'] for r in one.values())==1 and sum(r['owned'] for r in two.values())==2
