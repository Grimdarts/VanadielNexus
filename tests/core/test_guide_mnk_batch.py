"""MNK evidence, action-state, exact hand and distinct-copy regression coverage."""
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
def rev(c,k):return next(r for r in c['revisions'] if r['set_id']=='nexus:mnk:'+k)
def slots(c,k):return {s['slot']:s for s in rev(c,k)['slots']}
def ctx(c,k):return next(s['context'] for s in c['sets'] if s['id']=='nexus:mnk:'+k)
def test_immutable_history_and_deferred_boundaries(batch):
 c,_,items,hands=batch;b=next(b for b in c['authoring_batches'] if b['id']=='mnk-2026-11-05')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':422,'revisions':433,'sources':839}
 for f,h in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in h.items())
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert len([r for r in c['coverage'] if r['job']=='DRG' and r['status']=='included'])==8
 assert 'all22jobs' in c['delivery_status'];validate_catalog(c,items=items,hand_types=hands)
@pytest.mark.parametrize('key',[d['key'] for d in read('gear-guide-t7-mnk-definitions.json')['definitions']])
def test_exact_hands_slots_and_unknown_classification_fail_closed(batch,key):
 c,_,items,hands=batch;r=rev(c,key);s=slots(c,key)
 assert len(s)==16 and s['main']['item_id']==20515
 assert s['sub']=={'slot':'sub','state':'empty'} and s['range']=={'slot':'range','state':'empty'}
 assert not composition_diagnostics(r['slots'],items,['MNK'],hand_types=hands,context=ctx(c,key))
 broken=dict(items);broken[20515]=replace(items[20515],skill=12)
 assert 20515 not in hand_types(broken)
 # Diagnostics enforce cross-hand combinations; exact main classification is
 # independently checked above and in the authoring/readback gate.
 paired=deepcopy(r['slots']);next(s for s in paired if s['slot']=='sub').update(state='selected',item_id=22212,name='Utu Grip',requirements={})
 assert composition_diagnostics(paired,broken,['MNK'],hand_types=hand_types(broken),context=ctx(c,key))
 assert 'current/maxHP' in ctx(c,key)['transitions'] and r['currency']=='unknown'
@pytest.mark.parametrize('item_id',[22212,27645,21527])
def test_h2h_rejects_grip_shield_or_second_weapon(batch,item_id):
 c,_,items,hands=batch;r=deepcopy(rev(c,'engaged-balanced'))
 next(s for s in r['slots'] if s['slot']=='sub').update(state='selected',item_id=item_id,name=items[item_id].en,requirements={})
 assert composition_diagnostics(r['slots'],items,['MNK'],hand_types=hands,context=ctx(c,'engaged-balanced'))
def test_buff_state_and_activation_sustained_costs(batch):
 c,_,_,_=batch
 assert slots(c,'engaged-impetus')['body']['item_id']==23488
 assert 'Sustained active Impetus' in ctx(c,'engaged-impetus')['action']
 assert slots(c,'footwork-activation')['feet']['item_id']==23689
 assert slots(c,'engaged-footwork')['feet']['item_id']==23644
 assert 'JA activation' in ctx(c,'footwork-activation')['action']
 assert 'Sustained active Footwork' in ctx(c,'engaged-footwork')['action']
 assert 'Footwork/Impetus inactive' in ctx(c,'tornado-kick-neutral')['action']
 assert 'Godhands does not grant it' in ctx(c,'victory-smite-impetus')['action']
 assert ctx(c,'refresh-idle')['job']=='MNK99/WHM49' and 'actual MP deficit' in ctx(c,'refresh-idle')['action']
 assert 'no Solace50' in ctx(c,'refresh-idle')['traits']
 assert 'current/maxHP' in ctx(c,'chakra')['action'] and slots(c,'chakra')['body']['item_id']==23443 and slots(c,'chakra')['hands']['item_id']==23533
@pytest.mark.parametrize('key,name',[('refresh-idle','Stikini Ring +1'),('engaged-accuracy','Chirich Ring +1')])
def test_duplicate_rings_allocate_distinct_copies(batch,key,name):
 c,_,_,_=batch;req=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(req)==2
 def alloc(n):return allocate_requirements(req,[dict(item_id=req[0]['item_id'],character_key='fictional',count=n)],'fictional')
 assert sum(r['owned'] for r in alloc(1).values())==1 and sum(r['owned'] for r in alloc(2).values())==2
def test_source_conflicts_and_substitutions_stay_separate(batch):
 c,_,_,_=batch;o=read('gear-guide-t7-mnk-observations.json');by={r['key']:r for r in o['table_observations']}
 assert by['idle']['grid']['main']==[] and by['idle']['grid']['sub']==[]
 assert by['established']['grid']['feet']==['Anch. Gaiters +4']
 assert slots(c,'engaged-footwork')['feet']['name']=='Anch. Gaiters +3'
 assert 'both labelled Footwork UP' in by['tornado']['source_options']['notes']
 assert 'not transferred' in by['chakra']['source_options']['feet']
 assert slots(c,'raging-fists')['legs']['requirements']=={} and slots(c,'shijin-spiral')['hands']['requirements']=={}
def test_literal_augment_negative_oracles(batch):
 c,_,_,_=batch;r=slots(c,'engaged-balanced')['back']['requirements']
 assert requirements_match(r,{'augments':['DEX+20','Accuracy+20 Attack+20','DEX+10','"Dbl.Atk."+10','Phys. dmg. taken -10%']})
 for a in [['DEX+30','Accuracy+20 Attack+20','"Dbl.Atk."+10','Phys. dmg. taken -10%'],['DEX+20','DEX+20','Accuracy+20 Attack+20','"Dbl.Atk."+10','Phys. dmg. taken -10%'],['DEX+20','DEX+10','Accuracy+20','Attack+20','"Dbl.Atk."+10','Phys. dmg. taken -10%']]:assert not requirements_match(r,{'augments':a})
 assert not requirements_match(slots(c,'raging-fists')['ear2']['requirements'],{'augments':['Attack+4','TP Bonus+250']})
def test_evidence_digests_and_exact_coverage(batch):
 c,p,_,_=batch;o=read('gear-guide-t7-mnk-observations.json');cards=read('gear-guide-t7-mnk-item-evidence.json')['items'];d=read('gear-guide-t7-mnk-definitions.json')
 assert len(o['table_observations'])==7 and len(o['guide_observations'])==7 and len(cards)==11
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert 'oldid=781551' in o['guide_observations'][0]['url']
 assert all(r['independent_public_card_verified'] and any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources']) for r in cards)
 assert len(d['coverage_reconciliation'])==7 and all(r['current_row']['status']=='included' and r['current_row']['set_ids'] for r in d['coverage_reconciliation'])
 assert len(d['definitions'])==17 and 'ALL22jobs' in d['sequencing'] and d['unclaimed']
 assert len(p['items'])==863 and len(EVIDENCE)==55
