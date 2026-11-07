"""COR scoped actions, native literal copies, hands/ammo and immutable history."""
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
def rev(c,key):return next(r for r in c['revisions'] if r['set_id']=='nexus:cor:'+key)
def slots(c,key):return {s['slot']:s for s in rev(c,key)['slots']}
def ctx(c,key):return next(s['context'] for s in c['sets'] if s['id']=='nexus:cor:'+key)
KEYS=['dt-idle','refresh-idle','engaged-balanced','engaged-dt','engaged-accuracy','ranged-normal','ranged-accuracy','ranged-triple-shot','last-stand','savage-blade','evisceration','leaden-salute','wildfire','hot-shot','aeolian-edge','roll-initial','roll-double-up','quick-draw-damage','quick-draw-elemental-window','light-shot','dark-shot','quick-draw-tp','preshot-no-flurry','preshot-flurry1','preshot-flurry2','random-deal','fold','snake-eye','wild-card']
def test_append_only_histories_and_deferred_brd_drg(batch):
 c,p,items,hands=batch;b=next(b for b in c['authoring_batches'] if b['id']=='cor-2026-11-04')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':283,'revisions':294,'sources':570}
 for f,history in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in history.items())
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 assert [len(c[f]) for f in ('sets','revisions','sources','coverage')]==[520,547,1331,231] and len(p['items'])==863
 drg=[r for r in c['coverage'] if r['job']=='DRG'];assert len(drg)==8 and all(r['status']=='included' for r in drg)
 rows=[r for r in c['coverage'] if r['job']=='COR'];assert len(rows)==11 and all(r['status']=='included' and r['set_ids'] for r in rows)
 assert sum(r['status']=='gap' for r in c['coverage'])==0 and not any(r['status']=='not_applicable' for r in c['coverage'])
 validate_catalog(c,items=items,hand_types=hands)
@pytest.mark.parametrize('key',KEYS)
def test_all_compositions_exact_hands_subjob_ammo_and_slot_states(batch,key):
 c,_,items,hands=batch;r=rev(c,key);context=ctx(c,key);s=slots(c,key)
 assert {x['slot'] for x in r['slots']}==set(SLOTS) and len(r['slots'])==16
 assert not composition_diagnostics(r['slots'],items,['COR'],hand_types=hands,context=context)
 if context['dual_wield']:
  assert context['job']=='COR99/NIN49' and 'NIN45' in context['trait']
  assert composition_diagnostics(r['slots'],items,['COR'],hand_types=hands,context={**context,'dual_wield':False})
 else:assert s['sub']['item_id']==26421
 if key.startswith('roll-'):
  assert s['range']['item_id']==21482 and s['ammo']=={'slot':'ammo','state':'empty'}
 else:assert s['range']['item_id']==21485 and s['ammo']['item_id']==21296
 assert r['origin']=='nexus_recommendation' and r['currency']=='unknown'
 assert not any('rank' in x.get('requirements',{}) for x in r['slots'])
def test_tauret_exact_hand_classification_fails_closed(batch):
 c,_,items,hands=batch;assert len(EVIDENCE)==55 and EVIDENCE[33].item_id==21565 and hands[21565]=='one_handed'
 changed=deepcopy(items);changed[21565]=replace(items[21565],skill=12)
 assert 21565 not in hand_types(changed)
 assert composition_diagnostics(rev(c,'evisceration')['slots'],changed,['COR'],hand_types=hand_types(changed),context={'dual_wield':True})
