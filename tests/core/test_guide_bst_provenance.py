"""Provenance successors retain immutable history and exact selected equipment."""
import hashlib,json
from pathlib import Path
import pytest
F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(n):return json.loads((F/n).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def catalog():return read('gear-guide-t7-candidate.json')
def latest(key):return max((r for r in catalog()['revisions'] if r['set_id']=='nexus:bst:'+key),key=lambda r:r['version_order'])

def test_every_preexisting_record_is_immutable_and_no_default_retarget():
 c=catalog();b=next(x for x in c['authoring_batches'] if x['id']=='bst-provenance-2026-11-05')
 assert {f:len(v) for f,v in b['baseline_record_hashes'].items()}==dict(sets=514,revisions=525,sources=1271)
 for f,m in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in m.items())
 assert not any('default_revision_id' in s for s in c['sets'])
 a=next(x for x in c['authoring_amendments'] if x['id']=='bst-provenance-2026-11-05')
 assert len(a['amendments'])==13
 by={r['id']:r for r in c['revisions']}
 for x in a['amendments']:
  old,new=by[x['retired_revision_id']],by[x['successor_revision_id']]
  assert new['slots']==old['slots'] and new['set_id']==old['set_id'] and new['version_order']==old['version_order']+1
  assert new['verification']==old['verification'] and new['equipment_version']==old['equipment_version']
 retired={x['retired_revision_id'] for b in c['authoring_amendments'] for x in b['amendments']}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert len([r for r in retired if r.startswith('nexus:brd:')])==11

@pytest.mark.parametrize('sid',[323870,323871,264975,302857,381578,381577,381576,371161,333283,347567,391446,337061,337063,337064,342233,333993,320353,335128,264979,281814,347643])
def test_source_successors_bind_exact_page_capture_and_prior_source(sid):
 c=catalog();grid=next(g for g in read('gear-guide-t7-bst-second-pass-slots.json')['observations'] if g['url'].endswith('/'+str(sid)))
 src=next(s for s in c['sources'] if s['id']==grid['id'])
 assert src['url']==f'https://www.ffxiah.com/item-sets/{sid}' and grid['observation_sha256'] in src['locator'] and grid['capture']['body_sha256'] in src['locator']
 assert (grid['current_set_note'] or '[no item-set update note supplied]') in src['locator']
 a=next(a for a in c['source_observation_amendments'] if a['source_id']==grid['id'])
 prior=next(s for s in c['sources'] if s['id']==a['supersedes_source_id'])
 assert digest(prior)==a['prior_source_sha256'] and grid['prior_observation_sha256'] in prior['locator']
 for r in c['revisions']:
  if r['set_id'].startswith('nexus:bst:') and r['version_order']>1:assert a['supersedes_source_id'] not in r['source_ids']

def test_pet_source_hands_and_nexus_tradeoff_are_explicit():
 r=latest('pet-accuracy');s={x['slot']:x.get('item_id') for x in r['slots']}
 assert s['main']==21730 and s['sub']==21738
 assert 'Telopanos Axe 21738 main / Spalirisos 21730 sub' in r['rationale'] and 'deliberately reverses' in r['rationale']
 assert 'without hands' not in r['rationale']
 for g in read('gear-guide-t7-bst-second-pass-slots.json')['observations']:
  if g['url'].endswith(('/337064','/347643')):assert g['slot_grid']['main']==[21738] and g['slot_grid']['sub']==[21730]

def test_balanced_ears_and_source_omissions_are_distinct():
 r=latest('engaged-balanced');s={x['slot']:x.get('item_id') for x in r['slots']}
 assert (s['ear1'],s['ear2'])==(26084,27544)
 assert 'Dedition Earring27544 ear1 / Sherida Earring26084 ear2' in r['rationale'] and 'omits both weapon hands' in r['rationale']
 assert len(r['provenance_reconciliation']['comparisons'])==1
 assert latest('engaged-dt')['version_order']==1

def test_integration_packet_supersedes_pending_findings_without_waiving_variants():
 p=read('gear-guide-t7-bst-provenance-integration.json');c=catalog()
 assert len(p['source_amendments'])==21 and len(p['revision_amendments'])==13
 assert [x['status'] for x in p['issue_dispositions']]==['fixed in candidate provenance']*3+['explicitly deferred']
 assert p['new_resources']==p['new_hands']==p['new_requirements']==0
 assert 'SMN' in c['delivery_status'] and 'all22jobs' in c['delivery_status'] and 'DNC' in c['delivery_status']
