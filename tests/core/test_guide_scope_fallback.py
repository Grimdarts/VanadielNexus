"""Null-URL scope-source fallbacks (BST/PUP) corrected append-only; engaged-accuracy NIN AM3 citation completed."""
from pathlib import Path
import json, hashlib
F = Path(__file__).resolve().parents[2] / 'docs/catalog'
def read(n): return json.loads((F / n).read_text(encoding='utf-8'))
def digest(v): return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
FIX = {'bst:t7:scope-community-guide:2026-11-05': ('bst:fallback:community-guide:2026-11-05', 'bgwiki', 'https://www.bg-wiki.com/ffxi/Community_Beastmaster_Guide'),
       'pup:t7:scope-node-inventory:2026-11-05': ('pup:fallback:node-inventory:2026-11-05', 'ffxiah', 'https://www.ffxiah.com/node/426'),
       'pup:t7:scope-stage-conflicts:2026-11-05': ('pup:fallback:stage-conflicts:2026-11-05', 'ffxiah', 'https://www.ffxiah.com/node/426'),
       'pup:t7:scope-automaton-actions:2026-11-05': ('pup:fallback:automaton-actions:2026-11-05', 'bgwiki', 'https://www.bg-wiki.com/ffxi/String_Theory')}


def test_four_attribution_successors_with_amendments_and_retained_priors():
    c = read('gear-guide-t7-candidate.json'); S = {s['id']: s for s in c['sources']}
    A = {a['supersedes_source_id']: a for a in c['source_observation_amendments']}
    for old_id, (new_id, kind, url) in FIX.items():
        old = S[old_id]; new = S[new_id]; a = A[old_id]
        assert old['kind'] == 'bgwiki' and old['url'] in ('https://www.bg-wiki.com/ffxi/Ready', 'https://www.bg-wiki.com/ffxi/Maneuver')
        assert (new['kind'], new['url']) == (kind, url) and a['source_id'] == new_id and a['prior_source_sha256'] == digest(old)
        assert a['prior_observation_sha256'] == a['observation_sha256'] and a['observation_sha256'] in old['locator'] and a['observation_sha256'] in new['locator']


def test_confirmed_scope_sources_unchanged():
    p = read('gear-guide-t7-scope-fallback-correction.json'); S = {s['id']: s for s in read('gear-guide-t7-candidate.json')['sources']}
    assert [x['source_id'] for x in p['confirmed']] == ['bst:t7:scope-bg-ready:2026-11-05', 'pup:t7:scope-bg-maneuver:2026-11-05']
    assert S['bst:t7:scope-bg-ready:2026-11-05']['url'] == 'https://www.bg-wiki.com/ffxi/Ready'
    assert S['pup:t7:scope-bg-maneuver:2026-11-05']['url'] == 'https://www.bg-wiki.com/ffxi/Maneuver'
    assert p['classification_counts'] == dict(confirmed=2, label_attribution_defect=4, source_drift=0, source_limited=0)


def test_provenance_only_successors_keep_gear_and_retire_priors():
    c = read('gear-guide-t7-candidate.json'); R = {r['id']: r for r in c['revisions']}
    batch = next(a for a in c['authoring_amendments'] if a['id'] == 'scope-fallback-2026-11-05')['amendments']
    assert [a['set_id'] for a in batch] == ['nexus:pup:overdrive-sharpshot', 'nexus:bst:engaged-accuracy']
    for a in batch:
        old, new = R[a['retired_revision_id']], R[a['successor_revision_id']]
        assert new['slots'] == old['slots'] and new['verification'] == old['verification'] and new['version_order'] == old['version_order'] + 1
        assert max((r for r in c['revisions'] if r['set_id'] == a['set_id']), key=lambda r: r['version_order'])['id'] == new['id']
    sharp = R[batch[0]['successor_revision_id']]
    assert 'pup:fallback:automaton-actions:2026-11-05' in sharp['source_ids'] and 'pup:t7:scope-automaton-actions:2026-11-05' not in sharp['source_ids']
    acc = R[batch[1]['successor_revision_id']]
    assert 'bst:other27:grid:378247:2026-11-05' in acc['source_ids'] and 'bst:second-pass:slots:371161:2026-11-05' in acc['source_ids']
    assert {x['slot']: x['item_id'] for x in acc['slots'] if x['slot'] in ('ring1', 'ring2')} == {'ring1': 26182, 'ring2': 26182}


def test_effective_accounting_and_production_untouched():
    c = read('gear-guide-t7-candidate.json'); p = read('gear-guide-t7-scope-fallback-correction.json')
    retired = {x['retired_revision_id'] for a in c['authoring_amendments'] for x in a.get('amendments', [])}
    assert len(retired) == 27 and sum(r['verification']['status'] == 'verified' and r['id'] not in retired for r in c['revisions']) == 512
    assert sum(r['verification']['status'] == 'verified' for r in c['revisions']) == 539
    prod = Path(__file__).resolve().parents[2] / 'vanadiel_nexus/resources/gear_guides.json'
    fix = read('gear-guide-t7-production-duplicate-fix.json')
    assert p['production_sha256'] == fix['prior_sha256'] == '54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85'
    publication=read('gear-guide-t7-production-replacement.json')
    assert publication['prior_production_sha256']==fix['sha256']
    assert hashlib.sha256(prod.read_bytes()).hexdigest()==publication['production_sha256']
    assert p['new_resources'] == p['new_hands'] == p['new_requirements'] == 0
