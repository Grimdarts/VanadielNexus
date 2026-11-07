"""BST other27 node 227 scope audit: evidence-only grids, production defects recorded, one source attribution successor."""
from collections import Counter
from pathlib import Path
import json, hashlib
from vanadiel_nexus.core.equipment_matching import SLOTS
R = Path(__file__).resolve().parents[2]; F = R / 'docs/catalog'
def read(n): return json.loads((F / n).read_text(encoding='utf-8'))
def digest(v): return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
def packet(): return read('gear-guide-t7-bst-other27-audit.json')
def production():
    # Historical audit comparisons stay pinned to the retained v1 snapshot.
    return json.loads((R / 'docs/catalog/gear-guide-production-v1-2026-11-05.json').read_text(encoding='utf-8'))
OTHER = ['264977', '378207', '250145', '333128', '378247', '365036', '250549', '262999', '292382', '257714', '390390', '335643', '308312',
         '333131', '311276', '333386', '326913', '326915', '326916', '333218', '326554', '366003', '365916', '339928', '339931', '339932', '365917']


def test_scope_is_exactly_the_27_deferred_node_sets_in_node_order():
    p = packet(); prod = production(); guide = next(g for g in prod['guides'] if g['job'] == 'BST')
    scoped = {o['url'].rsplit('/', 1)[-1] for o in read('gear-guide-t7-bst-second-pass-slots.json')['observations']}
    assert [o['set_id'] for o in p['observations']] == OTHER == [i for i in guide['set_ids'] if i not in scoped]
    assert p['node']['linked_ids'] == guide['set_ids'] and len(p['node']['linked_ids']) == 48
    assert p['node']['last_modified'] == '2026-06-25 20:01:27' and p['node']['capture']['last_modified_header'] is None


def test_each_grid_is_sixteen_cells_hashed_and_classified():
    p = packet()
    assert p['classification_counts'] == dict(confirmed=22, label_attribution_defect=5, source_drift=0, source_limited=0)
    assert p['counts'] == dict(pages=27, cells=432, selected=338, omissions=94, macro_conflicts=0)
    for o in p['observations']:
        body = {k: v for k, v in o.items() if k != 'observation_sha256'}
        assert digest(body) == o['observation_sha256'] and o['capture']['status'] == 200 and len(o['capture']['body_sha256']) == 64
        assert [c['slot'] for c in o['cells']] == list(SLOTS) and list(o['slot_grid']) == list(SLOTS)
        assert all((c['item_ids'] == []) == (c['placeholder_number'] == c['index']) for c in o['cells'])
        assert o['source_omissions'] == [s for s, v in o['slot_grid'].items() if not v] and o['macro_grid_conflicts'] == []
        assert all(r['fits'] and r['bst_wearable'] for r in o['exact_resource_checks'])
        assert o['page_revision'].startswith('FFXIAH exposes no revision id') and o['candidate_records'] == 0
        assert (o['classification'] == 'confirmed') == (o['comparison']['grid_copies_missing_from_record'] == [])


def test_production_duplicate_copy_defects_recorded_then_fixed_by_authorized_successor():
    p = packet(); P = {s['id']: s for s in production()['sets']}
    fix = read('gear-guide-t7-production-duplicate-fix.json'); prior = {r['set_id']: r['prior_record_sha256'] for r in fix['records']}
    assert [a['set_id'] for a in p['production_record_amendments']] == ['378247', '333131', '339931', '339932', '365917']
    expected = {'378247': (26182, 'Chirich Ring +1'), '333131': (26184, 'Stikini Ring +1'), '339931': (20809, 'Kumbhakarna'),
                '339932': (20809, 'Kumbhakarna'), '365917': (27566, 'Levia. Ring')}
    for a in p['production_record_amendments']:
        assert a['production_mutation'] is False and a['catalog_mutation'] is False
        (miss,) = a['missing_copies']; assert (miss['item_id'], miss['name']) == expected[a['set_id']]
        assert miss['grid_copies'] == 2 and miss['recorded_copies'] == 1 and len(miss['grid_slots']) == 2
        rec = P[a['set_id']]; assert prior[a['set_id']] == a['production_record_sha256'] != digest(rec)
        assert Counter(i['item_id'] for i in rec['items'])[miss['item_id']] == 2
    assert p['production_sha256'] == fix['prior_sha256'] == '54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85'
    publication=read('gear-guide-t7-production-replacement.json')
    assert publication['prior_production_sha256']==fix['sha256']
    assert hashlib.sha256((R / publication['legacy_snapshot_path']).read_bytes()).hexdigest()==fix['sha256']
    assert hashlib.sha256((R / 'vanadiel_nexus/resources/gear_guides.json').read_bytes()).hexdigest()==publication['production_sha256']


