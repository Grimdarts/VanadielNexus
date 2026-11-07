"""DNC evidence and meaningful hand, dual-wield, Waltz recipient, Step/Flourish timing and distinct-copy rejection checks."""
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
def rev(c,k):return next(r for r in c['revisions'] if r['set_id']=='nexus:dnc:'+k)
def slots(c,k):return {s['slot']:s for s in rev(c,k)['slots']}
def ctx(c,k):return next(s['context'] for s in c['sets'] if s['id']=='nexus:dnc:'+k)
DEFS=read('gear-guide-t7-dnc-definitions.json')['definitions'];KEYS=[d['key'] for d in DEFS]
MAIN,SUB=20584,20587
def test_history(batch):
 c,_,items,h=batch;b=next(b for b in c['authoring_batches'] if b['id']=='dnc-2026-11-05')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':499,'revisions':510,'sources':1127}
 for f,m in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in m.items())
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert [len(c[f]) for f in ('sets','revisions','sources','coverage')]==[520,547,1331,231]
 assert not [r for r in c['coverage'] if r['status']=='gap'] and not any(r['status']=='not_applicable' for r in c['coverage'])
 assert 'all22jobs' in c['delivery_status'] and 'DNC' in c['delivery_status'];validate_catalog(c,items=items,hand_types=h)
 # The original DNC pilot (DT Shell V, ten slots, unresolved) is preserved unchanged.
 assert next(r for r in c['revisions'] if r['set_id']=='ffxiah:367871:dnc')['verification']['status']=='unresolved'
@pytest.mark.parametrize('key',KEYS)
def test_exact_hands_slots_dual_wield_and_unknown_rejection(batch,key):
 c,_,items,h=batch;s=slots(c,key);r=rev(c,key)
 assert len(s)==16 and s['main']['item_id']==MAIN and s['sub']['item_id']==SUB and s['range']==dict(slot='range',state='empty')
 assert h[MAIN]=='one_handed' and h[SUB]=='one_handed'
 assert not composition_diagnostics(r['slots'],items,['DNC'],hand_types=h,context=ctx(c,key))
 # Two one-handed daggers without an explicit dual-wield context are rejected.
 assert 'main/sub: dual wield is unconfirmed' in composition_diagnostics(r['slots'],items,['DNC'],hand_types=h,context=dict(ctx(c,key),dual_wield=False))
 # A changed exact-ID record loses its reviewed classification (no unknown-hand waiver).
 bad=dict(items);bad[MAIN]=replace(items[MAIN],skill=3);assert MAIN not in hand_types(bad)
 assert 'main/sub: unresolved weapon legality' in composition_diagnostics(r['slots'],bad,['DNC'],hand_types=hand_types(bad),context=ctx(c,key))
 assert composition_diagnostics(r['slots'],items,['WHM'],hand_types=h,context=ctx(c,key))
 cx=ctx(c,key);assert cx['dual_wield'] is True and 'current/maxHP' in cx['transitions'] and 'never inferred' in cx['finishing_moves'] and cx['recipient']
 assert all(z['requirements']=={} for z in r['slots'] if z['state']=='selected')
def test_empty_sub_still_needs_reviewed_main(batch):
 c,_,items,h=batch
 noSub=[dict(z) if z['slot']!='sub' else dict(slot='sub',state='empty') for z in rev(c,'dt-idle')['slots']]
 # The structural validator judges only main/sub combinations, so an empty sub yields no hand diagnostic...
 assert not composition_diagnostics(noSub,items,['DNC'],hand_types=h,context={})
 # ...therefore the batch gate requires reviewed exact classification of both daggers in every composition.
 assert all(h.get(slots(c,k)['main']['item_id'])=='one_handed' and h.get(slots(c,k)['sub']['item_id'])=='one_handed' for k in KEYS)
 assert len(EVIDENCE)==55 and EVIDENCE_REVISION=='hands.2026-11-05.v19' and [e.item_id for e in EVIDENCE[53:]]==[20584,20587]
