"""BLU literal copies, explicit action/trait contexts and source conflict preservation."""
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
def rev(c,key):return next(r for r in c['revisions'] if r['set_id']=='nexus:blu:'+key)
def slots(c,key):return {s['slot']:s for s in rev(c,key)['slots']}
def ctx(c,key):return next(s['context'] for s in c['sets'] if s['id']=='nexus:blu:'+key)
def test_append_only_prior_batches_and_deferred_brd_drg(batch):
 c,p,items,hands=batch;b=next(b for b in c['authoring_batches'] if b['id']=='blu-2026-11-04')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':266,'revisions':277,'sources':508}
 for f,history in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in history.items())
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 assert [len(c[f]) for f in ('sets','revisions','sources','coverage')]==[520,547,1331,231] and len(p['items'])==863
 drg=[r for r in c['coverage'] if r['job']=='DRG'];assert len(drg)==8 and all(r['status']=='included' for r in drg)
 blu=[r for r in c['coverage'] if r['job']=='BLU'];assert len(blu)==11 and all(r['status']=='included' and r['set_ids'] for r in blu)
 assert sum(r['status']=='gap' for r in c['coverage'])==0 and not any(r['status']=='not_applicable' for r in c['coverage'])
 validate_catalog(c,items=items,hand_types=hands)
@pytest.mark.parametrize('key',['dt-idle','refresh-idle','engaged-balanced','engaged-dt','engaged-accuracy','savage-blade','sanguine-blade','red-lotus-blade','magical-free','magical-burst','physical-sinker','physical-chain-efflux','spell-accuracy','skill-occultation','magic-fruit','general-precast','blue-precast'])
def test_composition_requires_real_usable_spell_set_dual_wield(batch,key):
 c,_,items,hands=batch;r=rev(c,key);context=ctx(c,key)
 assert {s['slot'] for s in r['slots']}==set(SLOTS) and slots(c,key)['range']=={'slot':'range','state':'empty'}
 assert not composition_diagnostics(r['slots'],items,['BLU'],hand_types=hands,context=context)
 assert composition_diagnostics(r['slots'],items,['BLU'],hand_types=hands,context={**context,'dual_wield':False})
 assert context['dual_wield'] is True and 'Delta Thrust + Barbed Crescent' in context['spell_set']
 assert 'no ML or JP gifts assumed' in context['job'] and r['origin']=='nexus_recommendation' and r['currency']=='unknown'
 assert all('rank' not in s.get('requirements',{}) for s in r['slots'])
def test_new_exact_hand_fails_closed_after_classification_change(batch):
 _,_,items,hands=batch
 assert len(EVIDENCE)==55 and EVIDENCE[32].item_id==22041 and hands[22041]=='one_handed'
 changed=deepcopy(items);changed[22041]=replace(items[22041],skill=12)
 assert 22041 not in hand_types(changed)
 assert composition_diagnostics(rev(batch[0],'magical-free')['slots'],changed,['BLU'],hand_types=hand_types(changed),context={'dual_wield':True})
