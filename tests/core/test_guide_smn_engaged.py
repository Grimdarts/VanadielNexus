"""Bounded master engagement: provenance, actual identities and immutable prior coverage."""
from pathlib import Path
from collections import Counter
from dataclasses import replace
import json,hashlib
import pytest
from vanadiel_nexus.core.item_res import Item
from vanadiel_nexus.core.equipment_hands import hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS,allocate_requirements
from vanadiel_nexus.core.guide_catalog import composition_diagnostics,validate_catalog
F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(n):return json.loads((F/n).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
@pytest.fixture
def batch():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json');items={x['id']:Item(**x) for x in p['items']};return c,p,items,hand_types(items)
def revision(c,key):return next(r for r in c['revisions'] if r['set_id']=='nexus:smn:engaged-'+key)
def test_prior_history_and_three_new_obligations(batch):
 c,p,items,h=batch;b=next(x for x in c['authoring_batches'] if x['id']=='smn-engaged-2026-11-05')
 assert {k:len(v) for k,v in b['baseline_record_hashes'].items()}==dict(sets=514,revisions=538,sources=1292)
 for f,history in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in history.items())
 assert [len(c[k]) for k in ('sets','revisions','sources','coverage')]==[520,547,1331,231]
 assert len(p['items'])==863
 retired={x['retired_revision_id'] for b in c['authoring_amendments'] for x in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert sum(r['verification']['status']=='unresolved' for r in c['revisions'])==8
 rows=[r for r in c['coverage'] if r['job']=='SMN'];assert len(rows)==17
 assert {r['priority'] for r in rows if r['priority'].startswith('Engaged ')}=={'Engaged Balanced','Engaged DT','Engaged Accuracy'}
 assert all(r['status']=='included' for r in c['coverage'])
 validate_catalog(c,items=items,hand_types=h)
@pytest.mark.parametrize('key',['balanced','dt','accuracy'])
def test_exact_hands_pet_ammo_and_comparable_context(batch,key):
 c,p,items,h=batch;r=revision(c,key);s={x['slot']:x for x in r['slots']}
 assert list(s)==list(SLOTS) and s['range']==dict(slot='range',state='empty')
 assert s['main']['item_id']==22100 and s['sub']['item_id']==22218 and s['ammo']['item_id']==21381
 assert h[22100]=='two_handed' and h[22218]=='grip'
 assert not composition_diagnostics(r['slots'],items,['SMN'],hand_types=h)
 assert not any(x.get('requirements') for x in r['slots'])
 ctx=next(x['context'] for x in c['sets'] if x['id']==r['set_id'])
 assert 'SMN99/WAR49' in ctx['job'] and '/WAR has no Hasso' in ctx['haste']
 assert 'master is recipient' in ctx['role'] and 'Sroda Pet Alive' in ctx['pet'] and 'no aggregate' in ctx['haste']
 changed=dict(items);changed[22218]=replace(items[22218],skill=12)
 assert 22218 not in hand_types(changed)
 assert composition_diagnostics(r['slots'],changed,['SMN'],hand_types=hand_types(changed))
def test_balanced_retains_source_twelve_cells_and_fills_omissions(batch):
 c,_,_,_=batch;e=read('gear-guide-t7-smn-engaged-evidence.json');g=next(x for x in e['observations'] if x['item_set_id']==401863)
 s={x['slot']:x.get('item_id') for x in revision(c,'balanced')['slots']}
 assert g['source_omissions']==['main','sub','range','ammo']
 assert all(ids==[s[k]] for k,ids in g['slot_grid'].items() if ids)
 assert sum(bool(x) for x in g['slot_grid'].values())==12
def test_accuracy_duplicate_ring_needs_two_physical_copies(batch):
 c,_,_,_=batch;s=revision(c,'accuracy')['slots'];rings=[x for x in s if x.get('item_id')==26182];assert len(rings)==2
 for n in (1,2):
  allocated=allocate_requirements(rings,[dict(item_id=26182,character_key='fictional-smn',count=n)],'fictional-smn')
  assert sum(x['owned'] for x in allocated.values())==n
 assert Counter(x.get('item_id') for x in revision(c,'balanced')['slots'])[26182]==1
def test_dt_and_accuracy_are_attributed_tradeoffs(batch):
 c,_,_,_=batch;dt={x['slot']:x.get('item_id') for x in revision(c,'dt')['slots']};acc={x['slot']:x.get('item_id') for x in revision(c,'accuracy')['slots']}
 assert [dt[k] for k in ('neck','body','ring1')]==[26002,23768,13566]
 assert [acc[k] for k in ('head','hands','legs','ear1','ear2')]==[25573,25834,25885,27545,27541]
 assert 'no Shell, capped DT' in revision(c,'dt')['rationale']
 assert 'no modeled hit rate' in revision(c,'accuracy')['rationale']
def test_sources_and_original_deferral_remain_distinct():
 e=read('gear-guide-t7-smn-engaged-evidence.json');d=read('gear-guide-t7-smn-engaged-definitions.json')
 assert len(e['observations'])==3 and len(e['items'])==23 and len(e['nexus_reconciliation'])==9
 for g in e['observations']:
  assert digest({k:v for k,v in g.items() if k!='observation_sha256'})==g['observation_sha256']
  assert len(g['cells'])==16 and g['source_omissions']==['main','sub','range','ammo']
  assert g['capture']['status']==200 and g['capture']['last_modified'] is None
 assert e['node']['date_last_modified']=='2026-01-31 11:48:12'
 assert d['new_resources']==[25573,25796,25834,25885] and d['new_hands']==d['new_requirements']==0
 assert any('engaged' in x for x in read('gear-guide-t7-smn-definitions.json')['unclaimed'])
 assert len(read('gear-guide-t7-smn-definitions.json')['definitions'])==14
 assert 'Other' in d['unclaimed'][0] and 'BRD runtime retirement' in d['unclaimed'][-1]
