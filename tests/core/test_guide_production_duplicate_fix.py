"""Jason-authorized production data fix: 10 BST guide sets now list both copies the source grid selects."""
from collections import Counter
from pathlib import Path
import json, hashlib
from vanadiel_nexus.core import gear_guides
R = Path(__file__).resolve().parents[2]; F = R / 'docs/catalog'; PROD = R / 'docs/catalog/gear-guide-production-v1-2026-11-05.json'
def read(n): return json.loads((F / n).read_text(encoding='utf-8'))
def digest(v): return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
TARGETS = ['264975', '302857', '371161', '333993', '264979', '378247', '333131', '339931', '339932', '365917']


def grids():
    out = {o['set_id']: o for o in read('gear-guide-t7-bst-other27-audit.json')['observations']}
    out.update({o['url'].rsplit('/', 1)[-1]: o for o in read('gear-guide-t7-bst-second-pass-slots.json')['observations']})
    return out


def test_packet_records_the_authorized_byte_change():
    p = read('gear-guide-t7-production-duplicate-fix.json'); raw = PROD.read_bytes()
    assert p['prior_sha256'] == read('gear-guide-t7-bst-other27-audit.json')['production_sha256'] == \
        '54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85'
    assert hashlib.sha256(raw).hexdigest() == p['sha256'] and len(raw) == p['bytes'] and b'\r\n' not in raw
    assert raw == (json.dumps(json.loads(raw), indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    assert [r['set_id'] for r in p['records']] == TARGETS and p['counts'] == dict(sets=10, copies=11, sets_total=376, sets_changed=10)
    assert "'1. Yes fix.'" in p['authorization']


def test_every_bst_grid_copy_count_now_matches_production():
    P = {s['id']: s for s in json.loads(PROD.read_text(encoding='utf-8'))['sets']}; G = grids(); assert len(G) == 48
    for sid, o in G.items():
        grid = Counter(i for v in o['slot_grid'].values() for i in v); rec = Counter(i['item_id'] for i in P[sid]['items'])
        assert not (grid - rec), sid
        if sid in TARGETS:
            assert grid == rec, sid


def test_inserted_copies_are_identical_neighbours_and_nothing_else_changed():
    p = read('gear-guide-t7-production-duplicate-fix.json'); prod = json.loads(PROD.read_text(encoding='utf-8'))
    P = {s['id']: s for s in prod['sets']}
    for r in p['records']:
        s = P[r['set_id']]; assert digest(s) == r['record_sha256']
        for c in r['inserted_copies']:
            i = c['inserted_index']; assert s['items'][i] == s['items'][i - 1] and s['items'][i]['item_id'] == c['item_id']
            assert Counter(x['item_id'] for x in s['items'])[c['item_id']] == 2 and len(c['grid_slots']) == 2
    untouched = [s for s in prod['sets'] if s['id'] not in TARGETS]
    assert len(untouched) == 366 and digest(untouched) == p['unchanged']['untouched_sets_sha256']
    assert gear_guides.load_catalog()['schema_version'] == 1


def test_one_owned_copy_is_no_longer_complete_for_a_two_copy_set():
    entry = {s['id']: s for s in gear_guides.load_catalog()['sets']}['378247']
    one = [{'character': 'Fictional', 'item_id': 26182, 'name': 'Chirich Ring +1', 'count': 1}]
    rows = [r for r in gear_guides.set_rows(entry, one, 'Fictional') if r['item_id'] == 26182]
    assert [(r['status'], r['detail']) for r in rows] == [('Missing', '1/2 copies in the selected character snapshot.')] * 2
    two = [{**one[0], 'count': 2}]
    rows = [r for r in gear_guides.set_rows(entry, two, 'Fictional') if r['item_id'] == 26182]
    assert [(r['status'], r['detail']) for r in rows] == [('Owned', '2/2 copies found.')] * 2


# These regressions intentionally exercise the retained v1 compatibility path.
import pytest
from tests.guide_bundle_fixtures import LEGACY

@pytest.fixture(autouse=True)
def retained_v1_bundle(monkeypatch):
    from vanadiel_nexus.core import gear_guides
    monkeypatch.setattr(gear_guides, 'resource_path', lambda *_: str(LEGACY))