def test_node_inventory_source_successor_is_append_only_and_uncited():
    c = read('gear-guide-t7-candidate.json'); p = packet(); S = {s['id']: s for s in c['sources']}
    old = S['bst:t7:scope-node-inventory:2026-11-05']; new = S['bst:other27:node-inventory:2026-11-05']
    assert (old['kind'], old['url']) == ('bgwiki', 'https://www.bg-wiki.com/ffxi/Ready')
    assert (new['kind'], new['url']) == ('ffxiah', 'https://www.ffxiah.com/node/227') and new == p['candidate_source_successor']
    a = next(x for x in c['source_observation_amendments'] if x['source_id'] == new['id']); assert a == p['candidate_source_amendment']
    assert a['supersedes_source_id'] == old['id'] and a['prior_source_sha256'] == digest(old) and a['related_revision_ids'] == []
    inv = p['node_inventory_successor']; assert a['observation_sha256'] == inv['observation_sha256'] == digest({k: v for k, v in inv.items() if k != 'observation_sha256'})
    assert inv['prior_observation_sha256'] == 'b0f28f2bca38dbf39f7908848f73a13997ba343c08af827f8e915d405d25a777'
    assert [w['title'] for w in inv['linked_ws_item_sets']] == ['BST Rampage', 'BST Mistral Axe', 'BST Decimation', 'BST Ruinator', 'BST Onslaught',
                                                                 'BST Primal Rend', 'BST Cloudsplitter', 'BST Blitz']
    assert not any(old['id'] in r['source_ids'] or new['id'] in r['source_ids'] for r in c['revisions'])
    b = next(x for x in c['authoring_batches'] if x['id'] == 'bst-other27-audit-2026-11-05')
    for f in ('sets', 'revisions'):
        n = len(b['baseline_record_hashes'][f])
        assert {r['id']: digest(r) for r in c[f][:n]} == b['baseline_record_hashes'][f]
    assert {r['id']: digest(r) for r in c['sources'][:c['sources'].index(new)]} == b['baseline_record_hashes']['sources']


def test_engaged_accuracy_claim_corroborated_and_gear_unchanged():
    p = packet(); c = read('gear-guide-t7-candidate.json')
    grid = next(o for o in p['observations'] if o['set_id'] == '378247')['slot_grid']
    assert grid['ring1'] == grid['ring2'] == [26182]
    for r in c['revisions']:
        if r['set_id'] == 'nexus:bst:engaged-accuracy':
            rings = {x['slot']: x['item_id'] for x in r['slots'] if x['slot'] in ('ring1', 'ring2')}
            assert rings == {'ring1': 26182, 'ring2': 26182}
    assert set(p['engaged_accuracy_corroboration']['revision_ids']) < {r['id'] for r in c['revisions'] if r['set_id'] == 'nexus:bst:engaged-accuracy'}


def test_no_historical_incorrect_ear_labels_repeated():
    text = (F / 'gear-guide-t7-bst-other27-audit.json').read_text(encoding='utf-8')
    for bad in ('Sherida27544', 'Sherida 27544', 'Telos26084', 'Telos 26084'):
        assert bad not in text
