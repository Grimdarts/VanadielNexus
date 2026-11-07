"""NIN source conflicts, declared DW contexts, copied rolls, and history gates."""
from copy import deepcopy
from dataclasses import asdict
import hashlib,json
from pathlib import Path
import pytest
from vanadiel_nexus.core.equipment_hands import EVIDENCE, hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS, requirements_match, allocate_requirements
from vanadiel_nexus.core.guide_catalog import validate_catalog, composition_diagnostics
from vanadiel_nexus.core.item_res import Item

F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(n):return json.loads((F/n).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
@pytest.fixture
def batch():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json');items={r['id']:Item(**r) for r in p['items']}
 return c,p,items,hand_types(items)
def rev(c,key):return next(r for r in c['revisions'] if r['set_id']=='nexus:nin:'+key)
def slots(c,key):return {s['slot']:s for s in rev(c,key)['slots']}
def context(c,key):return next(s['context'] for s in c['sets'] if s['id']=='nexus:nin:'+key)

def test_prior_history_withdrawals_and_effective_counts(batch):
 c,p,items,hands=batch;b=next(b for b in c['authoring_batches'] if b['id']=='nin-2026-11-04')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':222,'revisions':233,'sources':396}
 for f,history in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in history.items())
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27
 assert sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 assert [len(c[f]) for f in ('sets','revisions','sources')]==[520,547,1331]
 assert len(p['items'])==863
 validate_catalog(c,items=items,hand_types=hands)

@pytest.mark.parametrize('item_id', [20977,21922,21925])
def test_exact_katana_hand_evidence_fails_closed_when_resource_changes(batch,item_id):
 c,p,items,hands=batch
 assert len(EVIDENCE)==55 and hands[item_id]=='one_handed'
 changed=deepcopy(items);changed[item_id]=Item(**{**asdict(items[item_id]),'skill':10})
 assert item_id not in hand_types(changed)
 key='ku' if item_id==21922 else 'ten'
 assert composition_diagnostics(list(slots(c,key).values()),changed,['NIN'],hand_types=hand_types(changed),context=context(c,key))

def test_native_dual_wield_is_required_beyond_job_string(batch):
 c,p,items,hands=batch;s=list(slots(c,'ten').values());ctx=context(c,'ten')
 assert ctx['dual_wield'] is True and 'native' in ctx['dual_wield_evidence']
 assert not composition_diagnostics(s,items,['NIN'],hand_types=hands,context=ctx)
 missing=deepcopy(ctx);missing.pop('dual_wield')
 assert composition_diagnostics(s,items,['NIN'],hand_types=hands,context=missing)
 missing['dual_wield']=False
 assert composition_diagnostics(s,items,['NIN'],hand_types=hands,context=missing)
 assert 21925 in hands and len([s for s in slots(c,'ten').values() if s.get('item_id')==21925])==1

