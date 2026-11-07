"""DRG evidence and meaningful hand, wyvern/timing, distinct-copy rejection checks."""
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
def rev(c,k):return next(r for r in c['revisions'] if r['set_id']=='nexus:drg:'+k)
def slots(c,k):return {s['slot']:s for s in rev(c,k)['slots']}
def ctx(c,k):return next(s['context'] for s in c['sets'] if s['id']=='nexus:drg:'+k)
KEYS=[d['key'] for d in read('gear-guide-t7-drg-authoring-definitions.json')['definitions']]
def test_history(batch):
 c,_,items,h=batch;b=next(b for b in c['authoring_batches'] if b['id']=='drg-2026-11-05')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':454,'revisions':465,'sources':902}
 for f,m in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in m.items())
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert [len(c[f]) for f in ('sets','revisions','sources','coverage')]==[520,547,1331,231]
 gaps=[r for r in c['coverage'] if r['status']=='gap'];assert len(gaps)==0 and {r['job'] for r in gaps}==set()
 validate_catalog(c,items=items,hand_types=h)
@pytest.mark.parametrize('key',KEYS)
def test_exact_hands_slots_and_unknown_rejection(batch,key):
 c,_,items,h=batch;s=slots(c,key);r=rev(c,key)
 assert len(s)==16 and s['main']['item_id']==21883 and s['sub']['item_id']==22212
 assert s['range']==dict(slot='range',state='empty') and h[21883]=='two_handed' and h[22212]=='grip'
 assert not composition_diagnostics(r['slots'],items,['DRG'],hand_types=h,context=ctx(c,key))
 bad=dict(items);bad[21883]=replace(items[21883],skill=12);assert 21883 not in hand_types(bad)
 assert composition_diagnostics(r['slots'],bad,['DRG'],hand_types=hand_types(bad),context=ctx(c,key))
 wrong=dict(h);wrong[22212]='shield';assert composition_diagnostics(r['slots'],items,['DRG'],hand_types=wrong,context=ctx(c,key))
 assert composition_diagnostics(r['slots'],items,['WHM'],hand_types=h,context=ctx(c,key))
 assert 'current/maxHP' in ctx(c,key)['transitions'] and 'wyvern' in ctx(c,key)
@pytest.mark.parametrize('key,name',[('refresh-idle','Stikini Ring +1'),('jump','Chirich Ring +1'),('spirit-jump','Chirich Ring +1')])
def test_distinct_ring_allocation(batch,key,name):
 c,_,_,_=batch;r=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(r)==2
 def alloc(n):return allocate_requirements(r,[dict(item_id=r[0]['item_id'],character_key='fictional',count=n)],'fictional')
 assert sum(x['owned'] for x in alloc(1).values())==1
 assert sum(x['owned'] for x in alloc(2).values())==2
def test_wyvern_timing_and_access(batch):
 c,_,_,_=batch
 assert slots(c,'call-wyvern')['body']['item_id']==23478 and 'time of use' in ctx(c,'call-wyvern')['action']
 assert slots(c,'spirit-link')['ear1']['item_id']==28498 and 'below 100% HP' in ctx(c,'spirit-link')['action']
 assert slots(c,'restoring-breath')['head']['item_id']==23411 and 'resolves' in ctx(c,'restoring-breath')['action']
 assert 'tic' in ctx(c,'steady-wing')['action'] and slots(c,'steady-wing')['legs']['item_id']==23589
 assert 'Martial Mastery' in ctx(c,'stardiver')['action'] and 'regardless of quest' in ctx(c,'impulse-drive')['action']
 for k in ('spirit-jump','soul-jump'):assert 'wyvern actually present' in ctx(c,k)['action']
 assert slots(c,'spirit-jump')['legs']['item_id']==23634 and slots(c,'spirit-jump')['feet']['item_id']==23701
 assert slots(c,'soul-jump')['body']['item_id']==23500 and slots(c,'soul-jump')['hands']['item_id']==23770
 assert ctx(c,'refresh-idle')['job']=='DRG99/WHM49' and '46MP' in ctx(c,'refresh-idle')['action']
def test_literal_copies_and_source_distinctions(batch):
 c,_,_,_=batch
 da=slots(c,'engaged-balanced')['back']['requirements'];stp=slots(c,'jump')['back']['requirements']
 assert requirements_match(da,{'augments':['STR+20','Accuracy+20 Attack+20','Accuracy+10','"Dbl.Atk."+10','Phys. dmg. taken -10%']})
 assert not requirements_match(da,{'augments':['STR+20','Accuracy+30','Attack+20','"Dbl.Atk."+10','Phys. dmg. taken -10%']})
 assert not requirements_match(stp,{'augments':['DEX+20','Accuracy+20 Attack+20','Accuracy+10','Store TP+10','Phys. dmg. taken -10%']})
 assert not requirements_match(slots(c,'impulse-drive')['ear2']['requirements'],{'augments':['Attack+4','TP Bonus+250']})
 assert slots(c,'restoring-breath')['back']=={'slot':'back','state':'selected','item_id':26259,'name':"Brigantia's Mantle",'requirements':{}}
 o=read('gear-guide-t7-drg-authoring-observations.json');by={r['key']:r for r in o['table_observations']}
 assert by['stardiver']['grid']['main']==['Trishula'] and slots(c,'stardiver')['main']['item_id']==21883
 assert by['endgame-tp']['grid']['legs']==['Ptero. Brais +4'] and slots(c,'engaged-balanced')['legs']['name']=='Ptero. Brais +3'
 assert by['acc-wyvern']['grid']['ring2']==['Varar Ring +1'] and slots(c,'engaged-accuracy')['ring2']['name']=='Chirich Ring +1'
 assert by['grid-inventory']['composition_kind']=='equipment_options' and 'Cloudflare' in o['access']
def test_evidence_reconciliation_and_checkpoint_preserved(batch):
 c,p,_,_=batch;o=read('gear-guide-t7-drg-authoring-observations.json');cards=read('gear-guide-t7-drg-authoring-item-evidence.json')['items'];d=read('gear-guide-t7-drg-authoring-definitions.json')
 assert len(o['table_observations'])==23 and len(o['guide_observations'])==15 and len(cards)==27
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert all(r['independent_public_card_verified'] and any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources']) for r in cards)
 assert len(d['definitions'])==15 and len(d['coverage_reconciliation'])==8
 assert all(r['original_row']['status']=='gap' and r['current_row']['status']=='included' and r['current_row']['set_ids'] for r in d['coverage_reconciliation'])
 assert read('gear-guide-t7-drg-definitions.json')['definitions']==[]
 assert len(p['items'])==863 and len(EVIDENCE)==55
