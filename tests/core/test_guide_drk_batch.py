"""DRK history, weapon-family legality, conditional magic and source conflicts."""
from copy import deepcopy
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
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json');items={r['id']:Item(**r) for r in p['items']}
 return c,p,items,hand_types(items)
def rev(c,k):return next(r for r in c['revisions'] if r['set_id']=='nexus:drk:'+k)
def slots(c,k):return {s['slot']:s for s in rev(c,k)['slots']}
def ctx(c,k):return next(s['context'] for s in c['sets'] if s['id']=='nexus:drk:'+k)
def test_prior_history_amendments_and_deferred_scope(batch):
 c,_,items,hands=batch;b=next(b for b in c['authoring_batches'] if b['id']=='drk-2026-11-04')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':359,'revisions':370,'sources':754}
 for f,h in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in h.items())
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert len([r for r in c['coverage'] if r['job']=='DRG' and r['status']=='included'])==8
 assert 'all22jobs' in c['delivery_status'];validate_catalog(c,items=items,hand_types=hands)
@pytest.mark.parametrize('key',[d['key'] for d in read('gear-guide-t7-drk-definitions.json')['definitions']])
def test_legal_weapon_family_unknown_classification_fails_closed(batch,key):
 c,_,items,hands=batch;r=rev(c,key);s=slots(c,key);i=s['main']['item_id']
 assert len(r['slots'])==16 and s['range']=={'slot':'range','state':'empty'}
 assert i in (20890,21689) and s['sub']['item_id']==22212 and hands[i]=='two_handed'
 assert not composition_diagnostics(r['slots'],items,['DRK'],hand_types=hands,context=ctx(c,key))
 broken=dict(items);broken[i]=replace(items[i],skill=12)
 assert i not in hand_types(broken)
 assert composition_diagnostics(r['slots'],broken,['DRK'],hand_types=hand_types(broken),context=ctx(c,key))
 assert r['currency']=='unknown' and 'current/maxHP' in ctx(c,key)['transitions']
def test_literal_source_omissions_conflicts_not_silent_repairs(batch):
 c,_,_,_=batch;o=read('gear-guide-t7-drk-observations.json');by={r['key']:r for r in o['table_observations']}
 assert by['fc3']['grid']['waist']==[] and by['fc3']['grid']['main']==[]
 assert by['entropy3']['grid']['legs']==['Ratri Cuisses +1'] and 'Leggings' in by['entropy3']['source_options']['legs']
 assert 'MIXED STR20,INT10,WSD10' in by['entropy3']['source_options']['back']
 assert slots(c,'entropy')['back']['requirements']['augments']==['INT+20','Accuracy+20 Attack+20','INT+10','"Dbl.Atk."+10','Damage taken-5%']
 assert by['dread3']['grid']['main']==['Crepuscular Scythe'] and slots(c,'dread-spikes-scythe')['main']['item_id']==20890
 assert any('unfinished' in f for f in o['guide_observations'][0]['findings'])
def test_action_access_target_phase_and_hp_constraints(batch):
 c,_,_,_=batch
 assert 'Permanently unlocked Torcleaver' in ctx(c,'torcleaver')['action']
 assert 'merit-unlocked Resolution' in ctx(c,'resolution')['action']
 assert 'granted by exact equipped Anguta' in ctx(c,'entropy')['action']
 assert 'missingHP' in ctx(c,'drain-recovery-scythe')['action']
 assert 'gift-unlocked DrainIII' in ctx(c,'drain-iii-dsnv-scythe')['action'] and 'active DarkSeal' in ctx(c,'drain-iii-dsnv-scythe')['action']
 assert 'completion retains legs' in next(r for r in read('gear-guide-t7-drk-item-evidence.json')['items'] if r['item_id']==23628)['conditional']
 assert 'target must have drainableMP' in ctx(c,'aspir-scythe')['action']
 assert 'target must have usableTP' in ctx(c,'absorb-tp-scythe')['action'] and slots(c,'absorb-tp-scythe')['hands']['item_id']==23561
 assert 'initiation only' in ctx(c,'precast-scythe')['action']
 assert 'casting maxHP' in ctx(c,'dread-spikes-scythe')['action'] and 'not a third spell' in rev(c,'dread-spikes-scythe')['rationale']
 assert slots(c,'weapon-bash-scythe')['hands']['item_id']==23516
 assert slots(c,'last-resort-scythe')['feet']['item_id']==23673
@pytest.mark.parametrize('key,name',[('refresh-idle-scythe','Stikini Ring +1'),('endark-ii-scythe','Stikini Ring +1'),('engaged-accuracy-greatsword','Chirich Ring +1')])
def test_two_rings_require_two_physical_copies(batch,key,name):
 c,_,_,_=batch;req=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(req)==2
 def allocate(n):return allocate_requirements(req,[dict(item_id=req[0]['item_id'],character_key='fictional',count=n)],'fictional')
 assert sum(r['owned'] for r in allocate(1).values())==1 and sum(r['owned'] for r in allocate(2).values())==2
def test_independent_cape_parts_and_native_punctuation(batch):
 c,_,_,_=batch;r=slots(c,'torcleaver')['back']['requirements']
 assert requirements_match(r,{'augments':['VIT+20','Accuracy+20 Attack+20','VIT+10','Weapon skill damage +10%','Damage taken-5%']})
 for a in [['VIT+30','Accuracy+20 Attack+20','Weapon skill damage +10%','Damage taken-5%'],['VIT+20','VIT+20','Accuracy+20 Attack+20','Weapon skill damage +10%','Damage taken-5%'],['VIT+20','VIT+10','Accuracy+20','Attack+20','Weapon skill damage +10%','Damage taken-5%']]:assert not requirements_match(r,{'augments':a})
 assert not requirements_match(slots(c,'precast-scythe')['back']['requirements'],{'augments':['HP+60','Fast Cast+10']})
 assert not requirements_match(slots(c,'cross-reaper')['ear2']['requirements'],{'augments':['Attack+4','TP Bonus+250']})
 assert slots(c,'cross-reaper')['head']['requirements']=={'path':'B'}
def test_evidence_hashes_attribution_and_bounded_coverage(batch):
 c,p,_,_=batch;o=read('gear-guide-t7-drk-observations.json');cards=read('gear-guide-t7-drk-item-evidence.json')['items']
 assert len(o['table_observations'])==13 and len(o['guide_observations'])==3 and len(cards)==35
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert 'oldid=770942' in o['guide_observations'][0]['url']
 assert all(r['independent_public_card_verified'] and any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources']) for r in cards)
 rows=[r for r in c['coverage'] if r['job']=='DRK'];assert len(rows)==8 and all(r['status']=='included' and r['set_ids'] for r in rows)
 assert len([r for r in c['revisions'] if r['set_id'].startswith('nexus:drk:')])==38
 assert len(p['items'])==863 and len(EVIDENCE)==55
 assert not any(s.get('item_id')==28624 for r in c['revisions'] if r['set_id'].startswith('nexus:drk:') for s in r['slots'])
 assert slots(c,'drain-recovery-scythe')['back']['item_id']==15471