@pytest.mark.parametrize('key,copy',[
 ('engaged-dt',{'augments':['DEX+20','Accuracy+20 Attack+20','DEX+10','"Dbl.Atk."+10','Damage taken-5%']}),
 ('engaged-balanced-low',{'augments':['DEX+20','Accuracy+20 Attack+20','DEX+10','"Dual Wield"+10','Damage taken-5%']}),
 ('ten',{'augments':['STR+20','Accuracy+20 Attack+20','STR+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('chi',{'augments':['STR+20','Mag. Acc+20 /Mag. Dmg.+20','STR+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('jin',{'augments':['DEX+20','Accuracy+20 Attack+20','DEX+10','Crit.hit rate+10','Damage taken-5%']}),
 ('ku',{'augments':['STR+20','Accuracy+20 Attack+20','STR+10','"Dbl.Atk."+10','Damage taken-5%']}),
 ('ninjutsu-potency',{'augments':['INT+20','Mag. Acc+20 /Mag. Dmg.+20','INT+10','"Mag.Atk.Bns."+10','Damage taken-5%']}),
 ('utsusemi-precast',{'augments':['"Fast Cast"+10']})])
def test_literal_fictional_cape_copy_is_independent_of_definition(batch,key,copy):
 r=slots(batch[0],key)['back']['requirements']
 assert requirements_match(r,copy)
 assert not requirements_match(r,{'augments':copy['augments'][:-1]})
 for stat in ('STR','DEX','INT'):
  if stat+'+20' in copy['augments']:
   assert not requirements_match(r,{'augments':[v for v in copy['augments'] if not v.startswith(stat+'+')]+[stat+'+30']})

def test_moonshade_copies_require_native_parts_in_every_selected_slot(batch):
 c,_,_,_=batch
 for r in c['revisions']:
  if not r['set_id'].startswith('nexus:nin:'):continue
  for s in r['slots']:
   if s.get('item_id')==11697:
    assert s['requirements']=={'augments':['Attack+4','TP Bonus +250']}
    assert requirements_match(s['requirements'],{'augments':['Attack+4','TP Bonus +250']})
    assert not requirements_match(s['requirements'],{'augments':['Attack+4','TP Bonus+250']})
 assert slots(c,'ten-overflow')['ear1']['name']=='Ishvara Earring'
 assert slots(c,'ten')['ear2']['item_id']==25493

def test_haste_support_and_stance_time_contexts_stay_separate(batch):
 c,_,_,_=batch
 for mode in ('balanced','dt','accuracy'):
  low=slots(c,'engaged-'+mode+'-low');high=slots(c,'engaged-'+mode)
  assert low['head']['item_id']==23432 and low['body']['item_id']==23477
  assert low['waist']['item_id']==26321 and low['back']['requirements']['augments'][3]=='"Dual Wield"+10'
  assert low['head']!=high['head']
  assert 'No magical or JA haste' in context(c,'engaged-'+mode+'-low')['buffs']
  assert 'Honor March and Haste' in context(c,'engaged-'+mode)['buffs']
 assert 'behind target; Yonin inactive' in context(c,'engaged-innin')['stance']
 assert 'in front of target; Innin inactive' in context(c,'engaged-yonin')['stance']
 assert 'elapsed ability time unknown' in context(c,'engaged-yonin')['stance']
 assert slots(c,'ten-night')['ear1']['item_id']==28482
 assert 'Dusk to dawn only' in context(c,'ten-night')['time']
 assert 'Evening to early morning only' in context(c,'night-movement')['time']

def test_ninjutsu_access_futae_and_burst_are_explicit_not_gear_inference(batch):
 c,_,_,_=batch
 for key in ('ninjutsu-potency','ninjutsu-futae','ninjutsu-burst','ninjutsu-burst-futae'):
  s=slots(c,key);assert (s['main']['item_id'],s['sub']['item_id'])==(21922,21925)
 assert slots(c,'ninjutsu-potency')['hands']['name']=='Nyame Gauntlets'
 assert slots(c,'ninjutsu-futae')['hands']['item_id']==23566
 assert slots(c,'ninjutsu-burst')['ring2']['name']=='Mujin Band'
 assert 'Futae inactive' in context(c,'ninjutsu-burst')['ability']
 assert 'Futae active' in context(c,'ninjutsu-burst-futae')['ability']
 assert 'skillchain' in context(c,'ninjutsu-burst')['action']
 assert slots(c,'enfeebling')['head']['item_id']==23907
 assert slots(c,'enfeebling')['back']['name']=='Null Shawl'

def test_precast_completion_and_migawari_remain_distinct(batch):
 c,_,_,_=batch;pre=slots(c,'utsusemi-precast');mid=slots(c,'utsusemi-midcast');utility=slots(c,'enhancing')
 assert pre['body']['item_id']==23477 and pre['neck']['item_id']==11627
 for key in ('head','legs'):
  assert requirements_match(pre[key]['requirements'],{'augments':['"Fast Cast"+6']})
  assert not requirements_match(pre[key]['requirements'],{'augments':['Fast Cast+6']})
 assert mid['hands']['item_id']==24020
 assert all(s['back']['item_id']==26258 and s['feet']['item_id']==23700 for s in (pre,mid,utility))
 assert utility['body']['item_id']==23499
 assert mid['body']['name']=='Nyame Mail'
 assert 'resolution' in context(c,'utsusemi-midcast')['timing']

@pytest.mark.parametrize('key',['refresh-idle','enfeebling','ninjutsu-accuracy'])
def test_two_stikini_slots_need_two_physical_copies(batch,key):
 c,_,_,_=batch;s=slots(c,key);pair=[s['ring1'],s['ring2']]
 assert all(r['item_id']==26184 for r in pair)
 copies=[dict(character_key='fictional',item_id=26184,bag_id=8)]
 assert sum(r['owned'] for r in allocate_requirements(pair,copies,'fictional').values())==1
 assert slots(c,'refresh-idle')['neck']['name']=='Loricate Torque +1'
 assert 'NIN/RUN99/49' in context(c,'refresh-idle')['subjob']

def test_every_nin_composition_is_explicit_without_invented_rank(batch):
 c,_,_,_=batch;rows=[r for r in c['revisions'] if r['set_id'].startswith('nexus:nin:')]
 assert len(rows)==30
 for r in rows:
  assert {s['slot'] for s in r['slots']}==set(SLOTS)
  s={x['slot']:x for x in r['slots']};assert s['range']['state']=='empty'
  assert all('rank' not in x.get('requirements',{}) for x in r['slots'])
  assert all(x.get('item_id') not in (21906,21907,21908,26120) for x in r['slots'])
  if s['ammo'].get('item_id')==21391:assert ':engaged-' in r['set_id']
  for x in r['slots']:
   if x.get('item_id')==25493:assert x['slot']=='ear2'
 assert slots(c,'ten')['body']['requirements']=={'path':'B'}
 assert slots(c,'ninjutsu-potency')['body']['requirements']=={}

def test_original_source_conflicts_omissions_model_and_digests_retained():
 p=read('gear-guide-t7-nin-observations.json');rows=p['table_observations']
 assert len(rows)==16
 for r in rows+p['guide_observations']:
  assert digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256']
 by={r['title']:r for r in rows}
 assert by['772448 Savage Hitaki conflict']['grid']['sub']=='Hitaki'
 assert 'contradicts' in by['772448 Savage Hitaki conflict']['notes']
 assert by['Finans Enfeebling']['omitted_slots']==['main','sub','range']
 assert by['Finans Enfeebling']['grid']['ring1']==by['Finans Enfeebling']['grid']['ring2']=='Stikini Ring +1'
 assert 'magnitudes' in by['772448 Shun mid']['notes']
 assert 'Nexus' in by['Finans Katana TP Full DT']['notes']
 assert any(r.get('currency')=='retired' for r in p['guide_observations'])
 assert 'not raw HTML' in rows[0]['representation']

def test_public_card_evidence_does_not_claim_html_hashes_or_unconditional_effects():
 p=read('gear-guide-t7-nin-item-evidence.json');cards=p['items']
 assert len(cards)==35
 for r in cards:assert digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256']
 by={r['item_id']:r for r in cards}
 assert 'Right ear only' in by[25493]['conditional']
 assert 'not credited' in by[25416]['conditional']
 assert 'Sange consumes' in by[21391]['conditional']
 assert 'Dusk to dawn' in by[28482]['conditional']

def test_all_actual_nin_rows_are_bounded_and_remaining_jobs_stay_gaps(batch):
 c,_,_,_=batch;rows=[r for r in c['coverage'] if r['job']=='NIN'];assert len(rows)==11
 assert all(r['status']=='included' and r['set_ids'] for r in rows)
 assert sum(r['status']=='included' for r in c['coverage'])==231
 gaps=[r for r in c['coverage'] if r['status']=='gap']
 assert len(gaps)==0 and len({r['job'] for r in gaps})==0
 assert not any(r['status']=='not_applicable' for r in c['coverage'])
