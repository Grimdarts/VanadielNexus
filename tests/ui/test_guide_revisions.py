"""Fictional Qt/persistence integration; no player settings, inventory or Windower."""
from copy import deepcopy
import json
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtWidgets import QDialog

from vanadiel_nexus.core import gear_workspace as ws, gear_guides
from vanadiel_nexus.core.guide_catalog import validate_catalog
from vanadiel_nexus.core.item_res import Item


@pytest.fixture
def guide(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.core import windower
    from vanadiel_nexus.ui.context import AppContext
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    monkeypatch.setenv('VN_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr(windower, 'find_windower_dir', lambda *_: str(tmp_path / 'windower'))
    ctx = AppContext('fictional')
    ctx.inventory_snapshot = {'Alice': [{'character': 'Alice', 'item_id': 101, 'name': 'Fictional Ring',
                                         'count': 1, 'bag': 'Wardrobe 1'},
                                        {'character': 'Alice', 'item_id': 101, 'name': 'Fictional Ring',
                                         'count': 1, 'bag': 'Wardrobe 2'}], 'Bob': []}
    items = {101: Item(101, 'Fictional Ring', slots=1 << 13, jobs=1 << 5)}
    source = {'id': 'source', 'kind': 'ffxiah', 'url': 'https://www.ffxiah.com/item-sets/123',
              'title': 'Fictional composition', 'locator': 'Test row', 'accessed_on': '2026-11-03'}
    r1 = {'id': 'r1', 'set_id': 'idle', 'label': 'Test idle', 'equipment_version': 'Test tier',
          'version_order': 1, 'origin': 'source_adaptation', 'currency': 'older',
          'resource_fingerprint': 'fictional-v1',
          'verification': {'status': 'fixture-only', 'checked_on': '2026-11-03', 'scope': 'Fictional'},
          'source_ids': ['source'], 'assumptions': ['Test assumption'], 'rationale': 'Test rationale',
          'composition_kind': 'partial_loadout',
          'slots': [{'slot': 'ring1', 'state': 'selected', 'item_id': 101, 'requirements': {}},
                    {'slot': 'ring2', 'state': 'selected', 'item_id': 101, 'requirements': {}},
                    {'slot': 'head', 'state': 'empty'},
                    {'slot': 'body', 'state': 'unknown', 'diagnostic': 'Fictional unresolved source'}]}
    r1['verification']['status'] = 'unresolved'
    catalog = {'schema_version': 2, 'sources': [source], 'coverage': [],
               'sets': [{'id': 'idle', 'jobs': ['RDM'], 'purpose': 'Idle', 'target': 'Test idle',
                         'context': {'subjob': 'SCH'}, 'default_revision_id': 'r1'}], 'revisions': [r1]}
    catalog = validate_catalog(catalog, items=items, fixture=True)
    bags = [{'id': 8, 'en': 'Wardrobe', 'equippable': True},
            {'id': 10, 'en': 'Wardrobe 2', 'equippable': True},
            {'id': 11, 'en': 'Wardrobe 3', 'equippable': True}]
    store = ws.WorkspaceStore(tmp_path / 'data' / ws.BASENAME)
    page = GuidesPage(ctx, catalog=catalog, workspace=store, items=items, bags=bags)
    qtbot.addWidget(page)
    page.character_combo.setCurrentText('Alice')
    return page, ctx, catalog, store, items, bags


def rows(page):
    return {r['canonical_slot']: r for r in page.table.model_.rows}


def track(page):
    page.track_button.click()
    return page._target()


def add_revision(page, catalog, *, remove_old=False):
    new = deepcopy(catalog['revisions'][0])
    new.update(id='r2', currency='current', rationale='Updated independent evidence')
    new['slots'][0]['requirements'] = {'rank': 10}
    page.catalog = deepcopy(catalog)
    page.catalog['revisions'] = ([new] if remove_old else page.catalog['revisions'] + [new])
    page.catalog['sets'][0]['default_revision_id'] = 'r2'
    page._sets()


def test_navigation_read_only_and_slot_states(guide):
    page, ctx, _, store, *_ = guide
    original = deepcopy(ctx.db.data)
    page.refresh()
    assert not store.path.exists()
    assert ctx.db.data == original
    assert rows(page)['ring1']['status'] == 'Ready in snapshot'
    assert rows(page)['ring2']['status'] == 'Ready in snapshot'
    assert rows(page)['head']['status'] == 'Empty'
    assert rows(page)['body']['status'] == 'Unknown'
    assert rows(page)['feet']['status'] == 'Omitted'
    assert 'partial' in page.note.text().lower()


def test_track_uses_workspace_only_and_reopens_snapshot(guide, qtbot):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    page, ctx, catalog, store, items, bags = guide
    original = deepcopy(ctx.db.data)
    target = track(page)
    assert target['revision_id'] == 'r1'
    assert ctx.db.data == original
    assert not page.track_button.isEnabled()
    page._track()
    assert len(store.data['targets']) == 1
    reopened = GuidesPage(ctx, catalog=catalog, workspace=ws.WorkspaceStore(store.path), items=items, bags=bags)
    qtbot.addWidget(reopened)
    assert reopened._target()['id'] == target['id']
    assert reopened.workspace.data == store.data


def test_missing_snapshot_is_unverified_empty_complete_snapshot_is_missing(guide):
    page, ctx, *_ = guide
    track(page)
    ctx.inventory_snapshot = {}
    page.refresh()
    assert rows(page)['ring1']['status'] == 'Unverified'
    ctx.inventory_snapshot = {'Alice': []}
    page.refresh()
    assert rows(page)['ring1']['status'] == 'Missing'


def test_distinct_copies_bags_and_character_never_rebound(guide):
    page, ctx, _, store, *_ = guide
    target = track(page)
    proposal = store.data
    proposal['targets'][0]['bindings'] = [{'slot': 'ring1', 'bag_id': 8}, {'slot': 'ring2', 'bag_id': 10}]
    store.save(proposal)
    ctx.inventory_snapshot['Alice'][1]['bag'] = 'Wardrobe 3'
    page.refresh()
    assert rows(page)['ring1']['status'] == 'Ready in snapshot'
    assert rows(page)['ring2']['status'] == 'Owned · check bag'
    assert 'Wardrobe 3' in rows(page)['ring2']['detail']
    assert store.data['targets'][0]['bindings'][1]['bag_id'] == 10
    ctx.inventory_snapshot['Alice'].pop()
    page.refresh()
    assert sum(r['status'] == 'Ready in snapshot' for r in rows(page).values()) == 1
    page.character_combo.setCurrentText('Bob')
    assert page._target() is None
    assert rows(page)['ring1']['status'] == 'Missing'
    assert store.data['targets'][0]['id'] == target['id']


def test_adoption_cancel_navigation_and_explicit_save(guide, monkeypatch):
    from vanadiel_nexus.ui.guide_revisions import RevisionReview
    page, ctx, catalog, store, *_ = guide
    legacy_before = deepcopy(ctx.db.data)
    track(page)
    initial = store.path.read_bytes()
    add_revision(page, catalog)
    assert page._target()['revision_id'] == 'r1'
    assert 'available' in page.track_button.text().lower()
    page._version_picked(0)
    assert page.current_set['id'] == 'r2'
    assert store.path.read_bytes() == initial
    monkeypatch.setattr(RevisionReview, 'exec', lambda self: QDialog.Rejected)
    page.track_button.click()
    assert store.path.read_bytes() == initial
    monkeypatch.setattr(RevisionReview, 'exec', lambda self: QDialog.Accepted)
    page.track_button.click()
    assert page._target()['revision_id'] == 'r2'
    assert ws.WorkspaceStore(store.path).load().status == 'ok'
    assert ctx.db.data == legacy_before


def test_failed_adoption_keeps_memory_disk_and_pending_proposal(guide, monkeypatch):
    from vanadiel_nexus.ui.guide_revisions import RevisionReview
    page, _, catalog, store, *_ = guide
    track(page)
    initial = store.path.read_bytes()
    add_revision(page, catalog)
    monkeypatch.setattr(RevisionReview, 'exec', lambda self: QDialog.Accepted)
    def fail(*_):
        raise OSError('fictional disk full')
    monkeypatch.setattr(ws, '_write_temp', fail)
    page.track_button.click()
    page.refresh()
    assert store.path.read_bytes() == initial
    assert page._target()['revision_id'] == 'r1'
    assert store.pending['targets'][0]['revision_id'] == 'r2'
    assert 'disk full' in page.workspace_message.text()
    assert 'unchanged' in page.workspace_message.text()


def test_retired_snapshot_keeps_sources_context_and_requirements(guide):
    page, _, catalog, store, *_ = guide
    track(page)
    original = store.path.read_bytes()
    add_revision(page, catalog, remove_old=True)
    assert 'unavailable' in page.saved_state.text()
    assert page._revision_context()[0]['id'] == 'r1'
    assert page._revision_context()[1]['context'] == {'subjob': 'SCH'}
    assert page._revision_sources()[0]['title'] == 'Fictional composition'
    assert store.path.read_bytes() == original


def test_slot_editor_preserves_paired_requirement_and_curated_data(guide, monkeypatch):
    from vanadiel_nexus.ui.forms import FormDialog
    page, _, catalog, store, *_ = guide
    track(page)
    original = deepcopy(catalog)
    page.table.select_row(rows(page)['ring2'])
    monkeypatch.setattr(FormDialog, 'ask', lambda *a, **k: {
        'mode': 'Personal override', 'rank': 15, 'path': 'B', 'augments': 'A+1\nB+2', 'bag': 'Wardrobe 2'})
    page.edit_button.click()
    target = page._target()
    assert target['overrides'] == [{'slot': 'ring2', 'requirements': {'rank': 15, 'path': 'B', 'augments': ['A+1', 'B+2']}}]
    assert target['bindings'] == [{'slot': 'ring2', 'bag_id': 10}]
    assert rows(page)['ring1']['requirements'] == {}
    assert rows(page)['ring2']['requirements']['rank'] == 15
    assert catalog == original
    assert target['snapshot']['slots'][1]['requirements'] == {}


def test_source_routes_exact_revision_and_rejects_stale_menu(guide, monkeypatch):
    page, ctx, catalog, *_ = guide
    opened = []
    monkeypatch.setattr(ctx, 'open_url', opened.append)
    source = page._revision_sources()[0]
    key = page._source_key()
    page.source_button.click()
    assert opened == [source['url']]
    add_revision(page, catalog)
    page._open_revision_source(source, key)
    assert opened == [source['url']]
    bad = {**source, 'url': 'file:///private', 'kind': 'ffxiah'}
    page.catalog['sources'] = [bad]
    page._open_revision_source(bad, page._source_key())
    assert opened == [source['url']]


def test_mediawiki_permanent_link_keeps_exact_revision_and_fragment(guide, monkeypatch):
    from PySide6.QtGui import QDesktopServices
    page, _, catalog, *_ = guide
    url = 'https://www.bg-wiki.com/index.php?title=Community_White_Mage_Guide&oldid=781508#Idle_Sets'
    catalog['sources'][0].update(kind='bgwiki', url=url)
    page.catalog = catalog
    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda value: opened.append(value.toString()))
    page.source_button.click()
    assert opened == [url]


def test_options_are_references_and_cannot_be_tracked(guide):
    page, _, catalog, store, *_ = guide
    option = deepcopy(catalog['revisions'][0])
    option.update(composition_kind='equipment_options', options=[{'item_id': 101, 'requirements': {}}])
    option.pop('slots')
    page.catalog['revisions'] = [option]
    page._sets()
    assert page.table.model_.rows[0]['status'] == 'Reference option'
    assert not page.track_button.isEnabled()
    page._track()
    assert not store.path.exists()


def test_newer_workspace_is_read_only_and_not_repaired(guide, qtbot):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    page, ctx, catalog, store, items, bags = guide
    store.path.parent.mkdir(parents=True, exist_ok=True)
    newer = b'{"schema_version":99,"retained":"do not repair"}'
    store.path.write_bytes(newer)
    other = GuidesPage(ctx, catalog=catalog, workspace=ws.WorkspaceStore(store.path), items=items, bags=bags)
    qtbot.addWidget(other)
    assert not other.track_button.isEnabled()
    other._track()
    assert store.path.read_bytes() == newer
    assert 'read-only' in other.workspace_message.text()


def test_competing_writer_error_retains_pending_ui_proposal(guide):
    page, _, _, store, *_ = guide
    track(page)
    competitor = ws.WorkspaceStore(store.path)
    competitor.load()
    changed = competitor.data
    changed['targets'][0]['bindings'] = [{'slot': 'ring1', 'bag_id': 8}]
    competitor.save(changed)
    authoritative = store.path.read_bytes()
    proposed = store.data
    proposed['targets'][0]['bindings'] = [{'slot': 'ring2', 'bag_id': 10}]
    assert not page._save_workspace(proposed)
    assert store.path.read_bytes() == authoritative
    assert store.pending == proposed
    assert 'changed since load' in page.workspace_message.text()


def test_review_contains_context_requirements_sources_and_bindings(guide):
    from vanadiel_nexus.ui.guide_revisions import RevisionReview
    page, _, catalog, store, *_ = guide
    target = track(page)
    add_revision(page, catalog)
    _, delta = ws.prepare_adoption(store.data, target['id'], page.catalog, 'r2')
    dialog = RevisionReview(page, delta['before'], delta['after'])
    content = dialog.details.toPlainText()
    assert 'Rank ≥ 10' in content
    assert 'SCH' in content and 'Personal bags' in content and 'Fictional composition' in content
    assert 'Updated independent evidence' in content


def test_saved_target_survives_return_to_legacy_catalog(guide, qtbot):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    page, ctx, _, store, items, bags = guide
    target = track(page)
    legacy = GuidesPage(ctx, workspace=ws.WorkspaceStore(store.path), items=items, bags=bags)
    qtbot.addWidget(legacy)
    legacy.saved_combo.setCurrentIndex(legacy.saved_combo.findData(target['id']))
    assert legacy._target()['revision_id'] == 'r1'
    assert rows(legacy)['ring1']['status'] == 'Ready in snapshot'
    assert not legacy.track_button.isEnabled()


def test_unverified_bag_and_name_only_inventory_cannot_establish_readiness(guide):
    page, ctx, *_ = guide
    ctx.inventory_snapshot['Alice'][0]['bag'] = 'Invented equippable bag'
    ctx.inventory_snapshot['Alice'][1].pop('item_id')
    page.refresh()
    owned = [r for r in rows(page).values() if r['status'] == 'Owned · check bag']
    assert len(owned) == 1
    assert not any(r['status'] == 'Ready in snapshot' for r in rows(page).values())


def test_catalog_error_retains_inspectable_snapshot_and_blocks_mutation(guide, qtbot, monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    page, ctx, _, store, items, bags = guide
    target = track(page)
    original = store.path.read_bytes()
    def fail(**_):
        raise ValueError('fictional corrupt catalog')
    monkeypatch.setattr(gear_guides, 'load_catalog', fail)
    failed = GuidesPage(ctx, workspace=ws.WorkspaceStore(store.path), items=items, bags=bags)
    qtbot.addWidget(failed)
    failed.saved_combo.setCurrentIndex(failed.saved_combo.findData(target['id']))
    assert failed._target()['revision_id'] == 'r1'
    assert rows(failed)['ring1']['name'] == 'Fictional Ring'
    assert not failed.track_button.isEnabled() and not failed.edit_button.isEnabled()
    assert store.path.read_bytes() == original


def test_explicit_backup_recovery_preserves_unreadable_primary(guide, qtbot, monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    page, ctx, catalog, store, items, bags = guide
    target = track(page)
    store.backup.write_bytes(store.path.read_bytes())
    corrupt = b'fictional broken primary'
    store.path.write_bytes(corrupt)
    recovering = GuidesPage(ctx, catalog=catalog, workspace=ws.WorkspaceStore(store.path), items=items, bags=bags)
    qtbot.addWidget(recovering)
    assert recovering.workspace.result.status == 'recovery_available'
    assert not recovering.track_button.isEnabled()
    assert store.path.read_bytes() == corrupt
    monkeypatch.setattr(recovering, 'confirm', lambda *_: False)
    recovering._recover_workspace()
    assert store.path.read_bytes() == corrupt
    monkeypatch.setattr(recovering, 'confirm', lambda *_: True)
    recovering._recover_workspace()
    assert recovering.workspace.result.status == 'ok'
    assert recovering.workspace.data['targets'][0]['id'] == target['id']
    assert any(p.read_bytes() == corrupt for p in store.path.parent.glob('*.evidence'))


def test_revision_conflict_is_visible_and_saved_snapshot_wins(guide):
    page, _, _, store, *_ = guide
    track(page)
    original = store.path.read_bytes()
    page.catalog['revisions'][0]['rationale'] = 'Conflicting same revision'
    page.refresh()
    assert 'conflicts' in page.saved_state.text()
    assert not page.edit_button.isEnabled()
    assert not page.track_button.isEnabled()
    assert page._revision_context()[0]['rationale'] == 'Test rationale'
    assert store.path.read_bytes() == original


def test_removed_bound_slot_blocks_adoption_without_dropping_personal_choices(guide):
    page, _, catalog, store, *_ = guide
    track(page)
    proposal = store.data
    proposal['targets'][0]['bindings'] = [{'slot': 'ring2', 'bag_id': 10}]
    store.save(proposal)
    original = store.path.read_bytes()
    add_revision(page, catalog)
    page.catalog['revisions'][-1]['slots'] = [r for r in page.catalog['revisions'][-1]['slots'] if r['slot'] != 'ring2']
    page.track_button.click()
    assert 'reconciliation' in page.workspace_message.text()
    assert store.path.read_bytes() == original
    assert page._target()['bindings'] == [{'slot': 'ring2', 'bag_id': 10}]


def test_multi_source_chooser_uses_specific_titles_and_selection_guard(guide, monkeypatch):
    from PySide6.QtWidgets import QMenu
    from vanadiel_nexus.ui import guide_revisions
    page, ctx, _, *_ = guide
    page.catalog['sources'].append({**page.catalog['sources'][0], 'id': 'other-source',
                                    'title': 'Additional evidence', 'locator': 'Independent row',
                                    'url': 'https://www.ffxiah.com/item-sets/456'})
    page.current_set['source_ids'].append('other-source')
    opened, labels = [], []
    monkeypatch.setattr(ctx, 'open_url', opened.append)
    class CapturedMenu(QMenu):
        def exec(self, *_):
            labels.extend(a.text() for a in self.actions())
            self.actions()[1].trigger()
    monkeypatch.setattr(guide_revisions, 'QMenu', CapturedMenu)
    page.source_button.click()
    assert 'Additional evidence · Independent row' in labels
    assert opened == ['https://www.ffxiah.com/item-sets/456']


def test_compact_layout_renders_actual_qt_page(guide, qtbot, tmp_path):
    from vanadiel_nexus.ui import theme
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
    page, *_ = guide
    track(page)
    # Offscreen Qt does not enumerate native Windows fonts in this sandbox.
    # Register the installed font explicitly for a readable visual artifact.
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    theme.apply(QApplication.instance())
    page.show()
    for width, height in ((1024, 768), (900, 600)):
        page.resize(width, height)
        QApplication.processEvents()
        assert page.width() == width
        assert page.table.height() >= 140
        assert page.track_button.geometry().right() < width
        assert page.grab().save(str(tmp_path / f'guide-t4-{width}.png'))


def test_selection_change_during_adoption_review_cannot_save_stale_proposal(guide, monkeypatch):
    from vanadiel_nexus.ui.guide_revisions import RevisionReview
    page, _, catalog, store, *_ = guide
    track(page)
    original = store.path.read_bytes()
    add_revision(page, catalog)
    def changed(dialog):
        page.character_combo.setCurrentText('Bob')
        return QDialog.Accepted
    monkeypatch.setattr(RevisionReview, 'exec', changed)
    page.track_button.click()
    assert store.path.read_bytes() == original
    assert 'changed during review' in page.workspace_message.text()


# --- Runtime retirement (GEAR-GUIDE-T7-RUNTIME-RETIREMENT-DESIGN.md section 6, tests 8-14) ---

def _retired_revision(rid, set_id, order, ring1_augments):
    return {'id': rid, 'set_id': set_id, 'label': 'Fictional ' + set_id, 'equipment_version': 'Same tier',
            'version_order': order, 'origin': 'nexus_recommendation', 'currency': 'current',
            'resource_fingerprint': 'fictional-v1',
            'verification': {'status': 'fixture-only', 'checked_on': '2026-11-05', 'scope': 'Fictional'},
            'source_ids': ['source'], 'assumptions': ['Fictional'], 'rationale': 'Rationale ' + rid,
            'composition_kind': 'partial_loadout',
            'slots': [{'slot': 'ring1', 'state': 'selected', 'item_id': 101,
                       'requirements': {'augments': ring1_augments} if ring1_augments else {}},
                      {'slot': 'ring2', 'state': 'selected', 'item_id': 101, 'requirements': {}}]}


def _retired_catalog():
    source = {'id': 'source', 'kind': 'ffxiah', 'url': 'https://www.ffxiah.com/item-sets/123',
              'title': 'Fictional composition', 'locator': 'Test row', 'accessed_on': '2026-11-05'}
    sets = [{'id': key, 'jobs': ['RDM'], 'purpose': 'Idle', 'target': title, 'context': {}}
            for key, title in (('aug', 'Augment fix'), ('cite', 'Citation fix'), ('chain', 'Chain fix'))]
    revisions = [_retired_revision('aug:v1', 'aug', 1, ['DEX+30']),
                 _retired_revision('aug:v2', 'aug', 2, ['DEX+20', 'AGI+10']),
                 _retired_revision('cite:v1', 'cite', 1, None), _retired_revision('cite:v2', 'cite', 2, None),
                 _retired_revision('chain:v1', 'chain', 1, None), _retired_revision('chain:v2', 'chain', 2, None),
                 _retired_revision('chain:v3', 'chain', 3, None)]

    def fix(retired, successor):
        return {'set_id': retired.split(':')[0], 'retired_revision_id': retired,
                'successor_revision_id': successor, 'reason': 'Fictional correction'}
    return {'schema_version': 2, 'sources': [source], 'coverage': [], 'sets': sets, 'revisions': revisions,
            'authoring_amendments': [
                {'id': 'brd-augment-parts-2026-11-04', 'amendments': [fix('aug:v1', 'aug:v2')]},
                {'id': 'bst-provenance-2026-11-05', 'amendments': [fix('cite:v1', 'cite:v2'),
                                                                   fix('chain:v1', 'chain:v2')]},
                {'id': 'bst-ear-labels-2026-11-05', 'amendments': [fix('chain:v2', 'chain:v3')]}]}


@pytest.fixture
def retired(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.core import windower
    from vanadiel_nexus.ui.context import AppContext
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    monkeypatch.setenv('VN_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr(windower, 'find_windower_dir', lambda *_: str(tmp_path / 'windower'))
    ctx = AppContext('fictional')
    ctx.inventory_snapshot = {'Alice': [{'character': 'Alice', 'item_id': 101, 'name': 'Fictional Ring',
                                         'count': 1, 'bag': 'Wardrobe 1'},
                                        {'character': 'Alice', 'item_id': 101, 'name': 'Fictional Ring',
                                         'count': 1, 'bag': 'Wardrobe 2'}]}
    items = {101: Item(101, 'Fictional Ring', slots=1 << 13, jobs=1 << 5)}
    bags = [{'id': 8, 'en': 'Wardrobe', 'equippable': True},
            {'id': 10, 'en': 'Wardrobe 2', 'equippable': True}]
    catalog = validate_catalog(_retired_catalog(), items=items, fixture=True)
    store = ws.WorkspaceStore(tmp_path / 'data' / ws.BASENAME)

    def open_page(*, saved=(), picks=None, loader=None):
        if saved:
            targets = []
            for n, rid in enumerate(saved):
                target = ws.prepare_target(catalog, rid, target_id=f't{n}', character_key='Alice',
                                           bindings=[{'slot': 'ring2', 'bag_id': 10}])
                targets.append(target)
            store.load()
            store.save({**ws.empty_workspace(), 'targets': targets})
        if picks is not None:
            ctx.settings.set('guide_picks', picks)
        ctx.settings.set('guide_character', 'Alice')
        if loader:
            monkeypatch.setattr(gear_guides, 'load_catalog', loader)
        page = (GuidesPage(ctx, workspace=ws.WorkspaceStore(store.path), items=items, bags=bags) if loader else
                GuidesPage(ctx, catalog=catalog, workspace=ws.WorkspaceStore(store.path), items=items, bags=bags))
        qtbot.addWidget(page)
        page.character_combo.setCurrentText('Alice')
        return page

    return open_page, ctx, catalog, store


def show_set(page, set_id):
    page.purpose_combo.setCurrentIndex(page.purpose_combo.findData('Idle'))
    page.target_combo.setCurrentIndex(page.target_combo.findData(set_id))
    assert page.target_combo.currentData() == set_id


# 8
def test_opening_a_retired_set_selects_the_effective_revision_without_pills(retired):
    open_page, *_ = retired
    page = open_page()
    assert page.purpose_combo.currentText() == 'Idle (3)'
    for set_id, head in (('aug', 'aug:v2'), ('cite', 'cite:v2'), ('chain', 'chain:v3')):
        show_set(page, set_id)
        assert page.current_set['id'] == head
        assert page.version_group.buttons() == [] and page.versions.isHidden()
        assert page.retired_banner.isHidden()


# 9
def test_remembered_retired_choice_opens_effective_head_and_writes_nothing(retired):
    open_page, ctx, *_ = retired
    picks = {'RDM': {'purpose': 'Idle', 'target': 'aug', 'versions': {'aug': 'aug:v1'}}}
    ctx.settings.set('guide_picks', picks)
    ctx.settings.set('guide_character', 'Alice')
    before = open(ctx.settings.path, 'rb').read()
    page = open_page()
    assert page.target_combo.currentData() == 'aug'
    assert page.current_set['id'] == 'aug:v2'
    assert ctx.settings.get('guide_picks') == picks
    assert open(ctx.settings.path, 'rb').read() == before


# 10
def test_saved_retired_target_shows_banner_outdated_suffix_review_and_no_edit(retired):
    open_page, *_ = retired
    page = open_page(saved=['aug:v1'])
    show_set(page, 'aug')
    assert page._target()['revision_id'] == 'aug:v1'
    banner = page.retired_banner.text()
    assert not page.retired_banner.isHidden()
    assert banner.startswith('Outdated guide revision. This saved target uses aug:v1, replaced on 2026-11-04 by aug:v2:')
    assert 'augment requirements corrected to the exact in-game augment text; the gear is the same.' in banner
    assert banner.endswith('Review the update to switch; your saved choices are kept.')
    assert page.retired_banner.property('tone') == 'warning'
    assert page.saved_combo.currentText().endswith(' · outdated')
    assert page.track_button.text() == 'Review update…' and page.track_button.isEnabled()
    assert not page.edit_button.isEnabled()
    assert 'Review the update first' in page.edit_button.toolTip()


# 11
def test_changed_requirement_slot_is_outdated_never_graded(retired):
    open_page, *_ = retired
    page = open_page(saved=['aug:v1', 'cite:v1'])
    show_set(page, 'aug')
    ring1, ring2 = rows(page)['ring1'], rows(page)['ring2']
    assert ring1['status'] == 'Outdated requirement'
    assert ring1['status'] not in ('Missing', 'Upgrade / verify', 'Owned · check bag', 'Ready in snapshot')
    assert ring1['requirement'].startswith('DEX+30')
    assert ring1['detail'] == 'Requirement changed in the current revision; review the update to compare correctly.'
    assert ring2['status'] == 'Ready in snapshot'
    show_set(page, 'cite')
    assert page._target()['revision_id'] == 'cite:v1'
    assert {r['status'] for k, r in rows(page).items() if k in ('ring1', 'ring2')} == {'Ready in snapshot'}
    assert 'citations corrected; the gear and requirements are the same.' in page.retired_banner.text()


def test_personal_override_on_changed_slot_is_graded_and_shown(retired):
    open_page, _, catalog, store = retired
    target = ws.prepare_target(catalog, 'aug:v1', target_id='t0', character_key='Alice')
    target['overrides'] = [{'slot': 'ring1', 'requirements': {'rank': 3}}]
    store.load()
    store.save({**ws.empty_workspace(), 'targets': [target]})
    page = open_page()
    show_set(page, 'aug')
    ring1 = rows(page)['ring1']
    assert ring1['status'] == 'Upgrade / verify'
    assert ring1['requirement'].startswith('Rank ≥ 3')


def test_browsing_with_an_outdated_saved_target_still_warns(retired):
    open_page, *_ = retired
    page = open_page(saved=['aug:v1'])
    show_set(page, 'aug')
    page._browse_revision()
    page.refresh()
    assert page._target() is None and page.current_set['id'] == 'aug:v2'
    assert not page.retired_banner.isHidden() and 'aug:v1' in page.retired_banner.text()
    assert page.track_button.text() == 'Review update…' and page.track_button.isEnabled()
    assert page._revision_update(page._matching_target())['id'] == 'aug:v2'


# 12
def test_accepting_review_saves_effective_head_and_cancel_changes_nothing(retired, monkeypatch):
    from vanadiel_nexus.ui.guide_revisions import RevisionReview
    open_page, _, _, store = retired
    page = open_page(saved=['aug:v1'])
    show_set(page, 'aug')
    original = store.path.read_bytes()
    monkeypatch.setattr(RevisionReview, 'exec', lambda self: QDialog.Rejected)
    page.track_button.click()
    assert store.path.read_bytes() == original
    monkeypatch.setattr(RevisionReview, 'exec', lambda self: QDialog.Accepted)
    page.track_button.click()
    store.load()  # the page wrote through its own store; reread the file
    saved = store.data['targets'][0]
    assert saved['revision_id'] == 'aug:v2' and saved['id'] == 't0'
    assert saved['bindings'] == [{'slot': 'ring2', 'bag_id': 10}]
    assert page.retired_banner.isHidden()
    assert not page.saved_combo.currentText().endswith(' · outdated')
    assert rows(page)['ring1']['status'] == 'Upgrade / verify'


# 13
def test_chain_reviews_straight_to_the_head(retired, monkeypatch):
    from vanadiel_nexus.ui.guide_revisions import RevisionReview
    open_page, _, _, store = retired
    page = open_page(saved=['chain:v1'])
    show_set(page, 'chain')
    assert 'replaced on 2026-11-05 by chain:v3' in page.retired_banner.text()
    reviewed = []
    original_init = RevisionReview.__init__

    def capture(self, parent, before, after):
        reviewed.append((before['revision_id'], after['revision_id']))
        original_init(self, parent, before, after)
    monkeypatch.setattr(RevisionReview, '__init__', capture)
    monkeypatch.setattr(RevisionReview, 'exec', lambda self: QDialog.Accepted)
    page.track_button.click()
    assert reviewed == [('chain:v1', 'chain:v3')]
    store.load()
    assert store.data['targets'][0]['revision_id'] == 'chain:v3'


# 14
def test_malformed_amendment_is_a_catalog_error_and_snapshots_stay_inspectable(retired):
    open_page, _, catalog, store = retired
    bad = _retired_catalog()
    bad['authoring_amendments'][0]['amendments'][0]['successor_revision_id'] = 'aug:missing'
    items = {101: Item(101, 'Fictional Ring', slots=1 << 13, jobs=1 << 5)}

    def loader(**_):
        return validate_catalog(deepcopy(bad), items=items, fixture=True)
    targets = [ws.prepare_target(catalog, 'aug:v1', target_id='t0', character_key='Alice')]
    store.load()
    store.save({**ws.empty_workspace(), 'targets': targets})
    original = store.path.read_bytes()
    page = open_page(loader=loader)
    assert page.catalog_error and 'aug:missing' in page.catalog_error
    page.saved_combo.setCurrentIndex(page.saved_combo.findData('t0'))
    assert page._target()['revision_id'] == 'aug:v1'
    assert rows(page)['ring1']['name'] == 'Fictional Ring'
    assert not page.track_button.isEnabled() and not page.edit_button.isEnabled()
    assert store.path.read_bytes() == original
