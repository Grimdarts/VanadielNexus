"""Portable T7 evidence fixtures; no player persistence or installed resources."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from vanadiel_nexus.core import equipment_effects as effects, gear_guides, item_res
from vanadiel_nexus.core.equipment_hands import EVIDENCE, hand_types
from vanadiel_nexus.core.guide_catalog import CatalogError, JOBS, composition_diagnostics
from tools import prepare_guide_catalog as authoring


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'docs/catalog'


@pytest.fixture
def packet():
    metadata = json.loads((PACKET / 'gear-guide-t7-resource-evidence.json').read_text(encoding='utf-8'))
    items = {row['id']: item_res.Item(**row) for row in metadata['items']}
    return effects.SourceSnapshot('fictional-resources', (), metadata['fingerprint'],
                                  MappingProxyType(items), MappingProxyType({}), hand_types=hand_types(items))


def selected(slot, item_id):
    return dict(slot=slot, state='selected', item_id=item_id, requirements={})


def test_reviewed_hand_pairs_and_invalid_source_pair(packet):
    hands = packet.hand_types
    assert hands[22040] == 'one_handed' and hands[27645] == 'shield'
    assert hands[22100] == 'two_handed' and hands[22218] == 'grip'
    assert hands[20515] == hands[21527] == 'hand_to_hand'
    for main, sub, job in [(22040, 27645, 'WHM'), (22100, 22218, 'SCH')]:
        slots = [selected('main', main), selected('sub', sub)]
        assert not composition_diagnostics(slots, packet.items, [job], hand_types=hands)
        assert not effects.evaluate(slots, packet, job=job).diagnostics
    illegal = [selected('main', 22064), selected('sub', 27635)]
    assert composition_diagnostics(illegal, packet.items, ['SCH'], hand_types=hands) == ['main/sub: incompatible equipment']
    result = effects.evaluate(illegal, packet, job='SCH')
    assert not result.contributions and result.diagnostics
    with pytest.raises(TypeError):
        hands[1] = 'grip'


@pytest.mark.parametrize('change', [dict(id=999999), dict(en='Different'), dict(skill=12),
                                  dict(slots=1), dict(category='Armor'), dict(shield_size=1)])
def test_changed_or_unreviewed_resource_cannot_inherit_type(packet, change):
    changed = replace(packet.items[22040], **change)
    assert not hand_types({changed.id: changed})


def test_explicit_empty_override_and_unknown_hand_remain_fail_closed(packet):
    pair = [selected('main', 22040), selected('sub', 27645)]
    assert effects.evaluate(pair, packet, job='WHM', hand_types={}).diagnostics
    changed = replace(packet.items[22040], id=999999)
    items = {**packet.items, changed.id: changed}
    assert composition_diagnostics([selected('main', changed.id), selected('sub', 27645)], items,
                                   ['WHM'], hand_types=hand_types(items)) == ['main/sub: unresolved weapon legality']
    pair = [selected('main', 20515), selected('sub', 27645)]
    assert 'main/sub: incompatible equipment' in composition_diagnostics(pair, packet.items, ['MNK'], hand_types=packet.hand_types)


def test_resource_reader_and_worker_retain_classification_without_gui_scan(tmp_path):
    folder = tmp_path / 'res'
    folder.mkdir()
    (folder / 'items.lua').write_text(
        '[22040] = {id=22040,en="Daybreak",category="Weapon",slots=3,jobs=8,skill=11},\n'
        '[27645] = {id=27645,en="Genmei Shield",category="Armor",slots=2,jobs=8,shield_size=1},\n', encoding='utf-8')
    (folder / 'item_descriptions.lua').write_text('[22040] = {id=22040,en="Uninspected text"},\n', encoding='utf-8')
    items = item_res.items(str(tmp_path))
    assert items[22040].skill == 11 and items[27645].shield_size == 1
    source = effects.prepare_source(tmp_path)
    assert dict(source.hand_types) == {22040:'one_handed', 27645:'shield'}
    with pytest.raises(TypeError):
        source.hand_types[22040] = 'two_handed'


def test_entire_authoring_packet_retains_gaps_omissions_and_exact_copies(packet):
    raw = (PACKET / 'gear-guide-t7-candidate.json').read_text(encoding='utf-8')
    catalog = authoring.prepare(raw, packet)
    report = authoring.summary(catalog)
    assert report['revisions'] == 547 and report['coverage_rows'] == 231 and report['open_priorities'] == 0
    assert report['verified_revisions'] == 539 and report['unresolved_revisions'] == 8
    assert len(report['jobs_with_revisions']) == 22
    assert {r['job'] for r in catalog['coverage']} == set(JOBS)
    included = [r for r in catalog['coverage'] if r['status'] == 'included']
    assert len(included) == 231 and {r['job'] for r in included} == {'WHM', 'SCH', 'BLM', 'RDM', 'GEO', 'BRD', 'RNG', 'SAM', 'NIN', 'SMN', 'BLU', 'COR', 'RUN', 'PLD', 'DRK', 'WAR', 'MNK', 'THF', 'DRG', 'BST', 'PUP', 'DNC'}
    assert all(r['status'] == 'gap' for r in catalog['coverage'] if r['job'] not in ('WHM', 'SCH', 'BLM', 'RDM', 'GEO', 'BRD', 'RNG', 'SAM', 'NIN', 'SMN', 'BLU', 'COR', 'RUN', 'PLD', 'DRK', 'WAR', 'MNK', 'THF', 'DRG', 'BST', 'PUP', 'DNC'))
    assert not any('default_revision_id' in group for group in catalog['sets'])
    revisions = {r['set_id']:r for r in catalog['revisions']}
    dnc = revisions['ffxiah:367871:dnc']['slots']
    assert sum(s['item_id'] == 26190 for s in dnc) == 2 and len(dnc) == 10
    cor = revisions['ffxiah:357015:cor']['slots']
    assert sum(s['item_id'] == 26184 for s in cor) == 2 and len(cor) == 5
    assert next(s for s in cor if s['slot'] == 'legs')['requirements'] == {'path':'D'}
    assert 'range' not in {s['slot'] for s in revisions['ffxiah:373999:whm']['slots']}
    observations = json.loads((PACKET / 'gear-guide-t7-observations.json').read_text(encoding='utf-8'))
    for row in observations['observations']:
        stamp = row.pop('observation_sha256')
        assert hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == stamp
        revision = revisions[f'ffxiah:{row["external_set_id"]}:{row["job"].lower()}']
        assert revision['observation_sha256'] == stamp
        assert {s['slot']:s['name'] for s in revision['slots']} == row['selected_names']


def test_v2_loader_uses_same_reviewed_hands(packet, monkeypatch):
    monkeypatch.setattr(gear_guides, 'resource_path', lambda _: str(PACKET / 'gear-guide-t7-candidate.json'))
    monkeypatch.setattr(item_res, 'items', lambda _: packet.items)
    assert len(gear_guides.load_catalog(windower_dir='fictional')['revisions']) == 547


def test_bad_candidate_failed_replace_and_immutable_edit_preserve_artifact(packet, tmp_path, monkeypatch):
    raw = (PACKET / 'gear-guide-t7-candidate.json').read_text(encoding='utf-8')
    path = tmp_path / 'candidate.json'
    authoring.save_candidate(path, raw, packet)
    before = path.read_bytes()
    bad = json.loads(raw)
    bad['revisions'][0]['slots'][0]['item_id'] = 999999
    with pytest.raises(CatalogError):
        authoring.save_candidate(path, json.dumps(bad), packet)
    assert path.read_bytes() == before
    changed = json.loads(raw)
    changed['revisions'][0]['rationale'] = 'Overwrite immutable history'
    with pytest.raises(CatalogError, match='immutable'):
        authoring.save_candidate(path, json.dumps(changed), packet)
    assert path.read_bytes() == before
    def fail(*_):
        raise OSError('Fictional interrupted replace')
    monkeypatch.setattr(authoring.os, 'replace', fail)
    with pytest.raises(OSError, match='interrupted'):
        authoring.save_candidate(path, raw, packet)
    assert path.read_bytes() == before and not list(tmp_path.glob('*.tmp'))


def test_new_resource_revisions_retain_old_fingerprint_and_history(packet, tmp_path):
    raw = (PACKET / 'gear-guide-t7-candidate.json').read_text(encoding='utf-8')
    path = tmp_path / 'candidate.json'
    authoring.save_candidate(path, raw, packet)
    newer = replace(packet, fingerprint='fictional-new-snapshot')
    value = json.loads(raw)
    revision = deepcopy(value['revisions'][0])
    revision.update(id='new-revision', resource_fingerprint=newer.fingerprint)
    value['revisions'].append(revision)
    authoring.save_candidate(path, json.dumps(value), newer)
    result = json.loads(path.read_text(encoding='utf-8'))
    assert result['revisions'][0]['resource_fingerprint'] == packet.fingerprint
    before = path.read_bytes()
    value['revisions'] = value['revisions'][1:]
    with pytest.raises(ValueError, match='historical'):
        authoring.save_candidate(path, json.dumps(value), newer)
    assert path.read_bytes() == before


def test_fingerprint_mismatch_and_production_destination_are_rejected(packet, tmp_path):
    raw = (PACKET / 'gear-guide-t7-candidate.json').read_text(encoding='utf-8')
    with pytest.raises(ValueError, match='fingerprint'):
        authoring.prepare(raw, replace(packet, fingerprint='different'))
    with pytest.raises(ValueError, match='production bundle'):
        authoring.save_candidate(ROOT / 'vanadiel_nexus/resources/gear_guides.json', raw, packet)
    with pytest.raises(ValueError, match='read-only'):
        authoring.save_candidate(Path(packet.root) / 'anything.json', raw, packet)
    assert len(EVIDENCE) == 55 and all(r.checked_on and r.url and r.locator for r in EVIDENCE)