@pytest.mark.parametrize('key,slot,copy',[
 ('engaged-balanced','back',{'augments':['DEX+20','Accuracy+20 Attack+20','DEX+10','"Dbl.Atk."+10','Damage taken-5%']}),
 ('savage-blade','back',{'augments':['STR+20','Accuracy+20 Attack+20','STR+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('magical-free','back',{'augments':['INT+20','Mag. Acc+20 /Mag. Dmg.+20','INT+10','"Mag.Atk.Bns."+10','Damage taken-5%']}),
 ('sanguine-blade','back',{'augments':['INT+20','Mag. Acc+20 /Mag. Dmg.+20','INT+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('magic-fruit','back',{'augments':['MND+20','Mag. Acc+20 /Mag. Dmg.+20','MND+10','"Cure" potency +10%','Damage taken-5%']}),
 ('general-precast','back',{'augments':['"Fast Cast"+10']}),
 ('savage-blade','ear1',{'augments':['Attack+4','TP Bonus +250']}),
 ('savage-blade','body',{'path':'B'})])
def test_independent_literal_decoded_copies(batch,key,slot,copy):
 requirement=slots(batch[0],key)[slot]['requirements']
 assert requirements_match(requirement,copy) and not requirements_match(requirement,{})
 bad=deepcopy(copy)
 if 'augments' in bad:bad['augments']=bad['augments'][:-1]
 else:bad['path']='A'
 assert not requirements_match(requirement,bad)
@pytest.mark.parametrize('key,item_id',[('refresh-idle',26184),('engaged-accuracy',26182),('physical-sinker',28527),('magic-fruit',27567)])
def test_two_selected_slots_need_two_actual_copies(batch,key,item_id):
 requirements=[s for s in rev(batch[0],key)['slots'] if s.get('item_id')==item_id]
 assert len(requirements)==2
 one=allocate_requirements(requirements,[dict(item_id=item_id,character_key='fictional',count=1)],'fictional')
 two=allocate_requirements(requirements,[dict(item_id=item_id,character_key='fictional',count=2)],'fictional')
 assert sum(r['owned'] for r in one.values())==1 and sum(r['owned'] for r in two.values())==2
def test_abilities_casting_and_healing_never_collapse(batch):
 c,_,_,_=batch
 assert slots(c,'magical-free')['legs']['item_id']==23614 and slots(c,'magical-burst')['legs']['item_id']==23591
 assert 'Burst Affinity active' in ctx(c,'magical-burst')['abilities'] and 'compatible ice burst' in ctx(c,'magical-burst')['action']
 assert slots(c,'physical-sinker')['feet']['item_id']==23681 and slots(c,'physical-chain-efflux')['feet']['item_id']==23658
 assert 'Chain Affinity and Efflux active' in ctx(c,'physical-chain-efflux')['abilities']
 assert slots(c,'general-precast')['body']['item_id']==23480 and slots(c,'blue-precast')['body']['item_id']==23502
 assert slots(c,'blue-precast')['hands']['item_id']==23569
 assert slots(c,'spell-accuracy')['ear2']['item_id']==25510 and not slots(c,'spell-accuracy')['ear2']['requirements']
 assert 'Erratic Flutter active' in ctx(c,'engaged-balanced')['haste'] and 'no aftermath' in ctx(c,'savage-blade')['haste']
 assert 'Magic Fruit' in ctx(c,'magic-fruit')['action'] and 'missing HP' in ctx(c,'magic-fruit')['action']
 assert 'Physical and magical portions distinct' in rev(c,'red-lotus-blade')['rationale']
def test_original_conflicts_sparse_cells_and_manual_evidence():
 o=read('gear-guide-t7-blu-observations.json');rows=o['table_observations'];assert len(rows)==16 and len(o['guide_observations'])==4
 for r in rows+o['guide_observations']:assert digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256']
 by={r['item_set_id']:r for r in rows}
 assert by[386009]['grid']['legs']==['Luhlaza Shalwar +3','Hashishin Tayt +3']
 assert by[337111]['grid']['neck']==['Phalaina Locket','Nuna Gorget +1']
 assert by[386024]['grid']['ring2']==['Stikini Ring +1','Stikini Ring +1'] and by[386024]['grid']['ear1']==['Hashi. Earring +2']
 assert by[385973]['grid']['main']==['Thibron'] and by[385973]['grid']['sub']==['Naegling']
 assert 'main' in by[250766]['omitted_slots'] and len(by[250766]['grid'])==16
 cards=read('gear-guide-t7-blu-item-evidence.json')['items'];assert len(cards)==42
 assert all(r['independent_public_card_verified'] and digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256'] for r in cards)
 d=read('gear-guide-t7-blu-definitions.json');assert len(d['coverage_reconciliation'])==11 and any('White Wind' in r for r in d['unclaimed'])
