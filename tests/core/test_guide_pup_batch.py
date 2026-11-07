"""PUP evidence and meaningful hand, master/automaton recipient, maneuver/automaton-action timing and distinct-copy rejection checks."""
from dataclasses import replace
import hashlib,json
from pathlib import Path
import pytest
from vanadiel_nexus.core.equipment_hands import hand_types,EVIDENCE,EVIDENCE_REVISION
from vanadiel_nexus.core.equipment_matching import requirements_match,allocate_requirements
from vanadiel_nexus.core.guide_catalog import validate_catalog,composition_diagnostics
from vanadiel_nexus.core.item_res import Item
F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(n):return json.loads((F/n).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
@pytest.fixture
def batch():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json');items={r['id']:Item(**r) for r in p['items']};return c,p,items,hand_types(items)
def rev(c,k):return next(r for r in c['revisions'] if r['set_id']=='nexus:pup:'+k)
def slots(c,k):return {s['slot']:s for s in rev(c,k)['slots']}
def ctx(c,k):return next(s['context'] for s in c['sets'] if s['id']=='nexus:pup:'+k)
DEFS=read('gear-guide-t7-pup-definitions.json')['definitions'];KEYS=[d['key'] for d in DEFS];PAIR={d['key']:d['pair'] for d in DEFS}
MAIN={'H':20511,'M':20511,'O':20535,'R':21526,'W':21526,'T':20542,'C':21527,'D':20516}
RANGE={'H':21457,'M':21433,'O':21457,'R':21459,'W':21457,'T':21433,'C':21459,'D':21459}
def test_history(batch):
 c,_,items,h=batch;b=next(b for b in c['authoring_batches'] if b['id']=='pup-2026-11-05')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':483,'revisions':494,'sources':1045}
 for f,m in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in m.items())
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert [len(c[f]) for f in ('sets','revisions','sources','coverage')]==[520,547,1331,231]
 gaps=[r for r in c['coverage'] if r['status']=='gap'];assert len(gaps)==0 and {r['job'] for r in gaps}==set()
 assert 'all22jobs' in c['delivery_status'] and 'DNC' in c['delivery_status'];validate_catalog(c,items=items,hand_types=h)
@pytest.mark.parametrize('key',KEYS)
def test_exact_hands_slots_and_unknown_rejection(batch,key):
 c,_,items,h=batch;s=slots(c,key);r=rev(c,key);m=MAIN[PAIR[key]]
 assert len(s)==16 and s['main']['item_id']==m and s['range']['item_id']==RANGE[PAIR[key]]
 assert s['sub']==dict(slot='sub',state='empty') and s['ammo']==dict(slot='ammo',state='empty')
 assert h[m]=='hand_to_hand' and RANGE[PAIR[key]] not in h and items[RANGE[PAIR[key]]].slots==4
 assert not composition_diagnostics(r['slots'],items,['PUP'],hand_types=h,context=ctx(c,key))
 # Any sub weapon beside a hand-to-hand main is rejected, even with an explicit dual-wield claim.
 withsub=[dict(x) for x in r['slots']]
 for x in withsub:
  if x['slot']=='sub':x.clear();x.update(slot='sub',state='selected',item_id=21738,name='Telopanos Axe',requirements={})
 assert 'main/sub: incompatible equipment' in composition_diagnostics(withsub,items,['PUP','BST'],hand_types=h,context=dict(ctx(c,key),dual_wield=True))
 # A changed exact-ID record loses its reviewed classification (no unknown-hand waiver).
 bad=dict(items);bad[m]=replace(items[m],skill=5);assert m not in hand_types(bad)
 assert composition_diagnostics(r['slots'],items,['WHM'],hand_types=h,context=ctx(c,key))
 cx=ctx(c,key);assert cx['dual_wield'] is False and 'current/maxHP' in cx['transitions'] and 'ever added to master totals' in cx['automaton_inputs'] and cx['recipient'] and cx['automaton']
def test_empty_sub_still_needs_reviewed_main(batch):
 c,_,items,h=batch
 # The structural validator judges only main/sub combinations, so an empty sub yields no hand diagnostic...
 assert not composition_diagnostics(rev(c,'dt-idle')['slots'],items,['PUP'],hand_types=h,context={})
 # ...therefore the batch gate requires a reviewed exact main classification for every composition.
 assert all(h.get(slots(c,k)['main']['item_id'])=='hand_to_hand' for k in KEYS)
 stripped=dict(items);stripped[20511]=replace(items[20511],slots=3);assert 20511 not in hand_types(stripped)
 assert len(EVIDENCE)==55 and EVIDENCE_REVISION=='hands.2026-11-05.v19' and [e.item_id for e in EVIDENCE[48:53]]==[20511,21526,20535,20542,20516]
@pytest.mark.parametrize('key,name',[('refresh-idle','Stikini Ring +1'),('engaged-accuracy','Chirich Ring +1')])
def test_distinct_ring_allocation(batch,key,name):
 c,_,_,_=batch;r=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(r)==2
 def alloc(n):return allocate_requirements(r,[dict(item_id=r[0]['item_id'],character_key='fictional',count=n)],'fictional')
 assert sum(x['owned'] for x in alloc(1).values())==1
 assert sum(x['owned'] for x in alloc(2).values())==2
