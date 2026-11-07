from pathlib import Path
import hashlib,json
F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(n):return json.loads((F/n).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def test_label_successor_retains_history_and_exact_equipment():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-bst-ear-label-correction.json');by={r['id']:r for r in c['revisions']};a=p['amendment'];prior,new=by[a['retired_revision_id']],by[a['successor_revision_id']]
 for f in ('set_id','slots','verification','resource_fingerprint','equipment_version','composition_kind','provenance_reconciliation'):assert new[f]==prior[f]
 assert prior['version_order']==2 and new['version_order']==3
 b=next(b for b in c['authoring_batches'] if b['id']=='bst-ear-labels-2026-11-05')
 for f,history in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in history.items())
 assert [len(c[f]) for f in ('sets','revisions','sources','coverage')]==[520,547,1331,231]
def test_exact_id_names_and_ear_side_reversal_from_original_grid():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-bst-ear-label-correction.json');resources={r['id']:r for r in read('gear-guide-t7-resource-evidence.json')['items']};new=next(r for r in c['revisions'] if r['id']==p['amendment']['successor_revision_id'])
 assert resources[27544]['en']=='Dedition Earring' and resources[26084]['en']=='Sherida Earring' and resources[27545]['en']=='Telos Earring'
 assert p['source_slots']==dict(ear1=dict(item_id=27544,name='Dedition Earring'),ear2=dict(item_id=26084,name='Sherida Earring'))
 s={x['slot']:x for x in new['slots']};assert (s['ear1']['item_id'],s['ear2']['item_id'])==(26084,27544)
 assert 'Dedition Earring27544 ear1 / Sherida Earring26084 ear2' in new['rationale'] and 'Telos Earring is27545' in new['rationale']
 g=next(x for x in read('gear-guide-t7-bst-second-pass-slots.json')['observations'] if x['url'].endswith('/381576'))
 assert [x for x in g['equipment_macro_lines'] if x['slot'].startswith('ear')]==[dict(slot='ear1',name='Dedition Earring'),dict(slot='ear2',name='Sherida Earring')]
def test_correction_changes_no_coverage_resources_hands_or_effective_count():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-bst-ear-label-correction.json')
 retired={x['retired_revision_id'] for b in c['authoring_amendments'] for x in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert p['new_hands']==p['new_resources']==p['new_requirements']==0
 assert len(read('gear-guide-t7-resource-evidence.json')['items'])==863 and len(c['coverage'])==231