@pytest.mark.parametrize('key,name',[('dt-idle','Moonlight Ring'),('refresh-idle','Stikini Ring +1'),('steps','Mache Earring +1')])
def test_distinct_copy_allocation(batch,key,name):
 c,_,_,_=batch;r=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(r)==2
 def alloc(n):return allocate_requirements(r,[dict(item_id=r[0]['item_id'],character_key='fictional',count=n)],'fictional')
 assert sum(x['owned'] for x in alloc(1).values())==1
 assert sum(x['owned'] for x in alloc(2).values())==2
def test_recipients_timing_and_costs(batch):
 c,_,_,_=batch;w=ctx(c,'curing-waltz')
 assert 'received' in w['recipient'] and 'only when the Dancer is the recipient' in w['recipient'] and 'Other target' in w['waltz_targets']
 assert 'Saber Dance must be inactive' in w['action'] and slots(c,'curing-waltz')['body']['item_id']==23958
 assert 'Steps 100 TP' in w['tp_costs'] and 'potency received lines apply only to the wearer' in w['recipients']
 assert 'Step must hit' in ctx(c,'steps')['action'] and slots(c,'steps')['feet']['item_id']==24116
 assert 'Finishing Move' in ctx(c,'violent-flourish')['action'] and 'converts 1-5 actual Finishing Moves' in ctx(c,'reverse-flourish')['action']
 assert 'activation' in ctx(c,'climactic-flourish')['action'] and slots(c,'climactic-flourish')['head']['item_id']==23438
 assert 'Fan Dance must be inactive' in ctx(c,'samba')['action'] and slots(c,'samba')['back']['item_id']==26264
 assert ctx(c,'refresh-idle')['job']=='DNC99/WHM49' and 'no native MP' in ctx(c,'refresh-idle')['action']
 assert slots(c,'refresh-idle')['head']['item_id']==24270
 assert 'Kupofried' in ctx(c,'rudra-storm')['action'] and 'not asserted to grant it' in ctx(c,'rudra-storm')['action']
 assert 'Terpsichore in the main hand' in ctx(c,'pyrrhic-kleos')['action'] and 'Climactic Flourish is active' in ctx(c,'climactic-rudra')['action']
 for k in KEYS:
  assert all(z['slot']=='ear2' for z in rev(c,k)['slots'] if z.get('item_id')==25528)
def test_source_distinctions(batch):
 c,_,_,_=batch;o=read('gear-guide-t7-dnc-observations.json');by={r['key']:r for r in o['table_observations']}
 assert by['node-380094']['slot_grid']['main']==[19398] and slots(c,'rudra-storm')['sub']['item_id']==20587
 assert by['node-348201']['slot_grid']['ear1']==[] and by['node-348201']['slot_grid']['back']==[]
 assert [slots(c,'dt-idle')[s]['item_id'] for s in ('ammo','head','neck','ring1','ring2','waist')]==[22279,23732,26002,26190,26190,28414]
 assert by['cdg-tp-terpsichore']['grid']['main']==['Terpsichore (Level 119 III)'] and by['cdg-tp-terpsichore']['grid']['back']==["Senuna's Mantle"]
 assert slots(c,'engaged-balanced')['back']['item_id']==26274 and by['cdg-normal-rudra']['grid']['ear1']==['Moonshade Earring']
 assert slots(c,'rudra-storm')['ear1']['item_id']==27537 and by['cdg-waltz']['grid']['hands']==['Herculean Gloves'] and slots(c,'curing-waltz')['hands']['item_id']==25826
 assert sum(r.get('composition_kind')=='slot_grid' for r in o['table_observations'])==58 and 'no Cloudflare/bot check was completed or bypassed' in o['access']
def test_evidence_reconciliation(batch):
 c,p,_,_=batch;o=read('gear-guide-t7-dnc-observations.json');cards=read('gear-guide-t7-dnc-item-evidence.json')['items'];d=read('gear-guide-t7-dnc-definitions.json')
 assert len(o['table_observations'])==90 and len(o['guide_observations'])==23 and len(cards)==31
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert all(r['independent_public_card_verified'] and any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources']) for r in cards)
 assert len(d['definitions'])==15 and len(d['coverage_reconciliation'])==9
 assert all(r['original_row']['status']=='gap' and r['current_row']['status']=='included' and r['current_row']['set_ids'] for r in d['coverage_reconciliation'])
 assert len(p['items'])==863 and len(EVIDENCE)==55
