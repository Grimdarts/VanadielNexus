"""BRD stage/capacity/augment regressions; detached public resources only."""
from copy import deepcopy
import ast
import hashlib
import json
from pathlib import Path
import pytest
from vanadiel_nexus.core.equipment_hands import EVIDENCE, hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS, allocate_requirements, requirements_match
from vanadiel_nexus.core.guide_catalog import composition_diagnostics, validate_catalog
from vanadiel_nexus.core.item_res import Item

ROOT=Path(__file__).resolve().parents[2]
F=ROOT/'docs/catalog'
def read(name):return json.loads((F/name).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
@pytest.fixture
def batch():
    c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json')
    items={r['id']:Item(**r) for r in p['items']}
    return c,p,items,hand_types(items)
def rev(c,key):return max((r for r in c['revisions'] if r['set_id']=='nexus:brd:'+key),key=lambda r:r['version_order'])
def slots(c,key):return {s['slot']:s for s in rev(c,key)['slots']}
def context(c,key):return next(s['context'] for s in c['sets'] if s['id']=='nexus:brd:'+key)

def test_brd_preserves_all_136_prior_records_and_218_sources(batch):
    c,p,items,hands=batch
    history=c['authoring_batches'][6]['baseline_record_hashes']
    assert len(history['sets'])==len(history['revisions'])==136
    assert len(history['sources'])==218
    for field in ('sets','revisions','sources'):
        byid={r['id']:r for r in c[field]}
        assert all(digest(byid[k])==h for k,h in history[field].items())
    validate_catalog(c,items=items,hand_types=hands)
    assert len(EVIDENCE)==55 and EVIDENCE[18].item_id==20599
    assert hands[20599]=='one_handed' and items[20599].skill==2
    bad=deepcopy(items);bad[20599]=Item(**{**next(r for r in p['items'] if r['id']==20599),'skill':3})
    assert 20599 not in hand_types(bad)

@pytest.mark.parametrize('key',[
 'dt-idle','refresh-idle','song-general','march','minuet','madrigal','prelude','ballad',
 'scherzo','paeon','etude','carol','minne','mambo','honor-march','dummy-terpander',
 'dummy-daurdabla','debuff-accuracy','threnody','lullaby-wind','lullaby-string',
 'fast-cast','song-precast','honor-precast','engaged-balanced','engaged-dt',
 'engaged-accuracy','savage-blade'])
def test_brd_composition_has_complete_slots_and_bounded_claim(batch,key):
    c,p,items,hands=batch;r=rev(c,key)
    assert r['origin']=='nexus_recommendation' and r['currency']=='unknown'
    assert r['verification']['status']=='verified'
    assert 'No complete effects' in r['verification']['scope']
    assert {s['slot'] for s in r['slots']}==set(SLOTS)
    assert slots(c,key)['ammo']==dict(slot='ammo',state='empty')
    assert not composition_diagnostics(r['slots'],items,['BRD'],hand_types=hands,context=context(c,key))
    assert all(s['name']==items[s['item_id']].en for s in r['slots'] if s['state']=='selected')

def test_instrument_display_name_does_not_select_relic_stage_or_extra_slots(batch):
    c,p,_,_=batch
    assert slots(c,'song-general')['range']['item_id']==18572
    assert slots(c,'dummy-daurdabla')['range']['item_id']==18571
    desc=p['descriptions']
    assert 'All songs +4' in desc['18572'] and 'two additional' in desc['18571']
    assert slots(c,'honor-march')['range']['item_id']==slots(c,'honor-precast')['range']['item_id']==21398
    assert 'Able to use Honor March' in desc['21398']
    assert 'no extra capacity' in context(c,'song-general')['instrument']
    assert 'Clarion Call is separate' in context(c,'dummy-daurdabla')['sequence']
    assert 'Does not itself add song slots' in context(c,'honor-march')['capacity']

def test_dummy_gear_has_no_optional_song_duration_potency_or_fc_linos(batch):
    c,_,_,_=batch
    for key in ('dummy-terpander','dummy-daurdabla'):
        r=slots(c,key)
        assert r['main']['item_id']==22040 and r['neck']['item_id']!=26033
        assert 26255 not in {s.get('item_id') for s in r.values()}
        assert all(s.get('requirements',{})=={} for s in r.values())
    assert slots(c,'dummy-terpander')['range']['item_id']==21407
    assert 'does not stack' in context(c,'dummy-terpander')['capacity']

def test_song_swaps_preserve_duration_tradeoffs_and_nq_mousai(batch):
    c,p,_,_=batch
    assert slots(c,'ballad')['legs']['item_id']==23630
    assert slots(c,'song-general')['legs']['item_id']==25882
    assert slots(c,'scherzo')['feet']['item_id']==23697
    assert slots(c,'song-general')['feet']['item_id']==23652
    for key,slot,item in [('minne','legs',25901),('mambo','feet',25968),('threnody','body',26537)]:
        assert slots(c,key)[slot]['item_id']==item
        assert '+1' not in slots(c,key)[slot]['name']
        assert '500 BRD Job Points' in context(c,key)['access']
    assert '"Minne"+1' in p['descriptions']['25901']
    assert slots(c,'carol')['hands']['item_id']==25989 and slots(c,'etude')['head']['item_id']==25562

def test_wind_accuracy_does_not_certify_string_radius_and_su2_is_required(batch):
    c,p,_,_=batch
    assert slots(c,'lullaby-wind')['range']['item_id']==18572
    assert slots(c,'lullaby-string')['range']['item_id']==21401
    assert '100 BRD Job Points' in context(c,'lullaby-string')['access']
    assert 'String skill dependent' in context(c,'lullaby-string')['recipient']
    assert slots(c,'lullaby-string')['hands']['item_id']==23994
    assert 'Lullaby' in p['descriptions']['23994']
    assert '567/648' in rev(c,'lullaby-string')['rationale']

def test_fc_tp_ws_require_different_linos_and_cape_copies_and_no_rank_fiction(batch):
    c,_,_,_=batch
    fc=slots(c,'fast-cast');tp=slots(c,'engaged-balanced');ws=slots(c,'savage-blade')
    assert fc['range']['requirements']['augments']==['"Fast Cast"+6']
    assert fc['back']['requirements']['augments']==['"Fast Cast"+10']
    assert '"Store TP"+4' in tp['range']['requirements']['augments']
    assert 'STR+8' in ws['range']['requirements']['augments']
    assert tp['back']['requirements']!=ws['back']['requirements']!=fc['back']['requirements']
    for slot in ('head','hands','legs','feet'):assert ws[slot]['requirements']=={'path':'B'}
    assert slots(c,'song-precast')['range']['requirements']=={}
    assert 'recast' in rev(c,'song-precast')['rationale']
    assert 'rank unspecified' in rev(c,'savage-blade')['rationale']
    assert 'no Dual Wield' in context(c,'engaged-balanced')['subjob']

def test_exact_decoded_copies_match_successors_and_reject_summary_totals(batch):
    c,_,_,_=batch
    native={
      ('fast-cast','range'):['"Fast Cast"+6'],
      ('fast-cast','back'):['"Fast Cast"+10'],
      ('engaged-balanced','range'):['Accuracy+15 Attack+15','"Store TP"+4','Quadruple Attack +3'],
      ('engaged-balanced','back'):['DEX+20','Accuracy+20 Attack+20','DEX+10','"Store TP"+10','Damage taken-5%'],
      ('savage-blade','back'):['STR+20','Accuracy+20 Attack+20','STR+10','Weapon skill damage +10%','Damage taken-5%'],
      ('debuff-accuracy','back'):['CHR+20','Mag. Acc+20 /Mag. Dmg.+20','Mag. Acc.+10']}
    for (key,slot),parts in native.items():
        assert requirements_match(slots(c,key)[slot]['requirements'],{'augments':parts})
        first=next(r for r in c['revisions'] if r['set_id']=='nexus:brd:'+key)
        initial=next(s for s in first['slots'] if s['slot']==slot)
        assert not requirements_match(initial['requirements'],{'augments':parts})
    assert not requirements_match(slots(c,'engaged-balanced')['back']['requirements'],
      {'augments':['DEX+30','Accuracy+20 Attack+20','"Store TP"+10','Damage taken-5%']})

def test_augment_amendments_preserve_initial_records_and_select_latest_version(batch):
    c,_,_,_=batch
    amendments=next(b for b in c['authoring_amendments'] if b['id']=='brd-augment-parts-2026-11-04')['amendments'];assert len(amendments)==11
    history=c['authoring_batches'][7]['baseline_record_hashes']
    assert len(history['revisions'])==164 and len(history['sources'])==277
    for field in ('sets','revisions','sources'):
        current={r['id']:r for r in c[field]}
        assert all(digest(current[k])==v for k,v in history[field].items())
    for a in amendments:
        successor=next(r for r in c['revisions'] if r['id']==a['successor_revision_id'])
        assert successor['supersedes_revision_id']==a['retired_revision_id']
        assert successor['version_order']==2 and 'corrected augment parts' in successor['label']
    assert len([r for r in c['revisions'] if r['set_id'].startswith('nexus:brd:')])==39

def test_refresh_does_not_assume_citizenship_or_instrument_removal(batch):
    c,_,_,_=batch;r=slots(c,'refresh-idle')
    assert r['neck']['item_id']!=25416
    assert r['range']['item_id']==21404 and r['ammo']['state']=='empty'
    assert 'MP-using subjob' in context(c,'refresh-idle')['subjob']
    pair=[r['ring1'],r['ring2']]
    assert pair[0]['item_id']==pair[1]['item_id']==26184
    assert sum(x['owned'] for x in allocate_requirements(pair,[dict(character_key='fictional',item_id=26184,bag_id=8)],'fictional').values())==1

def test_observations_preserve_order_omissions_and_are_not_claimed_raw_html():
    packet=read('gear-guide-t7-brd-observations.json')
    rows=packet['table_observations'];assert len(rows)==10
    for r in rows+packet['guide_observations']:
        assert digest({k:v for k,v in r.items() if k!='observation_sha256'})==r['observation_sha256']
    byid={r['item_set']:r for r in rows}
    assert byid[363887]['ordered_macro_entries'][0]['slot']=='back'
    assert byid[363883]['ordered_macro_entries'][7]['slot']=='hands'
    assert {'main','sub','ammo'}<=set(byid[363865]['omitted_slots'])
    assert byid[363865]['occupied_entry_count']==13 and byid[363865]['conflicts']
    assert byid[363874]['ordered_macro_entries'][-1]['name']=="Mpaca's Staff"
    assert all('not raw HTML' in r['representation'] for r in rows)
    cards=read('gear-guide-t7-brd-item-evidence.json')['items']
    assert len(cards)==37
    assert {r['item_id'] for r in cards}>={18571,18572,20599,21401,26255}

def test_nine_bounded_brd_priorities_leave_16_jobs_and_149_gaps(batch):
    c,_,_,_=batch;rows=[r for r in c['coverage'] if r['job']=='BRD']
    assert len(rows)==9 and all(r['status']=='included' and r['set_ids'] for r in rows)
    gaps=[r for r in c['coverage'] if r['status']=='gap']
    assert len(gaps)==0 and len({r['job'] for r in gaps})==0
    assert not any(r['status']=='not_applicable' for r in c['coverage'])