@pytest.mark.parametrize('key,slot,copy',[
 ('ranged-normal','back',{'augments':['AGI+20','Rng.Acc.+20 Rng.Atk.+20','AGI+10','"Store TP"+10','Damage taken-5%']}),
 ('engaged-balanced','back',{'augments':['DEX+20','Accuracy+20 Attack+20','DEX+10','"Dbl.Atk."+10','Damage taken-5%']}),
 ('savage-blade','back',{'augments':['STR+20','Accuracy+20 Attack+20','STR+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('leaden-salute','back',{'augments':['AGI+20','Mag. Acc+20 /Mag. Dmg.+20','AGI+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('last-stand','back',{'augments':['AGI+20','Rng.Acc.+20 Rng.Atk.+20','AGI+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('aeolian-edge','back',{'augments':['INT+20','Mag. Acc+20 /Mag. Dmg.+20','INT+10','Weapon skill damage +10%','Damage taken-5%']}),
 ('evisceration','back',{'augments':['DEX+20','Accuracy+20 Attack+20','DEX+10','Crit.hit rate+10','Damage taken-5%']}),
 ('quick-draw-damage','back',{'augments':['AGI+20','Mag. Acc+20 /Mag. Dmg.+20','AGI+10','"Mag.Atk.Bns."+10','Damage taken-5%']}),
 ('preshot-no-flurry','back',{'augments':['"Snapshot"+10']}),
 ('savage-blade','ear1',{'augments':['Attack+4','TP Bonus +250']}),
 ('savage-blade','body',{'path':'B'})])
def test_independent_literal_decoded_copy_matching(batch,key,slot,copy):
 r=slots(batch[0],key)[slot]['requirements'];assert requirements_match(r,copy) and not requirements_match(r,{})
 bad=deepcopy(copy)
 if 'augments' in bad:bad['augments']=bad['augments'][:-1]
 else:bad['path']='A'
 assert not requirements_match(r,bad)
@pytest.mark.parametrize('key,item_id',[('refresh-idle',26184),('engaged-accuracy',26182),('ranged-accuracy',26182)])
def test_duplicate_selected_items_need_distinct_physical_copies(batch,key,item_id):
 c,_,items,_=batch;requirements=[s for s in rev(c,key)['slots'] if s.get('item_id')==item_id];assert len(requirements)==2
 one=allocate_requirements(requirements,[dict(item_id=item_id,character_key='fictional',count=1)],'fictional')
 two=allocate_requirements(requirements,[dict(item_id=item_id,character_key='fictional',count=2)],'fictional')
 assert sum(r['owned'] for r in one.values())==1 and sum(r['owned'] for r in two.values())==2

def test_roll_qd_shot_and_weapon_contexts_remain_distinct(batch):
 c,_,_,_=batch
 assert slots(c,'savage-blade')['main']['item_id']==21621 and slots(c,'savage-blade')['sub']['item_id']==21565
 assert slots(c,'evisceration')['main']['item_id']==21565
 assert 'ranged-WS-only' in rev(c,'savage-blade')['rationale'] and 'not consumed' not in ctx(c,'ranged-normal')['ammo']
 assert 'Actually active Triple Shot' in ctx(c,'ranged-triple-shot')['triple_shot'] and 'Does not apply to WS' in ctx(c,'last-stand')['triple_shot']
 assert [ctx(c,k)['flurry'] for k in ('preshot-no-flurry','preshot-flurry1','preshot-flurry2')]==['None','Flurry I actually active from external caster, not FlurryII','Flurry II actually active from external caster, not cumulative with FlurryI']
 assert slots(c,'quick-draw-elemental-window')['feet']['item_id']==23704 and slots(c,'quick-draw-damage')['feet']['item_id']==23682
 assert 'light sleep' in ctx(c,'light-shot')['action'] and 'removable buff' in ctx(c,'dark-shot')['action']
 assert ctx(c,'refresh-idle')['job']=='COR99/WHM49' and 'Sphere' in rev(c,'refresh-idle')['rationale']
 assert 'only highest' in ctx(c,'roll-initial')['roll_effects'] and 'Double-Up window' in ctx(c,'roll-double-up')['action']

def test_observation_conflicts_and_unresolved_refresh_survive(batch):
 c,_,_,_=batch;o=read('gear-guide-t7-cor-observations.json');by={r['item_set_id']:r for r in o['table_observations']}
 assert len(by)==19 and len(o['guide_observations'])==9
 assert by[356928]['grid']['main']==["Gleti's Knife"] and by[356928]['grid']['sub']==['Naegling']
 assert by[357009]['grid']['ear1']==['Chas. Earring +2'] and by[357137]['grid']['range']==['Earp']
 assert len(by[357015]['omitted_slots'])==11 and by[357015]['grid']['ring1']==by[357015]['grid']['ring2']==['Stikini Ring +1']
 assert next(r for r in c['revisions'] if r['set_id']=='ffxiah:357015:cor')['verification']['status']=='unresolved'
 assert any('guide10sec' in f['notes'] and 'BG25sec' in f['notes'] for f in o['guide_observations'])
 assert any('Guide lists1min' in f['notes'] for f in o['guide_observations'])
 assert all(digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256'] for r in o['table_observations']+o['guide_observations'])

def test_exact_card_evidence_and_no_invented_tiers(batch):
 c,p,_,_=batch;cards=read('gear-guide-t7-cor-item-evidence.json')['items'];assert len(cards)==31
 assert all(r['independent_public_card_verified'] and digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256'] for r in cards)
 assert all(hashlib.sha256(p['descriptions'][str(r['item_id'])].encode()).hexdigest()==r['resource_description_sha256'] for r in cards if r['item_id']!=22143)
 assert '22143' not in p['descriptions'] and all(s.get('item_id')!=22143 for k in KEYS for s in rev(c,k)['slots'])
 defs=read('gear-guide-t7-cor-definitions.json');assert len(defs['coverage_reconciliation'])==11 and len(defs['definitions'])==29 and len(defs['unclaimed'])==8
 assert all('Fixed base/explicit augment' in rev(c,k)['equipment_version'] for k in KEYS)
