"""PLD resource legality, source conflicts, action scope and distinct-copy regressions."""
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
def rev(c,k):return next(r for r in c['revisions'] if r['set_id']=='nexus:pld:'+k)
def slots(c,k):return {s['slot']:s for s in rev(c,k)['slots']}
def ctx(c,k):return next(s['context'] for s in c['sets'] if s['id']=='nexus:pld:'+k)
def test_prior_history_and_deferred_all_job_review(batch):
 c,_,items,hands=batch;b=next(b for b in c['authoring_batches'] if b['id']=='pld-2026-11-04')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}=={'sets':332,'revisions':343,'sources':694}
 for f,h in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in h.items())
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 assert len([r for r in c['coverage'] if r['job']=='DRG' and r['status']=='included'])==8
 retired={a['retired_revision_id'] for b in c['authoring_amendments'] for a in b.get('amendments',[])}
 assert len(retired)==27 and retired<={r['id'] for r in c['revisions']}
 assert 'all22jobs' in c['delivery_status']
 validate_catalog(c,items=items,hand_types=hands)
@pytest.mark.parametrize('key',['dt-idle','town-refresh-idle','combat-refresh-idle','engaged-balanced','engaged-dt','engaged-accuracy','enmity-ja','flash-enmity','precast','sird-completion','self-phalanx','phalanx-received','self-phalanx-sird','cure-self','cure-other','majesty-cure','savage-blade','atonement','shield-bash','sentinel','cover','rampart','chivalry','divine-emblem','enlight-ii','reprisal','crusade'])
def test_fixed_hand_pair_legal_unknown_shield_fails_closed(batch,key):
 c,_,items,hands=batch;r=rev(c,key);s=slots(c,key)
 assert len(r['slots'])==16 and s['range']=={'slot':'range','state':'empty'}
 assert (s['main']['item_id'],s['sub']['item_id'])==(21621,28648)
 assert not composition_diagnostics(r['slots'],items,['PLD'],hand_types=hands,context=ctx(c,key))
 broken=deepcopy(items);broken[28648]=replace(items[28648],shield_size=6)
 assert 28648 not in hand_types(broken)
 assert composition_diagnostics(r['slots'],broken,['PLD'],hand_types=hand_types(broken),context=ctx(c,key))
 assert r['currency']=='unknown'
def test_source_stage_ear_and_stale_snapshot_conflicts_retained(batch):
 c,_,items,hands=batch;o=read('gear-guide-t7-pld-observations.json');by={r['item_set_id']:r for r in o['table_observations']}
 assert by[397521]['exact_source_hand_links']['sub']==26495 and by[397548]['exact_source_hand_links']['sub']==26493
 assert by[397921]['grid']['ear1']==['Chev. Earring +1']
 assert by[397522]['grid']['body']==['Rev. Surcoat +4'] and 'stale' in by[397522]['notes']
 assert all(s.get('item_id') not in (20687,26493,26495,25457) for r in c['revisions'] if r['set_id'].startswith('nexus:pld:') for s in r['slots'])
 assert hands[28648]=='shield' and next(e for e in EVIDENCE if e.item_id==28648).shield_size==3
def test_town_combat_and_actual_recovery_contexts_are_distinct(batch):
 c,_,_,_=batch
 assert 'Safe-town' in ctx(c,'town-refresh-idle')['action']
 assert 'exposed' in ctx(c,'combat-refresh-idle')['action']
 assert slots(c,'town-refresh-idle')['body']['item_id']==26972
 assert slots(c,'combat-refresh-idle')['body']['item_id']==23764
 assert 'no base Refresh' in next(x for x in read('gear-guide-t7-pld-item-evidence.json')['items'] if x['item_id']==26972)['conditional']
def test_action_recipient_unlock_and_phase_distinctions(batch):
 c,_,_,_=batch
 assert 'initiation only' in ctx(c,'precast')['action'] and 'completion' in ctx(c,'sird-completion')['action']
 assert 'caster and recipient' in ctx(c,'self-phalanx')['action'] and 'another actual caster' in ctx(c,'phalanx-received')['action']
 assert 'Majesty inactive' in ctx(c,'cure-other')['action'] and 'actually active Majesty' in ctx(c,'majesty-cure')['action']
 assert 'missingHP' in ctx(c,'cure-self')['action'] and 'usableTP consumed' in ctx(c,'chivalry')['action']
 assert 'Permanently unlocked' in ctx(c,'atonement')['action'] and 'merit-unlocked' in ctx(c,'enlight-ii')['action']
 assert slots(c,'cover')['head']['item_id']==23381 and slots(c,'cover')['body']['item_id']==23471
 assert slots(c,'shield-bash')['hands']['item_id']==23538
@pytest.mark.parametrize('key,name',[('town-refresh-idle','Stikini Ring +1'),('combat-refresh-idle','Stikini Ring +1'),('self-phalanx','Stikini Ring +1'),('engaged-accuracy','Chirich Ring +1')])
def test_double_rings_require_two_distinct_physical_copies(batch,key,name):
 c,_,_,_=batch;req=[s for s in rev(c,key)['slots'] if s.get('name')==name];assert len(req)==2
 def allocated(n):return allocate_requirements(req,[dict(item_id=req[0]['item_id'],character_key='fictional',count=n)],'fictional')
 assert sum(r['owned'] for r in allocated(1).values())==1 and sum(r['owned'] for r in allocated(2).values())==2
def test_literal_augments_do_not_accept_totals_or_wrong_punctuation(batch):
 c,_,_,_=batch;r=slots(c,'savage-blade')['back']['requirements']
 assert requirements_match(r,{'augments':['STR+20','Accuracy+20 Attack+20','STR+10','Weapon skill damage +10%','Damage taken-5%']})
 for a in [['STR+30','Accuracy+20 Attack+20','Weapon skill damage +10%','Damage taken-5%'],['STR+20','STR+20','Accuracy+20 Attack+20','Weapon skill damage +10%','Damage taken-5%'],['STR+20','STR+10','Accuracy+20','Attack+20','Weapon skill damage +10%','Damage taken-5%']]:assert not requirements_match(r,{'augments':a})
 assert not requirements_match(slots(c,'precast')['back']['requirements'],{'augments':['HP+60','Fast Cast+10']})
 assert not requirements_match(slots(c,'savage-blade')['ear1']['requirements'],{'augments':['Attack+4','TP Bonus+250']})
 assert slots(c,'savage-blade')['body']['requirements']=={'path':'B'}
def test_original_evidence_digests_and_bounded_coverage(batch):
 c,p,_,_=batch;o=read('gear-guide-t7-pld-observations.json');cards=read('gear-guide-t7-pld-item-evidence.json')['items']
 assert len(o['table_observations'])==12 and len(o['guide_observations'])==2 and len(cards)==46
 for r in o['table_observations']+o['guide_observations']+cards:assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
 assert 'oldid=780215' in o['guide_observations'][1]['url']
 for r in cards:assert r['independent_public_card_verified'] and any(s['url']==r['url'] and r['observation_sha256'] in s['locator'] for s in c['sources'])
 rows=[r for r in c['coverage'] if r['job']=='PLD'];assert len(rows)==10 and all(r['status']=='included' and r['set_ids'] for r in rows)
 assert len([r for r in c['revisions'] if r['set_id'].startswith('nexus:pld:')])==27
 assert len(p['items'])==863 and len(EVIDENCE)==55
