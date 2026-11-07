"""SAM source conflicts, strict augments, action access, and history boundaries."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import pytest
from vanadiel_nexus.core.equipment_hands import EVIDENCE, hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS, requirements_match, allocate_requirements
from vanadiel_nexus.core.guide_catalog import validate_catalog, composition_diagnostics
from vanadiel_nexus.core.item_res import Item

F = Path(__file__).resolve().parents[2] / 'docs/catalog'
def read(name): return json.loads((F / name).read_text(encoding='utf-8'))
def digest(v): return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
@pytest.fixture
def batch():
    c=read('gear-guide-t7-candidate.json'); p=read('gear-guide-t7-resource-evidence.json')
    items={r['id']:Item(**r) for r in p['items']}
    return c,p,items,hand_types(items)
def revision(c,key): return next(r for r in c['revisions'] if r['set_id']=='nexus:sam:'+key)
def slots(c,key): return {s['slot']:s for s in revision(c,key)['slots']}
def context(c,key): return next(s['context'] for s in c['sets'] if s['id']=='nexus:sam:'+key)

def test_prior_immutable_records_amendments_and_withdrawals_survive(batch):
    c,p,items,hands=batch
    b=next(b for b in c['authoring_batches'] if b['id']=='sam-2026-11-04')
    assert {k:len(v) for k,v in b['baseline_record_hashes'].items()}=={'sets':194,'revisions':205,'sources':345}
    for field,history in b['baseline_record_hashes'].items():
        now={r['id']:r for r in c[field]}
        assert all(digest(now[k])==v for k,v in history.items())
    retired={a['retired_revision_id'] for batch in c['authoring_amendments'] for a in batch['amendments']}
    assert len(retired)==27
    assert sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
    assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
    assert len(p['items'])==863
    validate_catalog(c,items=items,hand_types=hands)

@pytest.mark.parametrize('item_id,kind',[(21956,'two_handed'),(21025,'two_handed'),(21883,'two_handed'),(22212,'grip')])
def test_exact_hand_classification_and_same_name_stage_do_not_expand(batch,item_id,kind):
    c,p,items,hands=batch
    assert len(EVIDENCE)==55 and hands[item_id]==kind
    bad=deepcopy(items); bad[item_id]=Item(**{**asdict(items[item_id]),'skill':99})
    assert item_id not in hand_types(bad)
    chosen=slots(c,'leg-sweep' if item_id==21883 else 'fudo')
    chosen['main' if item_id!=22212 else 'sub']['item_id']=item_id
    assert composition_diagnostics(list(chosen.values()),bad,['SAM'],hand_types=hand_types(bad))
    assert 19406 not in hands

@pytest.mark.parametrize('key,parts',[
 ('engaged-balanced',['DEX+20','Accuracy+20 Attack+20','DEX+10','"Dbl.Atk."+10','Damage taken-5%']),
 ('fudo',['STR+20','Accuracy+20 Attack+20','STR+10','Weapon skill damage +10%','Damage taken-5%']),
 ('jinpu',['STR+20','Mag. Acc+20 /Mag. Dmg.+20','STR+10','Weapon skill damage +10%','Damage taken-5%']),
 ('engaged-dt',['Phys. dmg. taken-10%'])])
def test_independent_literal_cape_rolls_and_punctuation(batch,key,parts):
    c,_,_,_=batch; r=slots(c,key)['back']['requirements']
    assert requirements_match(r,{'augments':parts})
    assert not requirements_match(r,{'augments':parts[:-1]})
    collapsed=[x for x in parts if not x.startswith(('STR+','DEX+'))]+['STR+30','DEX+30']
    if len(parts)>1: assert not requirements_match(r,{'augments':collapsed})
    if key=='engaged-dt': assert not requirements_match(r,{'augments':['Phys. dmg. taken -10%']})

def test_ws_paths_moonshade_and_ability_overlays_are_distinct(batch):
    c,_,_,_=batch
    r=slots(c,'fudo')
    assert all(r[s]['requirements']=={'path':'B'} for s in ('head','body','hands','legs','feet'))
    assert requirements_match(r['ear2']['requirements'],{'augments':['Attack+4','TP Bonus +250']})
    assert not requirements_match(r['ear2']['requirements'],{'augments':['Attack+4','TP Bonus+250']})
    assert slots(c,'fudo-overflow')['ear2']['requirements']=={}
    assert slots(c,'fudo-overflow')['ear2']['name']=='Ishvara Earring'
    assert slots(c,'fudo-sekkanoki')['hands']['item_id']==23565
    assert slots(c,'fudo-meikyo')['feet']['item_id']==23677
    assert slots(c,'jinpu-sengikori')['feet']['item_id']==23699
    assert 'Hagakure active' in context(c,'fudo-hagakure')['ability']
    assert slots(c,'impulse-drive')['main']['item_id']==21883
    assert slots(c,'shoha')['main']['item_id']==21025
    assert 'Seigan active, Hasso inactive' in context(c,'third-eye')['ability']

def test_utility_accuracy_is_separate_from_damage_and_pet_bonuses(batch):
    c,_,_,_=batch
    assert slots(c,'leg-sweep')['main']['item_id']==21883
    assert slots(c,'ageha')['main']['item_id']==21956
    assert slots(c,'leg-sweep')['ammo']['name']=='Pemphredo Tathlum'
    assert slots(c,'ageha')['ear1']['name']=='Digni. Earring'
    assert slots(c,'ageha')['ear2']['item_id']==25488
    assert all(s.get('item_id') not in (26120,26234) for s in slots(c,'ageha').values())
    assert 'no master macc inferred from pet text' in revision(c,'ageha')['rationale']
    for r in c['revisions']:
        if not r['set_id'].startswith('nexus:sam:'): continue
        assert {s['slot'] for s in r['slots']}==set(SLOTS)
        assert all('rank' not in s.get('requirements',{}) for s in r['slots'])
        assert next(s for s in r['slots'] if s['slot']=='range')['state']=='empty'

def test_refresh_requires_two_copies_and_mp_context_not_regen(batch):
    c,_,_,_=batch; s=slots(c,'refresh-idle')
    assert 'SAM/WHM99/49 with useful MP pool' in context(c,'refresh-idle')['subjob']
    pair=[s['ring1'],s['ring2']]
    assert all(x['item_id']==26184 for x in pair)
    assert sum(x['owned'] for x in allocate_requirements(pair,[dict(character_key='fictional',item_id=26184,bag_id=8)],'fictional').values())==1
    assert 'Regen319759 is not Refresh' in revision(c,'refresh-idle')['rationale']
    assert s['main']['item_id']==slots(c,'engaged-balanced')['main']['item_id']==21956

def test_source_conflicts_duplicates_omissions_and_observation_digests():
    p=read('gear-guide-t7-sam-observations.json'); rows=p['table_observations']
    assert len(rows)==29
    for r in rows+p['guide_observations']:
        assert digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256']
    bytitle={r['title']:r for r in rows}
    regen=bytitle['319759 Regen conflicts']['ordered_macro_entries']
    assert [r['name'] for r in regen if r['slot']=='feet']==['Danzo Sune-Ate','Rao Sune-Ate +1']
    assert len([r for r in regen if r['slot']=='body' and r['name']=='Sacro Breastplate'])==2
    assert bytitle['365416 PDT']['grid']['hands']=='Nyame Gauntlets'
    assert 'conflicts' in bytitle['365416 PDT']['notes']
    assert [r['name'] for r in bytitle['365423 High Acc TP']['ordered_hand_entries']]==['Wakido Kote +3','Ken. Tekko +1']
    assert bytitle['365422 Mid Acc TP']['occupied_slot_count']==12
    assert all(bytitle[str(n)+' empty linked WS']['occupied_slot_count']==0 for n in (337750,353089,353090))
    assert '19406' in bytitle['403330 SAM2026']['notes']
    assert bytitle['Reidden Ageha 2026-09-10 13:49']['grid']['ring1']=='Murky Ring'
    assert all('not raw HTML' in r['representation'] for r in rows)

def test_all_sam_rows_reconciled_only_in_bounded_contexts(batch):
    c,_,_,_=batch; rows=[r for r in c['coverage'] if r['job']=='SAM']
    assert len(rows)==8 and all(r['status']=='included' and r['set_ids'] for r in rows)
    assert len([r for r in c['revisions'] if r['set_id'].startswith('nexus:sam:')])==28
    assert len([r for r in c['coverage'] if r['status']=='included'])==231
    gaps=[r for r in c['coverage'] if r['status']=='gap']
    assert len(gaps)==0 and len({r['job'] for r in gaps})==0
    assert not any(r['status']=='not_applicable' for r in c['coverage'])
