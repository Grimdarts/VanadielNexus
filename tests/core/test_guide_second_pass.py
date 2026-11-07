"""Guard all-job scope and lossless BST source-grid correction, independent of author definitions."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import pytest
from vanadiel_nexus.core.equipment_matching import SLOTS

F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(n): return json.loads((F/n).read_text(encoding='utf-8'))
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
IDS=[323870,323871,264975,302857,381578,381577,381576,371161,333283,347567,391446,337061,337063,337064,342233,333993,320353,335128,264979,281814,347643]
def successor(sid):
    return next(r for r in read('gear-guide-t7-bst-second-pass-slots.json')['observations'] if r['id']==f'bst:second-pass:slots:{sid}:2026-11-05')

@pytest.mark.parametrize('sid',IDS)
def test_grid_successor_preserves_original_and_omission_semantics(sid):
    packet=read('gear-guide-t7-bst-second-pass-slots.json'); r=successor(sid)
    old=next(x for x in read('gear-guide-t7-bst-observations.json')['table_observations'] if x.get('key')==r['prior_observation_key'])
    assert r['prior_observation_sha256']==old['observation_sha256']
    assert r['observation_sha256']==digest({k:v for k,v in r.items() if k!='observation_sha256'})
    assert list(r['slot_grid'])==list(SLOTS) and len(r['cells'])==16
    for i,(slot,cell) in enumerate(zip(SLOTS,r['cells']),1):
        assert cell['slot']==slot and cell['index']==i and cell['item_ids']==r['slot_grid'][slot]
        assert len(cell['item_ids'])<=1
        assert cell['placeholder_number']==(None if cell['item_ids'] else i)
    assert r['source_omissions']==[s for s,v in r['slot_grid'].items() if not v]
    assert r['capture']['status']==200 and r['capture']['url']==f'https://www.ffxiah.com/item-sets/{sid}'
    assert r['capture']['final_url']==r['capture']['url'] and r['capture']['body_sha256']
    assert not r['macro_grid_conflicts']
    amendment=next(x for x in packet['source_observation_amendments'] if x['successor_observation_id']==r['id'])
    assert amendment['prior_observation_sha256']==old['observation_sha256'] and amendment['successor_observation_sha256']==r['observation_sha256'] and amendment['catalog_mutation'] is False

def test_refresh_grid_has_two_distinct_ring_cells_and_real_omissions():
    r=successor(264975)
    # Independent literal page cells, not a transformation of the authored Nexus target.
    assert r['slot_grid']==dict(zip(SLOTS,[[],[],[],[],[24270],[25416],[],[],[26972],[27139],[26184],[26184],[],[],[25841],[27495]]))
    assert sum(line==dict(slot='ring1',name='Stikini Ring +1') for line in r['equipment_macro_lines'])==1
    assert sum(line==dict(slot='ring2',name='Stikini Ring +1') for line in r['equipment_macro_lines'])==1

def test_repeated_shield_macro_is_one_slot_not_two_physical_copies():
    r=successor(302857)
    assert r['slot_grid']['sub']==[28657]
    assert r['old_item_order_retained'].count(28657)==2
    assert sum(line==dict(slot='sub',name='Kaidate') for line in r['equipment_macro_lines'])==2
    assert r['slot_grid']['ear1']==[14747] and r['slot_grid']['ear2']==[14747]
    assert Counter(r['old_item_order_retained'])-Counter(i for v in r['slot_grid'].values() for i in v)==Counter({28657:1})

def test_bst_slice_is_evidence_only_and_keeps_all_prior_recommendations():
    p=read('gear-guide-t7-bst-second-pass-slots.json'); c=read('gear-guide-t7-candidate.json')
    assert p['counts']==dict(pages=21,cells=336,selected=275,omissions=61,macro_conflicts=0,changed_item_multisets=1)
    assert len(p['source_observation_amendments'])==21 and len(p['nexus_reconciliation'])==19
    assert sum(s['id'].startswith('nexus:bst:') for s in c['sets'])==14
    assert len([s for s in c['sources'] if s['id'].startswith('bst:second-pass:')])==21
    assert all('Comparison only' in r['boundary'] for r in p['nexus_reconciliation'])

def test_inventory_reconciles_all_jobs_and_keeps_smn_unclaimed_obligation():
    p=read('gear-guide-t7-second-pass-inventory.json'); c=read('gear-guide-t7-candidate.json')
    expected=set('WAR MNK WHM BLM RDM THF PLD DRK BST BRD RNG SAM NIN DRG SMN BLU COR PUP DNC SCH GEO RUN'.split())
    assert {r['job'] for r in p['jobs']}==expected and len(p['jobs'])==22
    assert sum(len(r['coverage_rows']) for r in p['jobs'])==225
    added=read('gear-guide-t7-smn-engaged-definitions.json')['coverage_reconciliation']
    assert len(added)==3
    hasso=read('gear-guide-t7-smn-hasso-definitions.json')['coverage_reconciliation']
    assert len(hasso)==3
    added=added+hasso
    assert [r for j in p['jobs'] for r in j['coverage_rows']]==[r for j in p['jobs'] for r in c['coverage'] if r['job']==j['job'] and r not in added]
    assert len({r['id'] for r in p['issues']})==len(p['issues'])
    assert all(r['classification'] in ('fixable now','source-limited','explicitly deferred','not reproduced') and r['evidence'] for r in p['issues'])
    assert any(r['job']=='SMN' and r['classification']=='fixable now' and 'matrix rows' in r['title'] for r in p['issues'])
    assert len([r for r in p['reviewed_inputs'] if r['kind']=='complete job report'])==23
    assert len([r for r in p['reviewed_inputs'] if r['kind']=='complete job packet'])==91

def test_dnc_closeout_and_immutable_inventory_snapshot():
    d=read('gear-guide-t7-dnc-readback.json'); p=read('gear-guide-t7-second-pass-inventory.json')
    assert d['checks_passed']==55 and len(d['checks'])==55
    assert d['candidate_summary']['revisions']==525 and d['effective_recommendations']==506
    assert d['historical_validation']['full-native.log']['passed']==1423
    assert 'Historical' in d['historical_validation']['focused.log']['scope']
    candidate=next(r for r in p['reviewed_inputs'] if r['path']=='docs/catalog/gear-guide-t7-candidate.json')
    integration=read('gear-guide-t7-bst-provenance-integration.json')
    assert integration['baseline_candidate_sha256']==candidate['sha256']
    smn=read('gear-guide-t7-smn-engaged-definitions.json')
    assert smn['baseline_candidate_sha256']==integration['candidate_sha256']
    labels=read('gear-guide-t7-bst-ear-label-correction.json')
    assert labels['baseline_candidate_sha256']==smn['candidate_sha256']
    hasso=read('gear-guide-t7-smn-hasso-definitions.json')
    assert hasso['baseline_candidate_sha256']==labels['candidate_sha256']
    other27=read('gear-guide-t7-bst-other27-audit.json')
    assert other27['baseline_candidate_sha256']==hasso['candidate_sha256']
    fallback=read('gear-guide-t7-scope-fallback-correction.json')
    assert fallback['baseline_candidate_sha256']==other27['candidate_sha256']
    status=read('gear-guide-t7-run-status-correction.json')
    c=read('gear-guide-t7-candidate.json')
    assert status['baseline_candidate_sha256']==fallback['candidate_sha256']
    assert hashlib.sha256((F/'gear-guide-t7-candidate.json').read_bytes()).hexdigest()==status['candidate_sha256']
    assert c['delivery_status']==status['successor_delivery_status']
    assert c['delivery_status'].endswith(status['prior_delivery_status'])
    reconstructed=dict(c,delivery_status=status['prior_delivery_status'])
    assert hashlib.sha256((json.dumps(reconstructed,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()==status['baseline_candidate_sha256']
