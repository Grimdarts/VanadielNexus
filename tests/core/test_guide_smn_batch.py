"""SMN composition boundaries, exact hands, independent copies and source conflicts."""
from copy import deepcopy
from dataclasses import replace
import hashlib,json
from pathlib import Path
import pytest
from vanadiel_nexus.core.equipment_hands import EVIDENCE,hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS,requirements_match,allocate_requirements
from vanadiel_nexus.core.guide_catalog import validate_catalog,composition_diagnostics
from vanadiel_nexus.core.item_res import Item
F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(n):return json.loads((F/n).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
@pytest.fixture
def batch():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json');items={r['id']:Item(**r) for r in p['items']}
 return c,p,items,hand_types(items)
def rev(c,key):return next(r for r in c['revisions'] if r['set_id']=='nexus:smn:'+key)
def slots(c,key):return {s['slot']:s for s in rev(c,key)['slots']}
def ctx(c,key):return next(s['context'] for s in c['sets'] if s['id']=='nexus:smn:'+key)
def test_history_and_explicit_gaps_survive(batch):
 c,p,items,hands=batch;b=next(b for b in c['authoring_batches'] if b['id']=='smn-2026-11-04')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':252,'revisions':263,'sources':453}
 for f,history in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in history.items())
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 assert [len(c[f]) for f in ('sets','revisions','sources','coverage')]==[520,547,1331,231]
 assert len(p['items'])==863
 drg=[r for r in c['coverage'] if r['job']=='DRG'];assert len(drg)==8 and all(r['status']=='included' for r in drg)
 smn=[r for r in c['coverage'] if r['job']=='SMN'];assert len(smn)==17 and all(r['status']=='included' and r['set_ids'] for r in smn)
 assert sum(r['status']=='gap' for r in c['coverage'])==0 and not any(r['status']=='not_applicable' for r in c['coverage'])
 validate_catalog(c,items=items,hand_types=hands)
@pytest.mark.parametrize('item_id,kind',[(21149,'two_handed'),(21174,'two_handed'),(19058,'grip')])
def test_exact_hand_registry_is_fail_closed(batch,item_id,kind):
 c,p,items,hands=batch
 assert len(EVIDENCE)==55 and hands[item_id]==kind
 changed=deepcopy(items);changed[item_id]=replace(items[item_id],skill=10)
 assert item_id not in hand_types(changed)
 key='perpetuation' if item_id==21174 else 'ward-skill'
 assert composition_diagnostics(list(slots(c,key).values()),changed,['SMN'],hand_types=hand_types(changed))
@pytest.mark.parametrize('key',['physical-multihit','physical-single','physical-accuracy','magical-pact','magical-accuracy','flaming-crush','ward-skill','bp-recast','dt-idle','refresh-idle','perpetuation','pet-durability','summoning-precast','retribution'])
def test_all_full_compositions_retain_pet_ammo_and_no_invented_rank(batch,key):
 c,p,items,hands=batch;r=rev(c,key);s=slots(c,key)
 assert {x['slot'] for x in r['slots']}==set(SLOTS)
 assert s['range']=={'slot':'range','state':'empty'} and s['ammo']['item_id']==21381
 assert not composition_diagnostics(r['slots'],items,['SMN'],hand_types=hands,context=ctx(c,key))
 assert r['origin']=='nexus_recommendation' and r['currency']=='unknown'
 assert all('rank' not in x.get('requirements',{}) for x in r['slots'])
 for x in r['slots']:
  if x.get('item_id')==25504:assert x['slot']=='ear2' and not x['requirements']
@pytest.mark.parametrize('key,slot,copy',[
 ('pet-durability','back',{'augments':['Pet: Damage taken -5%']}),
 ('summoning-precast','back',{'augments':['"Fast Cast"+10']}),
 ('retribution','back',{'augments':['STR+20','Accuracy+20 Attack+20','STR+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('retribution','ear1',{'augments':['Attack+4','TP Bonus +250']}),
 ('retribution','body',{'path':'B'})])
def test_literal_decoded_copies_are_not_source_summary_totals(batch,key,slot,copy):
 requirement=slots(batch[0],key)[slot]['requirements']
 assert requirements_match(requirement,copy) and not requirements_match(requirement,{})
 if 'augments' in copy:assert not requirements_match(requirement,{'augments':copy['augments'][:-1]})
def test_separate_master_pet_and_timing_contexts(batch):
 c,_,_,_=batch
 assert slots(c,'physical-multihit')['hands']['item_id']==23999
 assert slots(c,'physical-single')['hands']['item_id']==23568
 assert slots(c,'physical-accuracy')['hands']['item_id']==23568
 assert slots(c,'magical-pact')['hands']['item_id']==27107 and slots(c,'magical-accuracy')['hands']['item_id']==23568
 assert slots(c,'magical-pact')['legs']['item_id']==23635 and slots(c,'flaming-crush')['legs']['item_id']==24044
 assert 'Ifrit Flaming Crush' in ctx(c,'flaming-crush')['action']
 assert 'Pet TP/merits unknown'==ctx(c,'magical-accuracy')['pet_tp']
 assert ctx(c,'magical-pact')['burst']=='Free magical pact; no skillchain window assumed'
 assert 'Favor active' in ctx(c,'bp-recast')['favor']
 assert slots(c,'bp-recast')['body']['item_id']==23456 and slots(c,'ward-skill')['body']['item_id']==26542
 assert '500 SMN JP' in ctx(c,'ward-skill')['access']
 assert 'Master TP distinct from pet TP' in ctx(c,'retribution')['pet_tp']
 assert slots(c,'pet-durability')['back']['requirements']!={'augments':['Damage taken-5%']}
def test_duplicate_rings_need_two_fictional_copies(batch):
 for key,item_id in [('physical-multihit',26180),('refresh-idle',26184)]:
  ring_slots=[s for s in slots(batch[0],key).values() if s.get('item_id')==item_id]
  one=allocate_requirements(ring_slots,[dict(item_id=item_id,character_key='fictional',count=1)],'fictional')
  two=allocate_requirements(ring_slots,[dict(item_id=item_id,character_key='fictional',count=2)],'fictional')
  assert sum(r['owned'] for r in one.values())==1 and sum(r['owned'] for r in two.values())==2
def test_source_conflicts_and_omissions_not_silently_repaired():
 o=read('gear-guide-t7-smn-observations.json');rows=o['table_observations'];assert len(rows)==17
 for r in rows+o['guide_observations']:assert digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256']
 by={r['item_set_id']:r for r in rows}
 assert by[366319]['grid']['sub']==['Elan Strap +1','Opashoro']
 assert set(by[366342]['conflicting_slots'])=={'hands','feet'}
 assert len(by[366308]['ordered_macro_cells'])==7 and 'sub' in by[366308]['omitted_slots']
 assert 'ammo' in by[366324]['omitted_slots'] and 'main' in by[401864]['omitted_slots']
 assert 'Master WS' not in by[366319]['title']
 cards=read('gear-guide-t7-smn-item-evidence.json')['items'];assert len(cards)==34
 assert all(r['independent_public_card_verified'] and digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256'] for r in cards)
 assert 'base only' in next(r for r in cards if r['item_id']==21149)['conflict']
 d=read('gear-guide-t7-smn-definitions.json');assert len(d['definitions'])==14
 assert any('engaged' in s for s in d['unclaimed'])
