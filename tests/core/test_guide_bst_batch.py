"""BST evidence and meaningful hand, master/pet recipient, Ready timing and distinct-copy rejection checks."""
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
def rev(c,k):return next(r for r in c['revisions'] if r['set_id']=='nexus:bst:'+k)
def slots(c,k):return {s['slot']:s for s in rev(c,k)['slots']}
def ctx(c,k):return next(s['context'] for s in c['sets'] if s['id']=='nexus:bst:'+k)
DEFS=read('gear-guide-t7-bst-definitions.json')['definitions'];KEYS=[d['key'] for d in DEFS];PAIR={d['key']:d['pair'] for d in DEFS}
HANDS={'A':(21730,21723),'B':(20793,21738),'C':(21730,21738),'S':(21730,26488)}
def test_history(batch):
 c,_,items,h=batch;b=next(b for b in c['authoring_batches'] if b['id']=='bst-2026-11-05')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':469,'revisions':480,'sources':967}
 for f,m in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in m.items())
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert [len(c[f]) for f in ('sets','revisions','sources','coverage')]==[520,547,1331,231]
 gaps=[r for r in c['coverage'] if r['status']=='gap'];assert len(gaps)==0 and {r['job'] for r in gaps}==set()
 assert 'all22jobs' in c['delivery_status'];validate_catalog(c,items=items,hand_types=h)
@pytest.mark.parametrize('key',KEYS)
def test_exact_hands_slots_and_unknown_rejection(batch,key):
 c,_,items,h=batch;s=slots(c,key);r=rev(c,key);m,sub=HANDS[PAIR[key]]
 assert len(s)==16 and s['main']['item_id']==m and s['sub']['item_id']==sub and s['range']==dict(slot='range',state='empty')
 assert h[m]=='one_handed' and h[sub]==('shield' if PAIR[key]=='S' else 'one_handed')
 assert not composition_diagnostics(r['slots'],items,['BST'],hand_types=h,context=ctx(c,key))
 bad=dict(items);bad[m]=replace(items[m],skill=12);assert m not in hand_types(bad)
 assert composition_diagnostics(r['slots'],bad,['BST'],hand_types=hand_types(bad),context=ctx(c,key))
 wrong=dict(h);wrong[m]='two_handed';assert composition_diagnostics(r['slots'],items,['BST'],hand_types=wrong,context=ctx(c,key))
 assert composition_diagnostics(r['slots'],items,['WHM'],hand_types=h,context=ctx(c,key))
 if PAIR[key]!='S':
  nodw=dict(ctx(c,key),dual_wield=False);assert 'main/sub: dual wield is unconfirmed' in composition_diagnostics(r['slots'],items,['BST'],hand_types=h,context=nodw)
 else:assert ctx(c,key)['dual_wield'] is False and ctx(c,key)['job']=='BST99/WHM49'
 assert 'current/maxHP' in ctx(c,key)['transitions'] and 'recipient' in ctx(c,key) and 'never added to master' in ctx(c,key)['pet']
def test_empty_sub_still_needs_reviewed_main(batch):
 c,_,items,h=batch;r=[dict(x) for x in rev(c,'dt-idle')['slots']]
 for x in r:
  if x['slot']=='sub':x.clear();x.update(slot='sub',state='empty')
 # The structural validator only judges main/sub combinations, so an empty sub yields no diagnostic.
 assert not composition_diagnostics(r,items,['BST'],hand_types=h,context={})
 # The batch gate itself requires a reviewed exact main classification for every composition, empty sub or not.
 assert all(h.get(slots(c,k)['main']['item_id'])=='one_handed' for k in KEYS)
 stripped=dict(items);stripped[21730]=replace(items[21730],slots=1);assert 21730 not in hand_types(stripped)
 assert len(EVIDENCE)==55 and EVIDENCE_REVISION=='hands.2026-11-05.v19' and [e.item_id for e in EVIDENCE[43:48]]==[21730,21723,20793,21738,26488]
@pytest.mark.parametrize('key,name',[('refresh-idle','Stikini Ring +1'),('engaged-accuracy','Chirich Ring +1')])
def test_distinct_ring_allocation(batch,key,name):
 c,_,_,_=batch;r=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(r)==2
 def alloc(n):return allocate_requirements(r,[dict(item_id=r[0]['item_id'],character_key='fictional',count=n)],'fictional')
 assert sum(x['owned'] for x in alloc(1).values())==1
 assert sum(x['owned'] for x in alloc(2).values())==2