def test_recipients_and_timing(batch):
 c,_,_,_=batch
 for k in ('dt-idle','refresh-idle','engaged-balanced','engaged-dt','engaged-accuracy','stringing-pummel','asuran-fists'):assert ctx(c,k)['recipient'].startswith('master (')
 for k in ('pet-engaged-melee','pet-engaged-ranged','overdrive-sharpshot','pet-ws','pet-magic'):assert ctx(c,k)['recipient'].startswith('automaton (') and 'not Nexus-certified' in ctx(c,k)['recipient']
 assert ctx(c,'hybrid-engaged')['recipient'].startswith('master and automaton') and ctx(c,'maneuver')['recipient'].startswith('master action')
 assert 'when the maneuver is used' in ctx(c,'maneuver')['action'] and slots(c,'maneuver')['body']['item_id']==23504 and slots(c,'maneuver')['main']['item_id']==slots(c,'hybrid-engaged')['main']['item_id']
 assert 'cannot intercept' in ctx(c,'pet-ws')['action'] and 'before the automaton begins casting' in ctx(c,'pet-magic')['action']
 assert 'Overdrive SP ability active' in ctx(c,'overdrive-sharpshot')['action'] and 'Bean Daifuku only if actually eaten' in ctx(c,'overdrive-sharpshot')['action']
 assert ctx(c,'refresh-idle')['job']=='PUP99/WHM49' and 'usable subjob maxMP' in ctx(c,'refresh-idle')['action']
 assert slots(c,'refresh-idle')['body']['item_id']==26969 and slots(c,'refresh-idle')['head']['item_id']==24270
 a=slots(c,'automaton-refresh-idle');assert (a['main']['item_id'],a['head']['item_id'],a['back']['item_id'])==(20516,23415,28642) and 'mage automaton' in ctx(c,'automaton-refresh-idle')['action']
 assert 'PUP main job' in ctx(c,'stringing-pummel')['action'] and 'The Walls of Your Mind' in ctx(c,'asuran-fists')['action']
 for k in KEYS:
  e=[x for x in rev(c,k)['slots'] if x.get('item_id')==25524];assert all(x['slot']=='ear2' for x in e)
def test_literal_copies_and_source_distinctions(batch):
 c,_,_,_=batch
 stp=slots(c,'engaged-balanced')['back']['requirements'];crit=slots(c,'stringing-pummel')['back']['requirements'];wsd=slots(c,'asuran-fists')['back']['requirements']
 assert requirements_match(stp,{'augments':['DEX+20','Accuracy+20 Attack+20','"Store TP"+10','DEX+10','Phys. dmg. taken -10%']})
 assert not requirements_match(stp,{'augments':['DEX+30','Accuracy+20 Attack+20','"Store TP"+10','Phys. dmg. taken -10%']})
 assert not requirements_match(crit,{'augments':['STR+30','Accuracy+20','Attack+20','Critical Hit Rate+10%','PDT-10%']})
 assert not requirements_match(wsd,{'augments':['STR+20','Accuracy+20 Attack+20','Weapon skill damage+10%','STR+10','Phys. dmg. taken -10%']})
 assert slots(c,'engaged-dt')['back']['requirements']==stp
 for k in ('hybrid-engaged','pet-engaged-melee','pet-durability','pet-ws','overdrive-sharpshot'):assert slots(c,k)['back']=={'slot':'back','state':'selected','item_id':26263,'name':"Visucius's Mantle",'requirements':{}}
 o=read('gear-guide-t7-pup-observations.json');by={r['key']:r for r in o['table_observations']}
 assert by['node-tp-kenkonken']['slot_grid']['main']==[18988] and slots(c,'engaged-balanced')['main']['item_id']==20511
 assert by['node-od-ss']['slot_grid']['back']==[28634] and slots(c,'overdrive-sharpshot')['back']['item_id']==26263
 assert by['node-turtle-tank']['slot_grid']['head']==[26675] and slots(c,'pet-durability')['head']['item_id']!=26675
 assert by['node-pet-tp']['slot_grid']['head']==[26735] and slots(c,'pet-engaged-melee')['head']['item_id']==25564
 assert by['node-hp-dt-meva']['slot_grid']['main']==[] and slots(c,'dt-idle')['main']['item_id']==20511
 assert by['bg-tp-kenkonken-25dt']['grid']['range']==['Neo Animator'] and slots(c,'engaged-balanced')['range']['item_id']==21433
 assert by['node-inventory']['composition_kind']=='equipment_options' and 'no Cloudflare/bot check was completed or bypassed' in o['access']
def test_evidence_reconciliation(batch):
 c,p,_,_=batch;o=read('gear-guide-t7-pup-observations.json');cards=read('gear-guide-t7-pup-item-evidence.json')['items'];d=read('gear-guide-t7-pup-definitions.json')
 assert len(o['table_observations'])==31 and len(o['guide_observations'])==25 and len(cards)==26
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert all(r['independent_public_card_verified'] and any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources']) for r in cards)
 assert len(d['definitions'])==16 and len(d['coverage_reconciliation'])==10
 assert all(r['original_row']['status']=='gap' and r['current_row']['status']=='included' and r['current_row']['set_ids'] for r in d['coverage_reconciliation'])
 assert len(p['items'])==863 and len(EVIDENCE)==55
