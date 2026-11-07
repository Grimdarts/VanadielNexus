"""THF evidence and meaningful hand, timing, distinct-copy rejection checks."""
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
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json');items={r['id']:Item(**r) for r in p['items']};return c,p,items,hand_types(items)
def rev(c,k):return next(r for r in c['revisions'] if r['set_id']=='nexus:thf:'+k)
def slots(c,k):return {s['slot']:s for s in rev(c,k)['slots']}
def ctx(c,k):return next(s['context'] for s in c['sets'] if s['id']=='nexus:thf:'+k)
def test_history(batch):
 c,_,items,h=batch;b=next(b for b in c['authoring_batches'] if b['id']=='thf-2026-11-05')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':439,'revisions':450,'sources':864}
 for f,m in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in m.items())
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert len([r for r in c['coverage'] if r['job']=='DRG' and r['status']=='included'])==8
 validate_catalog(c,items=items,hand_types=h)
@pytest.mark.parametrize('key',[d['key'] for d in read('gear-guide-t7-thf-definitions.json')['definitions']])
def test_exact_hands_slots_and_unknown_rejection(batch,key):
 c,_,items,h=batch;s=slots(c,key);r=rev(c,key)
 assert len(s)==16 and s['main']['item_id']==21565 and s['sub']['item_id']==21567
 assert s['range']==dict(slot='range',state='empty') and h[21565]==h[21567]=='one_handed'
 assert not composition_diagnostics(r['slots'],items,['THF'],hand_types=h,context=ctx(c,key))
 for i in [21565,21567]:
  bad=dict(items);bad[i]=replace(items[i],skill=12);assert i not in hand_types(bad)
  assert composition_diagnostics(r['slots'],bad,['THF'],hand_types=hand_types(bad),context=ctx(c,key))
 assert composition_diagnostics(r['slots'],items,['THF'],hand_types=h,context=dict(dual_wield=False))
 assert 'current/maxHP' in ctx(c,key)['transitions']
@pytest.mark.parametrize('key,name',[('refresh-idle','Stikini Ring +1'),('engaged-accuracy','Chirich Ring +1'),('aeolian-edge','Shiva Ring +1')])
def test_distinct_ring_allocation(batch,key,name):
 c,_,_,_=batch;r=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(r)==2
 def alloc(n):return allocate_requirements(r,[dict(item_id=r[0]['item_id'],character_key='fictional',count=n)],'fictional')
 assert sum(x['owned'] for x in alloc(1).values())==1
 assert sum(x['owned'] for x in alloc(2).values())==2
@pytest.mark.parametrize('key,hands,body',[('rudra-sneak',23559,23492),('sneak-hit',23559,23492),('rudra-trick',23514,23470),('trick-hit',23514,23470)])
def test_hit_time_gear(batch,key,hands,body):
 c,_,_,_=batch;s=slots(c,key);assert s['hands']['item_id']==hands and s['body']['item_id']==body
 assert 'not snapshotted atactivation' in ctx(c,key)['timing']
 assert 'unconsumed' in ctx(c,key)['action']
def test_mp_th_buffs_and_source_distinctions(batch):
 c,_,_,_=batch
 assert ctx(c,'refresh-idle')['job']=='THF99/WHM49' and '46MP' in ctx(c,'refresh-idle')['action']
 assert '550JP' in ctx(c,'engaged-balanced')['action'] and slots(c,'engaged-low-haste')['hands']['item_id']==23514
 assert slots(c,'treasure-tag')['feet']['item_id']==23693
 assert 'permanent unlock' in ctx(c,'rudra-neutral')['action']
 o=read('gear-guide-t7-thf-observations.json');by={r['key']:r for r in o['table_observations']}
 assert by['nyame-dt']['grid']['main']==[] and by['hybrid-b']['grid']['body']==['Pill. Vest +4']
 assert slots(c,'engaged-balanced')['body']['name']=="Pillager's Vest +3"
 assert by['th-options']['composition_kind']=='equipment_options'
 assert 'not playableloadouts' in o['guide_observations'][1]['findings'][0]
 assert slots(c,'rudra-neutral')['hands']['requirements']=={} and slots(c,'defensive-evasion')['neck']['requirements']=={}
def test_literal_copy_negatives(batch):
 c,_,_,_=batch;r=slots(c,'aeolian-edge')['back']['requirements']
 assert requirements_match(r,{'augments':['INT+20','Mag. Acc+20 /Mag. Dmg.+20','INT+10','Weapon skill damage +10%','Phys. dmg. taken -10%']})
 assert not requirements_match(r,{'augments':['INT+30','Mag. Acc+20 /Mag. Dmg.+20','Weapon skill damage +10%','Phys. dmg. taken -10%']})
 assert not requirements_match(slots(c,'rudra-neutral')['ear2']['requirements'],{'augments':['Attack+4','TP Bonus+250']})
def test_evidence_and_reconciliation(batch):
 c,p,_,_=batch;o=read('gear-guide-t7-thf-observations.json');cards=read('gear-guide-t7-thf-item-evidence.json')['items'];d=read('gear-guide-t7-thf-definitions.json')
 assert len(o['table_observations'])==13 and len(o['guide_observations'])==7 and len(cards)==18
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert all(r['independent_public_card_verified'] and any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources']) for r in cards)
 assert len(d['definitions'])==15 and len(d['coverage_reconciliation'])==8
 assert all(r['current_row']['status']=='included' and r['current_row']['set_ids'] for r in d['coverage_reconciliation'])
 assert len(p['items'])==863 and len(EVIDENCE)==55