def test_pet_recipient_weapon_and_timing(batch):
 c,_,_,_=batch
 for k in ('ready-physical','ready-multihit','ready-magical','pet-durability','ready-precast'):assert slots(c,k)['main']['item_id']==20793 and 'main' in ctx(c,k)['weapon_pair'].lower()
 assert slots(c,'pet-accuracy')['main']['item_id']==21730 and slots(c,'pet-accuracy')['sub']['item_id']==21738
 assert slots(c,'ready-precast')['legs']['item_id']==23777 and 'when Ready is used' in ctx(c,'ready-precast')['action']
 assert slots(c,'ready-physical')['hands']['item_id']==23562 and 'until the move resolves' in ctx(c,'ready-physical')['action']
 assert slots(c,'blitz')['ear2']['item_id']==25470 and 'Level 119 II or higher' in ctx(c,'blitz')['action'] and 'main job' in ctx(c,'mistral-axe')['action']
 assert ctx(c,'refresh-idle')['job']=='BST99/WHM49' and 'usable subjob maxMP' in ctx(c,'refresh-idle')['action']
 assert slots(c,'refresh-idle')['head']['item_id']==24270 and slots(c,'refresh-idle')['neck']['item_id']==26002
 assert ctx(c,'ready-physical')['recipient'].startswith('pet') and ctx(c,'dt-idle')['recipient']=='master'
def test_literal_copies_and_source_distinctions(batch):
 c,_,_,_=batch
 stp=slots(c,'engaged-dt')['back']['requirements'];wsd=slots(c,'blitz')['back']['requirements'];crit=slots(c,'rampage')['back']['requirements']
 assert requirements_match(stp,{'augments':['DEX+20','Accuracy+20 Attack+20','Accuracy+10','"Store TP"+10','Phys. dmg. taken -10%']})
 assert not requirements_match(stp,{'augments':['DEX+20','Accuracy+30','Attack+20','"Store TP"+10','Phys. dmg. taken -10%']})
 assert not requirements_match(wsd,{'augments':['STR+30','Accuracy+20 Attack+20','Weapon skill damage +10%']})
 assert not requirements_match(crit,{'augments':['STR+20','Accuracy+20 Attack+20','STR+10','Critical hit rate +10%']})
 assert not requirements_match(slots(c,'rampage')['ear1']['requirements'],{'augments':['Attack+4','TP Bonus+250']})
 for k in ('ready-physical','pet-accuracy','pet-durability'):assert slots(c,k)['back']=={'slot':'back','state':'selected','item_id':26254,'name':"Artio's Mantle",'requirements':{}}
 o=read('gear-guide-t7-bst-observations.json');by={r['key']:r for r in o['table_observations']}
 assert by['bg-tp-25dt']['grid']['main']==['Spalirisos (Level 119 II)'] and slots(c,'engaged-balanced')['main']['item_id']==21730
 assert by['node-ready-magic']['item_ids'][:2]==[20809,20809] and slots(c,'ready-magical')['main']['item_id']==20793
 assert by['node-ready-multihit']['item_ids'][0]==21751 and slots(c,'ready-multihit')['main']['item_id']==20793
 assert by['idle-refresh']['item_ids'].count(26184)==2 and 25416 in by['idle-refresh']['item_ids']
 assert by['node-inventory']['composition_kind']=='equipment_options' and 'no Cloudflare/bot check was completed or bypassed' in o['access']
def test_evidence_reconciliation(batch):
 c,p,_,_=batch;o=read('gear-guide-t7-bst-observations.json');cards=read('gear-guide-t7-bst-item-evidence.json')['items'];d=read('gear-guide-t7-bst-definitions.json')
 assert len(o['table_observations'])==29 and len(o['guide_observations'])==13 and len(cards)==36
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert all(r['independent_public_card_verified'] and any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources']) for r in cards)
 assert len(d['definitions'])==14 and len(d['coverage_reconciliation'])==11
 assert all(r['original_row']['status']=='gap' and r['current_row']['status']=='included' and r['current_row']['set_ids'] for r in d['coverage_reconciliation'])
 assert len(p['items'])==863 and len(EVIDENCE)==55
