"""WAR context, immutable evidence and negative hand/copy/augment regressions."""
from copy import deepcopy
from dataclasses import replace
import hashlib,json
from pathlib import Path
import pytest
from vanadiel_nexus.core.equipment_hands import hand_types,EVIDENCE
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
def rev(c,k):return next(r for r in c['revisions'] if r['set_id']=='nexus:war:'+k)
def slots(c,k):return {s['slot']:s for s in rev(c,k)['slots']}
def ctx(c,k):return next(s['context'] for s in c['sets'] if s['id']=='nexus:war:'+k)
def test_preserves_history_amendments_and_deferred_scope(batch):
 c,_,items,hands=batch;b=next(b for b in c['authoring_batches'] if b['id']=='war-2026-11-05')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':397,'revisions':408,'sources':805}
 for f,h in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in h.items())
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 assert len([r for r in c['coverage'] if r['job']=='DRG' and r['status']=='included'])==8
 assert 'all22jobs' in c['delivery_status'];validate_catalog(c,items=items,hand_types=hands)
@pytest.mark.parametrize('key',[d['key'] for d in read('gear-guide-t7-war-definitions.json')['definitions']])
def test_legal_hands_and_changed_classification_fails_closed(batch,key):
 c,_,items,hands=batch;r=rev(c,key);s=slots(c,key);i=s['main']['item_id']
 assert len(r['slots'])==16 and s['range']=={'slot':'range','state':'empty'}
 assert (i,s['sub']['item_id']) in ((20843,22212),(21621,27644))
 assert not composition_diagnostics(r['slots'],items,['WAR'],hand_types=hands,context=ctx(c,key))
 broken=dict(items);broken[i]=replace(items[i],skill=12)
 assert i not in hand_types(broken)
 assert composition_diagnostics(r['slots'],broken,['WAR'],hand_types=hand_types(broken),context=ctx(c,key))
 assert r['currency']=='unknown' and 'current/maxHP' in ctx(c,key)['transitions']
def test_illegal_cross_family_pair_and_no_dualwield(batch):
 c,_,items,hands=batch;r=deepcopy(rev(c,'savage-blade'))
 next(s for s in r['slots'] if s['slot']=='sub').update(item_id=22212,name='Utu Grip')
 assert composition_diagnostics(r['slots'],items,['WAR'],hand_types=hands,context=ctx(c,'savage-blade'))
 assert all(not s['context']['dual_wield'] for s in c['sets'] if s['id'].startswith('nexus:war:'))
def test_source_omissions_options_and_discrepancy_preserved(batch):
 c,_,_,_=batch;o=read('gear-guide-t7-war-observations.json');by={r['key']:r for r in o['table_observations']}
 assert by['layered']['grid']['main']==[] and by['layered']['grid']['waist']==[]
 assert by['retaliation']['grid']['ring1']==[] and by['retaliation']['grid']['ear2']==[]
 assert 'R20' in by['upheaval2']['source_options']['head/body/legs/feet']
 assert slots(c,'upheaval-wsd')['body']['requirements']=={'path':'B'}
 assert 'Acc10' in by['twohand4']['source_options']['back'] and slots(c,'engaged-balanced-greataxe')['back']['requirements']['augments'][2]=='DEX+10'
 card=next(r for r in read('gear-guide-t7-war-item-evidence.json')['items'] if r['item_id']==27644)
 assert 'jobs386 excludes DRK' in card['conditional'] and 'WAR matches both' in card['conditional']
def test_subjob_traits_mp_and_action_phases(batch):
 c,_,_,_=batch
 assert ctx(c,'engaged-balanced-greataxe')['job']=='WAR99/SAM49'
 assert ctx(c,'savage-blade')['job']=='WAR99/DRG49'
 assert ctx(c,'refresh-idle-fencer')['job']=='WAR99/DRK49'
 assert 'MP deficit' in ctx(c,'refresh-idle-fencer')['action']
 assert 'LastResort50' in ctx(c,'stun-subjob-fencer')['traits']
 assert 'onehand singleweapon' in ctx(c,'savage-blade')['traits']
 assert 'permanent unlock' in ctx(c,'savage-blade')['action']
 assert "Permanently unlocked King's Justice" in ctx(c,'kings-justice')['action']
 assert 'does not grant' in ctx(c,'kings-justice')['action']
 assert 'effectiveTP' in ctx(c,'upheaval-multihit')['action']
 assert 'received damage remains' in ctx(c,'retaliation-sustained-fencer')['action']
 assert 'shieldblocked' in ctx(c,'retaliation-sustained-fencer')['action']
 assert 'activation' in ctx(c,'defender-fencer')['action'] and 'sustained buff distinct' in ctx(c,'defender-fencer')['action']
 assert 'initiation only' in ctx(c,'precast-greataxe')['action']
 assert 'Stun completion' in ctx(c,'stun-subjob-greataxe')['action']
 assert 'no cap/TPloop' in ctx(c,'engaged-dt-fencer')['buffs']
@pytest.mark.parametrize('key,name',[('refresh-idle-greataxe','Stikini Ring +1'),('stun-subjob-fencer','Stikini Ring +1'),('engaged-accuracy-fencer','Chirich Ring +1')])
def test_two_simultaneous_rings_require_two_copies(batch,key,name):
 c,_,_,_=batch;req=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(req)==2
 def allocate(n):return allocate_requirements(req,[dict(item_id=req[0]['item_id'],character_key='fictional',count=n)],'fictional')
 assert sum(r['owned'] for r in allocate(1).values())==1 and sum(r['owned'] for r in allocate(2).values())==2
def test_literal_augments_and_native_punctuation(batch):
 c,_,_,_=batch;r=slots(c,'upheaval-wsd')['back']['requirements']
 assert requirements_match(r,{'augments':['VIT+20','Accuracy+20 Attack+20','VIT+10','Weapon skill damage +10%','Damage taken-5%']})
 for a in [['VIT+30','Accuracy+20 Attack+20','Weapon skill damage +10%','Damage taken-5%'],['VIT+20','VIT+20','Accuracy+20 Attack+20','Weapon skill damage +10%','Damage taken-5%'],['VIT+20','VIT+10','Accuracy+20','Attack+20','Weapon skill damage +10%','Damage taken-5%']]:assert not requirements_match(r,{'augments':a})
 assert not requirements_match(slots(c,'precast-greataxe')['back']['requirements'],{'augments':['HP+60','Fast Cast+10']})
 assert not requirements_match(slots(c,'savage-blade')['ear1']['requirements'],{'augments':['Attack+4','TP Bonus+250']})
def test_hashed_evidence_and_bounded_priority_reconciliation(batch):
 c,p,_,_=batch;o=read('gear-guide-t7-war-observations.json');cards=read('gear-guide-t7-war-item-evidence.json')['items'];d=read('gear-guide-t7-war-definitions.json')
 assert len(o['table_observations'])==11 and len(o['guide_observations'])==5 and len(cards)==18
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert 'oldid=781333' in o['guide_observations'][0]['url']
 assert all(r['independent_public_card_verified'] and any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources']) for r in cards)
 assert len(d['coverage_reconciliation'])==7 and all(r['current_row']['status']=='included' and r['current_row']['set_ids'] for r in d['coverage_reconciliation'])
 assert len(d['definitions'])==25 and 'ALL22jobs' in d['sequencing'] and d['unclaimed']
 assert len(p['items'])==863 and len(EVIDENCE)==55
