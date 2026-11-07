"""RNG stage/ammo/augment and source-boundary checks; detached public data only."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
import pytest
from vanadiel_nexus.core.equipment_hands import EVIDENCE,hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS,requirements_match,allocate_requirements
from vanadiel_nexus.core.guide_catalog import validate_catalog,composition_diagnostics
from vanadiel_nexus.core.item_res import Item
F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(name):return json.loads((F/name).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
@pytest.fixture
def batch():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json')
 items={r['id']:Item(**r) for r in p['items']}
 return c,p,items,hand_types(items)
def revision(c,key):return next(r for r in c['revisions'] if r['set_id']=='nexus:rng:'+key)
def slots(c,key):return {s['slot']:s for s in revision(c,key)['slots']}
def context(c,key):return next(s['context'] for s in c['sets'] if s['id']=='nexus:rng:'+key)

def test_rng_retains_all_prior_records_and_brd_withdrawals(batch):
 c,p,items,hands=batch
 history=next(b for b in c['authoring_batches'] if b['id']=='rng-2026-11-04')['baseline_record_hashes']
 assert {k:len(v) for k,v in history.items()}=={'sets':164,'revisions':175,'sources':278}
 for field in history:
  current={r['id']:r for r in c[field]}
  assert all(digest(current[k])==v for k,v in history[field].items())
 validate_catalog(c,items=items,hand_types=hands)
 retired={a['retired_revision_id'] for batch in c['authoring_amendments'] for a in batch['amendments']}
 assert len(retired)==27
 assert sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert len([r for r in c['revisions'] if r['set_id'].startswith('nexus:rng:')])==30
 assert len(p['items'])==863

@pytest.mark.parametrize('key,weapon,ammo',[('ranged-tp',21485,21296),('trueflight',21266,21311),
 ('wildfire',21269,21325),('coronach',21267,21296),('jishnu',22116,21297),('namas',22115,21297),('apex-arrow',22117,21297)])
def test_exact_base_stage_and_compatible_expendable_ammo(batch,key,weapon,ammo):
 c,p,items,_=batch;r=slots(c,key)
 assert r['range']['item_id']==weapon and r['ammo']['item_id']==ammo
 assert r['range']['requirements']==r['ammo']['requirements']=={}
 assert 'Dispense:' in p['descriptions'][str(weapon)]
 assert items[weapon].slots==4 and items[ammo].slots==8
 assert 'no rank-derived' in context(c,key)['weapon_access']
 assert 'expendable' in context(c,key)['ammo_safety']

def test_same_skill_is_not_proof_of_bullet_bolt_compatibility(batch):
 c,_,items,_=batch
 # Both crossbow and gun are skill26. This independently reviewed family map is
 # a batch oracle, not a new runtime classifier or claim the service enforces it.
 weapon_ammo={21266:{21311},21485:{21296},21267:{21296},21269:{21325},22115:{21297},22116:{21297},22117:{21297}}
 assert items[21266].skill==items[21485].skill==26
 assert 21296 not in weapon_ammo[21266] and 21311 not in weapon_ammo[21485]
 for r in c['revisions']:
  if not r['set_id'].startswith('nexus:rng:'):continue
  s={x['slot']:x for x in r['slots']}
  if s['ammo']['state']=='selected':assert s['ammo']['item_id'] in weapon_ammo[s['range']['item_id']]

def test_six_preshot_states_are_distinct_and_taeon_has_two_rolls(batch):
 c,_,_,_=batch
 heads=[slots(c,'preshot-standard-f'+str(f))['head']['item_id'] for f in range(3)]
 assert heads==[26735,23385,23385]
 req=slots(c,'preshot-standard-f0')['head']['requirements']
 assert requirements_match(req,{'augments':['"Snapshot"+5','"Snapshot"+5']})
 assert not requirements_match(req,{'augments':['"Snapshot"+5']})
 assert not requirements_match(req,{'augments':['"Snapshot"+10']})
 assert slots(c,'preshot-gastraphetes-f2')['legs']['requirements']=={'path':'A'}
 assert slots(c,'preshot-standard-f1')['legs']['requirements']=={'path':'D'}
 for family in ('standard','gastraphetes'):
  for f,buff in enumerate(('No Flurry','Flurry I active','Flurry II active')):
   key=f'preshot-{family}-f{f}'
   assert context(c,key)['buff']==buff
   assert 'No Snapshot/Rapid Shot cap' in revision(c,key)['rationale']
   assert slots(c,key)['neck']['requirements']=={}

@pytest.mark.parametrize('key,parts',[
 ('ranged-tp',['AGI+20','Rng.Acc.+20 Rng.Atk.+20','AGI+10','"Store TP"+10']),
 ('critical-armageddon',['AGI+20','Rng.Acc.+20 Rng.Atk.+20','AGI+10','Crit.hit rate+10']),
 ('trueflight',['AGI+20','Mag. Acc+20 /Mag. Dmg.+20','AGI+10','Weapon skill damage +10%']),
 ('jishnu',['DEX+20','Rng.Acc.+20 Rng.Atk.+20','DEX+10','Crit.hit rate+10']),
 ('savage-blade',['STR+20','Accuracy+20 Attack+20','STR+10','Weapon skill damage +10%','Damage taken-5%'])])
def test_independent_literal_decoded_cape_copies(batch,key,parts):
 c,_,_,_=batch;req=slots(c,key)['back']['requirements']
 assert requirements_match(req,{'augments':parts})
 assert not requirements_match(req,{'augments':parts[:-1]})
 stat=parts[0].split('+')[0]
 assert not requirements_match(req,{'augments':[stat+'+30']+[p for p in parts if not p.startswith(stat+'+')]})

def test_abilities_aftermath_access_and_right_ear_are_explicit(batch):
 c,_,items,_=batch
 for key in ('double-shot','critical-double-shot'):
  assert 'Double Shot active' in context(c,key)['ability']
  assert 'Superior 3' in context(c,key)['access']
  assert slots(c,key)['body']['item_id']==23475
 assert slots(c,'ranged-tp')['body']['item_id']==23762
 for key in ('critical-armageddon','critical-gandiva','critical-gastraphetes'):
  assert 'AM3 active' in context(c,key)['aftermath']
 for r in c['revisions']:
  if not r['set_id'].startswith('nexus:rng:'):continue
  for s in r['slots']:
   if s.get('item_id')==25482:assert s['slot']=='ear2' and s['requirements']=={}
   if s.get('item_id') in (25977,25890,25957):assert items[s['item_id']].superior_level==3
   assert s.get('item_id') not in (22293,19607) # No rare Hauksbok/stat-ammo shooting targets.

def test_three_new_exact_hand_records_fail_closed_and_no_dual_wield(batch):
 c,p,items,hands=batch
 assert len(EVIDENCE)==55 and [r.item_id for r in EVIDENCE[19:22]]==[20805,20595,26421]
 assert hands[20805]==hands[20595]=='one_handed' and hands[26421]=='shield'
 bad=deepcopy(items);bad[20805]=Item(**{**next(r for r in p['items'] if r['id']==20805),'skill':8})
 assert 20805 not in hand_types(bad)
 r=slots(c,'ranged-tp');r['main']['item_id']=20805
 assert composition_diagnostics(list(r.values()),bad,['RNG'],hand_types=hand_types(bad))
 for r in c['revisions']:
  if r['set_id'].startswith('nexus:rng:'):
   s={x['slot']:x for x in r['slots']};assert s['sub']['item_id']==26421
   assert {x['slot'] for x in r['slots']}==set(SLOTS)

def test_source_omissions_conflicts_and_options_survive():
 packet=read('gear-guide-t7-rng-observations.json');rows=packet['table_observations']
 assert len(rows)==35
 for row in rows+packet['guide_observations']:
  assert digest({k:v for k,v in row.items() if k!='observation_sha256'})==row['observation_sha256']
 for row in rows[:6]:
  assert row['occupied_slot_count']==9 and row['grid']['range'] is None
  assert len(row['omitted_slots'])==7 and 'not raw HTML' in row['representation']
 assert rows[9]['occupied_slot_count']==7 and rows[11]['occupied_slot_count']==6 and rows[13]['occupied_slot_count']==4
 assert rows[13]['notes'].find('R15+')>=0
 assert '30 STR/WSD' in rows[26]['notes'] and '30 DEX/Crit' in rows[27]['notes']
 assert rows[22]['grid']['head'] is None and 'Cohort' in rows[22]['grid']['body']
 assert 'conditional' in rows[23]['notes'].lower()
 assert 'Sparrowhawk' in rows[32]['grid']['range']
 cards=read('gear-guide-t7-rng-item-evidence.json')['items'];assert len(cards)==57
 assert all('not retained raw HTML' in r['scope'] for r in cards)

def test_idle_and_supported_melee_copy_and_transition_limits(batch):
 c,_,_,_=batch
 for key in ('melee-balanced','melee-dt','melee-accuracy','savage-blade','dt-idle','refresh-idle'):
  assert slots(c,key)['ammo']['state']=='empty'
 assert 'Velocity Shot off' in context(c,'melee-balanced')['stance']
 assert 'MP pool' in context(c,'refresh-idle')['subjob']
 pair=[slots(c,'refresh-idle')[s] for s in ('ring1','ring2')]
 assert pair[0]['item_id']==pair[1]['item_id']==26184
 assert sum(r['owned'] for r in allocate_requirements(pair,[dict(character_key='fictional',item_id=26184,bag_id=8)],'fictional').values())==1
 assert slots(c,'savage-blade')['range']['item_id']==21485
 assert 'No TP bonus credited' in revision(c,'savage-blade')['rationale']
 assert 'No Tonberry Grudge critical amount' in context(c,'critical-armageddon')['conditions']

def test_all_ten_rng_obligations_reconciled_without_all_job_completion(batch):
 c,_,_,_=batch;rows=[r for r in c['coverage'] if r['job']=='RNG']
 assert len(rows)==10 and all(r['status']=='included' and r['set_ids'] for r in rows)
 gaps=[r for r in c['coverage'] if r['status']=='gap']
 assert len(gaps)==0 and len({r['job'] for r in gaps})==0
 assert sum(r['status']=='included' for r in c['coverage'])==231
 assert not any(r['status']=='not_applicable' for r in c['coverage'])
