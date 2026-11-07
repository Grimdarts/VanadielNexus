"""The Sets page with read_job replaced by canned results: no Lua runs here."""
import os
import shutil
import threading
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

from vanadiel_nexus.core import gearswap_files, gearswap_reader  # noqa: E402
from vanadiel_nexus.core.gearswap_reader import JobRead, Piece, SetRead  # noqa: E402

FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'gearswap'


def piece(slot, name, **kw):
    return Piece(slot=slot, original_key=slot, name=name, **kw)


def job_read(character='Alice', job='BLU', sub='', **kw):
    sets = [
        SetRead('sets.Idle.Standard', ['Idle', 'Standard'], {'head': piece('head', 'Hashishin Kavuk +2')}),
        SetRead('sets.SavageBlade.Attack', ['SavageBlade', 'Attack'], {
            'head': piece('head', 'Hashishin Kavuk +2'),
            'ring1': piece('ring1', 'Sroda Ring'),
            'ring2': piece('ring2', 'Sroda Ring'),
            'neck': piece('neck', 'Fotia Gorget'),
            'body': piece('body', 'Nyame Mail'),
            'hands': piece('hands', 'Nyame Gauntlets'),
            'legs': piece('legs', 'Nyame Flanchard'),
            'feet': Piece(slot='feet', original_key='feet', empty=True),
        }, aliases=['sets.savage']),
        SetRead('sets.Blank', ['Blank'], {}, empty_in_file=True),
    ]
    defaults = dict(sets=sets, read_at=1.0)
    defaults.update(kw)
    return JobRead(character, job, sub, f'C:/x/{character}_{job}.lua', False, {}, **defaults)


def row(item_id, name, bag='Wardrobe 3', character='Alice'):
    return {'item_id': item_id, 'name': name, 'bag': bag, 'augments': '', 'count': 1, 'character': character}


class FakeReader:
    def __init__(self):
        self.calls = []
        self.results = {}
        self.gate = None

    def __call__(self, windower_dir, character, job, sub_job='', force=False, **_kw):
        self.calls.append((character, job, sub_job, force))
        if self.gate is not None:
            self.gate.wait(5)
        result = self.results.get(job)
        return result if result is not None else job_read(character, job, sub_job)


@pytest.fixture
def setup(qtbot, tmp_path, monkeypatch):
    tree = tmp_path / 'Windower'
    shutil.copytree(FIXTURE, tree)
    data = tree / 'addons' / 'GearSwap' / 'data'
    data.mkdir(parents=True, exist_ok=True)  # empty folder named data/ isn't in git (.gitignore)
    (data / 'Alice_BLU.lua').write_text('-- test', encoding='utf-8')
    (data / 'Alice_RUN.lua').write_text('-- test', encoding='utf-8')
    (data / 'Bob_SMN.lua').write_text('-- test', encoding='utf-8')
    monkeypatch.setenv('VN_DATA_DIR', str(tmp_path / 'data'))
    fake = FakeReader()
    monkeypatch.setattr(gearswap_reader, 'read_job', fake)
    from vanadiel_nexus import __version__
    from vanadiel_nexus.ui.context import AppContext
    ctx = AppContext(__version__)
    ctx.windower_dir = str(tree)
    ctx.inventory_snapshot = {'Alice': [row(23100, 'Hashishin Kavuk +2'), row(23110, 'Sroda Ring', 'Mog Safe 1'),
                                        row(23106, 'Fotia Gorget')]}
    ctx.bridge.state = {}
    return ctx, fake


def make_page(qtbot, ctx, show=True):
    from vanadiel_nexus.ui.pages.sets import SetsPage
    page = SetsPage(ctx)
    qtbot.addWidget(page)
    page.resize(1100, 760)
    if show:
        page.show()
        page.on_shown()
        wait(qtbot, page)
    return page


def wait(qtbot, page):
    qtbot.waitUntil(lambda: not page._busy and page.read is not None, timeout=5000)


def test_sets_comes_right_after_gear_in_the_sidebar():
    from vanadiel_nexus.ui.main_window import NAV
    from vanadiel_nexus.ui.pages.gear import GearPage
    from vanadiel_nexus.ui.pages.sets import SetsPage
    assert [cls for _icon, cls in NAV][:2] == [GearPage, SetsPage]


def test_construction_does_no_io_and_first_show_reads_once(qtbot, setup, monkeypatch):
    ctx, fake = setup
    looked = []
    real_find = gearswap_files.find_job_file
    monkeypatch.setattr(gearswap_files, 'find_job_file', lambda *a, **k: looked.append(a) or real_find(*a, **k))
    page = make_page(qtbot, ctx, show=False)
    assert looked == [] and fake.calls == [] and page.character_combo.count() == 0
    page.show()
    page.on_shown()
    wait(qtbot, page)
    assert fake.calls == [('Alice', 'BLU', '', False)]


def test_pickers_list_file_only_characters_and_disable_jobs_without_a_file(qtbot, setup):
    ctx, _fake = setup
    page = make_page(qtbot, ctx)
    names = [page.character_combo.itemText(i) for i in range(page.character_combo.count())]
    assert names == ['Alice', 'Bob']  # Bob has a job file but no snapshot
    model = page.job_combo.model()
    enabled = {page.job_combo.itemData(i): model.item(i).isEnabled() for i in range(page.job_combo.count())}
    assert enabled['BLU'] and enabled['RUN'] and not enabled['SMN'] and not enabled['WAR']
    assert page.job_combo.itemText(page.job_combo.findData('WAR')) == 'WAR (no file)'
    assert 'All' not in enabled


def test_grid_tree_header_and_needs_attention(qtbot, setup):
    ctx, _fake = setup
    page = make_page(qtbot, ctx)
    assert page.current_path == 'sets.SavageBlade.Attack'  # the first set needing attention is auto-selected
    grid = page.grid
    assert grid.cell('head').state == 'owned' and grid.cell('head').caption == 'Wardrobe 3'
    assert grid.cell('ring1').state == 'unreachable' and grid.cell('ring1').caption == '⚠ Mog Safe 1'
    assert grid.cell('ring2').state == 'missing' and grid.cell('ring2').caption == 'only 1 owned'
    assert grid.cell('feet').state == 'empty' and grid.cell('main').state == 'not_set'
    assert page.verdict.text() == '⚠ 5 need attention'
    assert page.path_label.text() == 'SavageBlade.Attack · also called savage'
    assert page.set_caption.text() == 'Weapon skill · Alice_BLU.lua · 8/16 set'
    rows = [r for r in page.attention_rows if not r.isHidden()]
    assert len(rows) == 4 and page.more_label.text() == '+1 more' and not page.more_label.isHidden()
    assert [r.text() for r in rows] == [  # grid order
        'Body: Nyame Mail: not owned.', 'Hands: Nyame Gauntlets: not owned.',
        "Ring 1: Sroda Ring is in Mog Safe 1. GearSwap can't equip it from there.", 'Ring 2: Sroda Ring: only 1 owned.']
    rows[3].clicked.emit()
    assert grid.selected() == 'ring2' and page.panel_slot.text() == 'Ring 2'


def test_tree_groups_aliases_and_empty_sets(qtbot, setup):
    ctx, _fake = setup
    page = make_page(qtbot, ctx)
    groups = [page.tree.topLevelItem(i).text(0) for i in range(page.tree.topLevelItemCount())]
    assert groups == ['Idle (1)', 'Weapon skill (1)', 'Other (1)']
    ws = page.tree.topLevelItem(1)
    assert [ws.child(i).text(0) for i in range(ws.childCount())] == ['SavageBlade.Attack', '↪ savage']
    assert ws.child(0).text(1) == '⚠ 5'
    assert page.tree.topLevelItem(2).child(0).text(0) == 'Blank (empty in file)'
    page.tree.setCurrentItem(page.tree.topLevelItem(0).child(0))
    assert page.current_path == 'sets.Idle.Standard' and page.verdict.text() == '✓ All pieces owned'
    page.tree.setCurrentItem(ws.child(1))  # an alias row selects its canonical set
    assert page.tree.currentItem() is ws.child(0) and page.current_path == 'sets.SavageBlade.Attack'


def test_search_matches_items_and_shows_no_match_with_clear(qtbot, setup):
    ctx, _fake = setup
    page = make_page(qtbot, ctx)
    page.toolbar.search.setText('fotia')
    visible = [page.tree.topLevelItem(i).text(0) for i in range(page.tree.topLevelItemCount())
               if not page.tree.topLevelItem(i).isHidden()]
    assert visible == ['Weapon skill (1)']
    page.toolbar.search.setText('savage')
    assert not page.tree.topLevelItem(1).child(1).isHidden()  # aliases match too
    page.toolbar.search.setText('zzz')
    assert page.no_match.isVisibleTo(page) and not page.tree.isVisibleTo(page)
    assert page.no_match_label.text() == 'No set or item matches "zzz"'
    page.toolbar.search.clear()
    assert page.tree.isVisibleTo(page) and not page.no_match.isVisibleTo(page)


def test_partial_read_shows_the_amber_strip(qtbot, setup):
    ctx, fake = setup
    fake.results['BLU'] = job_read(error='Alice_BLU.lua:9: boom', error_details='traceback', partial=True)
    page = make_page(qtbot, ctx)
    assert page.body.currentWidget() is page.workspace
    assert page.strip.isVisibleTo(page) and page.strip_label.text() == 'Read incomplete: some sets may be missing'
    page.strip_details_btn.click()
    assert 'boom' in page.details.toPlainText() and page.details.isVisibleTo(page)


def test_read_errors_and_missing_file_show_a_card(qtbot, setup):
    ctx, fake = setup
    fake.results['BLU'] = job_read(sets=[], error='took too long to load (over 10 s)')
    page = make_page(qtbot, ctx)
    assert page.body.currentWidget() is page.message
    assert page.message.title.text() == "Couldn't read Alice_BLU.lua: took too long to load (over 10 s)"
    assert page.message.action.text() == 'Retry'
    fake.results['BLU'] = JobRead('Alice', 'BLU', '', '', False, {}, error=gearswap_reader.NO_FILE)
    page.request(force=True)
    wait(qtbot, page)
    qtbot.waitUntil(lambda: page.message.title.text().startswith('No GearSwap file'))
    assert "Alice's BLU" in page.message.title.text() and 'data' in page.message.details.toPlainText()
    assert page.toolbar.isEnabled()  # other jobs still work


def test_snapshot_absent_and_empty_messages(qtbot, setup):
    ctx, _fake = setup
    ctx.inventory_snapshot = {}
    page = make_page(qtbot, ctx)
    assert page.verdict.text() == 'No inventory snapshot'
    assert page.grid.cell('head').state == 'no_snapshot'
    assert page.strip_label.text() == 'Log in with the Nexus addon running to see what you own'
    ctx.inventory_snapshot = {'Alice': []}
    ctx.inventory_changed.emit()
    assert page.strip_label.text() == 'No items recorded for Alice.'
    assert page.grid.cell('head').state == 'missing'


def test_inventory_change_recolours_without_running_lua(qtbot, setup):
    ctx, fake = setup
    page = make_page(qtbot, ctx)
    calls = len(fake.calls)
    ctx.inventory_snapshot['Alice'].append(row(23110, 'Sroda Ring', 'Wardrobe 2'))
    ctx.inventory_changed.emit()
    assert len(fake.calls) == calls
    assert page.grid.cell('ring1').state == 'owned' and page.grid.cell('ring2').state == 'unreachable'
    assert page.grid.cell('ring1').changed  # outlined once after the change


def test_quick_job_changes_read_at_most_twice_and_draw_the_last(qtbot, setup):
    ctx, fake = setup
    page = make_page(qtbot, ctx)
    fake.calls.clear()
    fake.gate = threading.Event()
    fake.results['RUN'] = job_read(job='RUN', sets=[SetRead('sets.RunOnly', ['RunOnly'], {})])
    for job in ('RUN', 'BLU', 'RUN', 'BLU', 'RUN'):
        page.job_combo.setCurrentIndex(page.job_combo.findData(job))
        page._manual_pick()
    fake.gate.set()
    qtbot.waitUntil(lambda: not page._busy and page.read.job == 'RUN', timeout=5000)
    assert len(fake.calls) <= 2
    assert [s.path for s in page.read.sets] == ['sets.RunOnly']


def test_stale_result_is_not_drawn(qtbot, setup):
    ctx, _fake = setup
    page = make_page(qtbot, ctx)
    page._latest = 99
    page._read_done(98, job_read(job='RUN', sets=[]))
    assert page.read.job == 'BLU'


def test_character_choice_is_saved_and_restored(qtbot, setup):
    ctx, _fake = setup
    page = make_page(qtbot, ctx)
    page.character_combo.setCurrentText('Bob')
    page._character_picked(page.character_combo.currentIndex())
    assert ctx.settings.get('sets_character') == 'Bob'
    assert page.job_combo.currentData() == 'SMN'
    again = make_page(qtbot, ctx)
    assert again.character_combo.currentText() == 'Bob'


def test_follows_the_game_until_a_job_is_picked_by_hand(qtbot, setup):
    ctx, fake = setup
    page = make_page(qtbot, ctx)
    ctx.bridge.state = {'player_name': 'Alice', 'main_job': 'RUN', 'sub_job': 'WAR'}
    ctx.bridge.state_received.emit(ctx.bridge.state)
    qtbot.waitUntil(lambda: not page._busy and page.read.job == 'RUN', timeout=5000)
    assert page.sub_combo.currentText() == 'WAR' and page.follow_btn.isHidden()
    page.job_combo.setCurrentIndex(page.job_combo.findData('BLU'))
    page._manual_pick()
    wait(qtbot, page)
    ctx.bridge.state_received.emit(ctx.bridge.state)
    assert page.job_combo.currentData() == 'BLU'  # pinned
    assert page.follow_label.text() == 'Game is on RUN/WAR ·' and not page.follow_btn.isHidden()
    page.follow_btn.click()
    qtbot.waitUntil(lambda: not page._busy and page.read.job == 'RUN', timeout=5000)
    assert page.follow_btn.isHidden()


def test_showing_again_rereads_and_keeps_the_selection(qtbot, setup):
    ctx, fake = setup
    page = make_page(qtbot, ctx)
    page.tree.setCurrentItem(page.tree.topLevelItem(0).child(0))
    page.grid.select('head')
    page._cell_clicked('head')
    calls = len(fake.calls)
    page.on_shown()
    wait(qtbot, page)
    qtbot.waitUntil(lambda: len(fake.calls) == calls + 1)
    qtbot.waitUntil(lambda: not page._busy)
    assert page.current_path == 'sets.Idle.Standard' and page.grid.selected() == 'head'


def test_keyboard_shortcuts_and_narrow_panel(qtbot, setup):
    ctx, fake = setup
    page = make_page(qtbot, ctx)
    page.resize(900, 600)
    qtbot.waitUntil(lambda: page._wide is False)
    page.grid.setFocus()
    qtbot.keyClick(page.grid, Qt.Key_Return)
    assert page.panel.isVisible() and page.panel_slot.text() == 'Main'
    qtbot.keyClick(page.grid, Qt.Key_Escape)
    assert not page.panel.isVisible()
    calls = len(fake.calls)
    qtbot.keyClick(page.grid, Qt.Key_F5)
    wait(qtbot, page)
    qtbot.waitUntil(lambda: len(fake.calls) == calls + 1)
    assert fake.calls[-1][3] is True  # F5 = Reload files (force)
    qtbot.keyClick(page.grid, Qt.Key_F, Qt.ControlModifier)
    assert page.toolbar.search.hasFocus()
    qtbot.waitUntil(lambda: not page._busy)


def test_wide_window_docks_the_panel(qtbot, setup):
    ctx, _fake = setup
    page = make_page(qtbot, ctx)
    page.resize(1500, 900)
    qtbot.waitUntil(lambda: page._wide is True)
    assert page.split.count() == 3 and page.split.widget(2) is page.panel
    assert page.panel_placeholder.text() == 'Click a slot to see what you own for it.'


def test_no_windower_folder_asks_for_one(qtbot, setup):
    ctx, fake = setup
    ctx.windower_dir = ''
    page = make_page(qtbot, ctx, show=False)
    page.show()
    page.on_shown()
    assert page.message.title.text() == 'Choose your Windower folder in Settings'
    assert fake.calls == []


def test_default_character_is_one_with_job_files(qtbot, setup):
    ctx, _fake = setup
    ctx.inventory_snapshot = {'Aaron': [row(23100, 'x', character='Aaron')], **ctx.inventory_snapshot}
    page = make_page(qtbot, ctx)
    assert page.character_combo.itemText(0) == 'Aaron' and page.character_combo.currentText() == 'Alice'


def replacement_groups(page):
    return [page.replacement_list.topLevelItem(i) for i in range(page.replacement_list.topLevelItemCount())]


def select_replacement(page, name):
    for group in replacement_groups(page):
        for i in range(group.childCount()):
            entry = group.child(i)
            if entry.data(0, Qt.UserRole)['name'] == name:
                page.replacement_list.setCurrentItem(entry)
                return entry
    raise AssertionError(f'No replacement named {name}')


def fix_read(ctx, fake, sets=None):
    filename = Path(ctx.windower_dir) / 'addons' / 'GearSwap' / 'data' / 'Alice_BLU.lua'
    filename.write_text('sets.Idle.Standard = {head="Hashishin Kavuk +2"}\n'
                        'sets.SavageBlade.Attack = {head="Hashishin Kavuk +2"}\n', encoding='utf-8')
    read = job_read()
    read.path = str(filename)
    read.files = {str(filename): filename.stat().st_mtime}
    if sets is not None:
        read.sets = sets
    fake.results['BLU'] = read
    return filename


def test_upgrade_badge_picker_group_order_and_stored_guidance(qtbot, setup):
    ctx, fake = setup
    fix_read(ctx, fake)
    ctx.inventory_snapshot['Alice'] += [row(23101, 'Hashishin Kavuk +3'), row(23113, 'Herculean Helm', 'Mog Safe 1')]
    # Raw snapshot rows need not carry their character; the snapshot's key supplies it.
    for item in ctx.inventory_snapshot['Alice']:
        item.pop('character', None)
    ctx.inventory_snapshot['Bob'] = [row(23116, 'Hope Masque', character='Bob')]
    page = make_page(qtbot, ctx)
    assert page.grid.cell('head').state == 'owned' and page.grid.cell('head').badge == '↑'
    assert 'upgrade available' in page.grid.cell('head').accessible_name
    assert page._items['sets.SavageBlade.Attack'].text(2) == '↑ 1'
    assert page.set_caption.text().endswith('1 upgrade')
    page._cell_clicked('head')
    groups = replacement_groups(page)
    assert [g.text(0) for g in groups] == ['Higher tier owned', 'In your wardrobes', 'Stored', 'On other characters (1)']
    assert not groups[-1].isExpanded()
    assert groups[0].child(0).text(0) == 'Hashishin Kavuk +3  ↑'
    assert groups[0].child(0).text(1) == 'Wardrobe 3'
    select_replacement(page, 'Herculean Helm')
    assert 'Move from Mog Safe 1 before use' in page.replacement_details.text()
    select_replacement(page, 'Hope Masque')
    assert 'On Bob; this copy is not available here.' in page.replacement_details.text()
    assert 'Requirements unverified: needs superior level 3' in page.replacement_details.text()
    assert not page.copy_btn.isEnabled() and page.copy_area.isHidden()


def test_copy_slot_and_all_snippets_clipboard_status_and_open_file(qtbot, setup, monkeypatch):
    from PySide6.QtWidgets import QApplication
    ctx, fake = setup
    filename = fix_read(ctx, fake)
    ctx.inventory_snapshot['Alice'].append(row(23101, 'Hashishin Kavuk +3'))
    page = make_page(qtbot, ctx)
    statuses, opened = [], []
    monkeypatch.setattr(page, 'status', statuses.append)
    monkeypatch.setattr(ctx, 'edit_file', opened.append)
    page._cell_clicked('head')
    select_replacement(page, 'Hashishin Kavuk +3')
    assert page.copy_btn.text() == 'Copy slot line'
    assert page.copy_scope.text() == 'Replace 1 slot line in Alice_BLU.lua'
    assert page.copy_location.text() == 'Alice_BLU.lua, line 2'
    assert 'Source: Alice_BLU.lua, line 2.' in page.source_help.text()
    assert 'sets.SavageBlade.Attack' in page.source_help.text()
    assert page.copy_all_btn.text() == 'Copy 2 snippets'
    page.copy_btn.click()
    assert QApplication.clipboard().text() == 'head="Hashishin Kavuk +3",'
    assert statuses[-1] == 'Copied: paste into Alice_BLU.lua, then //gs reload'
    page.copy_all_btn.click()
    assert '(2 places)' in QApplication.clipboard().text()
    assert QApplication.clipboard().text().count('head="Hashishin Kavuk +3",') == 2
    page.open_file_btn.click()
    assert opened == [str(filename)]
    assert 'Hashishin Kavuk +3' not in filename.read_text()  # copy/open never writes Lua


def test_filter_shown_above_eight_rows_and_selection_is_invalidated(qtbot, setup):
    ctx, fake = setup
    fix_read(ctx, fake)
    ctx.inventory_snapshot['Alice'] += [row(23101, 'Hashishin Kavuk +3')] * 9
    page = make_page(qtbot, ctx)
    page._cell_clicked('head')
    assert not page.replacement_filter.isHidden()
    select_replacement(page, 'Hashishin Kavuk +3')
    assert page.copy_btn.isEnabled()
    page.replacement_filter.setText('Herculean')
    assert not page.copy_btn.isEnabled() and all(g.isHidden() for g in replacement_groups(page))


def test_copy_disabled_during_reload_context_change_and_inventory_recompute(qtbot, setup):
    ctx, fake = setup
    fix_read(ctx, fake)
    ctx.inventory_snapshot['Alice'].append(row(23101, 'Hashishin Kavuk +3'))
    page = make_page(qtbot, ctx)
    page._cell_clicked('head')
    select_replacement(page, 'Hashishin Kavuk +3')
    fake.gate = threading.Event()
    try:
        page.request(force=True)
        assert not page.copy_btn.isEnabled() and page._copy_target is None
        assert not page.replacements.isEnabled()
    finally:
        fake.gate.set()
    wait(qtbot, page)
    assert page.current_slot == 'head' and not page.copy_btn.isEnabled()
    select_replacement(page, 'Hashishin Kavuk +3')
    ctx.inventory_snapshot['Alice'] = [row(23100, 'Hashishin Kavuk +2')]
    before = len(fake.calls)
    ctx.inventory_changed.emit()
    assert not page.copy_btn.isEnabled() and not page.grid.cell('head').badge
    assert len(fake.calls) == before
    page.job_combo.setCurrentIndex(page.job_combo.findData('RUN'))
    page._manual_pick()
    assert not page.copy_btn.isEnabled()
    wait(qtbot, page)


def test_ambiguous_location_shows_candidates_and_still_opens_job_file(qtbot, setup, monkeypatch):
    ctx, fake = setup
    filename = fix_read(ctx, fake)
    with filename.open('a') as f:
        f.write('sets.SavageBlade.Attack = {head="Hashishin Kavuk +2"}\n')
    ctx.inventory_snapshot['Alice'].append(row(23101, 'Hashishin Kavuk +3'))
    page = make_page(qtbot, ctx)
    page._cell_clicked('head')
    select_replacement(page, 'Hashishin Kavuk +3')
    assert 'Location ambiguous · search for sets.SavageBlade.Attack' in page.copy_location.text()
    assert 'Alice_BLU.lua:2' in page.copy_location.text() and 'Alice_BLU.lua:3' in page.copy_location.text()
    assert page.open_file_btn.isEnabled() and page.copy_btn.isEnabled()
    assert page.open_file_btn.text() == 'Open job file'
    assert 'Location ambiguous: check the candidate locations below before pasting.' in page.source_help.text()
    opened = []
    monkeypatch.setattr(ctx, 'edit_file', opened.append)
    page.open_file_btn.click()
    assert opened == [str(filename)]


@pytest.mark.parametrize('sets', [None, []], ids=['with_sets', 'without_sets'])
def test_open_job_file_works_before_selecting_any_replacement(qtbot, setup, monkeypatch, sets):
    ctx, fake = setup
    filename = fix_read(ctx, fake, sets=sets)
    page = make_page(qtbot, ctx)
    opened = []
    monkeypatch.setattr(ctx, 'edit_file', opened.append)
    assert page._copy_target is None and page.open_file_btn.isEnabled()
    page.open_file_btn.click()
    assert opened == [str(filename)]
    ctx.windower_dir = ''
    page._windower_changed('')
    assert not page.open_file_btn.isEnabled()


def test_source_search_guidance_tracks_slot_without_needing_a_replacement(qtbot, setup):
    ctx, fake = setup
    fix_read(ctx, fake)
    page = make_page(qtbot, ctx)
    page._cell_clicked('head')
    assert page.copy_area.isHidden()
    assert not page.source_help.isHidden()
    assert 'Ctrl+F' in page.source_help.text()
    assert 'sets.SavageBlade.Attack' in page.source_help.text()
    assert 'head= (Hashishin Kavuk +2)' in page.source_help.text()
    page._cell_clicked('neck')
    assert 'neck= (Fotia Gorget)' in page.source_help.text()
    assert 'head=' not in page.source_help.text()
    page._cell_clicked('main')  # no slot entry to search for
    assert page.source_help.isHidden() and page.source_help.text() == ''
    page._cell_clicked('head')
    page._clear_panel()
    assert page.source_help.isHidden() and page.source_help.text() == ''


def test_grid_context_menu_uses_the_clicked_item_and_all_existing_sites(qtbot, setup, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtWidgets import QApplication, QMenu
    from vanadiel_nexus.ui.pages import sets as sets_page
    ctx, _ = setup
    ctx.opened = []
    ctx.open_url = ctx.opened.append
    menus = []

    class CapturedMenu(QMenu):
        def exec(self, *_args):
            menus.append(self)

    monkeypatch.setattr(sets_page, 'QMenu', CapturedMenu)
    page = make_page(qtbot, ctx)
    cell = page.grid.cells['neck']
    event = QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(2, 2), cell.mapToGlobal(QPoint(2, 2)))
    QApplication.sendEvent(cell, event)
    assert page.grid.selected() == 'neck' and page.current_slot == 'neck'
    assert [a.text() for a in menus[-1].actions()] == ['Item details (Alt+I)', 'Open on BG-Wiki ↗', 'Open on FFXIAH ↗', 'Open on FFXIclopedia ↗']
    menus[-1].actions()[2].trigger()
    assert ctx.opened[-1] == 'https://www.ffxiah.com/item/23106'
    count = len(menus)
    cell = page.grid.cells['main']
    QApplication.sendEvent(cell, QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(2, 2), cell.mapToGlobal(QPoint(2, 2))))
    assert len(menus) == count  # no item, no wiki menu
    assert page.grid.selected() == page.current_slot == 'main'
    assert page._copy_target is None and not page.copy_btn.isEnabled()
    page._busy = True
    cell = page.grid.cells['head']
    QApplication.sendEvent(cell, QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(2, 2), cell.mapToGlobal(QPoint(2, 2))))
    assert len(menus) == count  # no stale-context actions during a read
    assert page.grid.selected() == page.current_slot == 'main'
    page._busy = False


def test_replacement_rows_separate_item_names_from_quieter_locations(qtbot, setup):
    ctx, fake = setup
    fix_read(ctx, fake)
    ctx.inventory_snapshot['Alice'].append({**row(23113, 'Herculean Helm'), 'augments': 'DEX+10, STR+5'})
    page = make_page(qtbot, ctx)
    page._cell_clicked('head')
    entry = select_replacement(page, 'Herculean Helm')
    assert page.replacement_list.headerItem().text(0) == 'Item'
    assert page.replacement_list.headerItem().text(1) == 'Location'
    assert entry.text(0) == 'Herculean Helm' and '\n' not in entry.text(0)
    assert entry.text(1) == 'Wardrobe 3' and entry.font(0).bold()
    assert entry.font(1).pixelSize() == round(12 * page._scale())
    assert page.replacement_name.text() == 'Herculean Helm'
    assert 'DEX+10' in page.replacement_details.text()
    page.replacement_filter.setText('STR+5')
    assert not entry.isHidden()  # augment filtering still works without cluttering the item column


@pytest.mark.parametrize('shared', [False, True])
def test_root_and_shared_scope_payload_label_and_affected_sets(qtbot, setup, shared):
    ctx, fake = setup
    sets = []
    for i in range(4):
        p = piece('head', 'Herculean Helm', augments=['DEX+10'], table_id=7 if shared else 0)
        if i and not shared:
            p.inherited_from = p.origin_path = 'sets.S0'
        sets.append(SetRead(f'sets.S{i}', [f'S{i}'], {'head': p}))
    filename = fix_read(ctx, fake, sets)
    filename.write_text('gear.helm={name="Herculean Helm",augments={"DEX+10"}}\n'
                        'sets.S0={head="Herculean Helm"}\n', encoding='utf-8')
    ctx.inventory_snapshot['Alice'].append({**row(23113, 'Herculean Helm'), 'augments': 'DEX+20, STR+10'})
    page = make_page(qtbot, ctx)
    page._select_path('sets.S3')
    page._cell_clicked('head')
    select_replacement(page, 'Herculean Helm')
    assert page.copy_scope.text() == ('Replace shared table · affects 4 sets' if shared else 'Fix at root S0 · fixes 4 sets')
    assert page.copy_btn.text() == ('Copy table' if shared else 'Copy slot line')
    assert ('search for:\nHerculean Helm' if shared else 'search for:\nsets.S0') in page.source_help.text()
    if shared:
        assert 'Find the shared item table definition.' in page.source_help.text()
    assert page.copy_all_btn.isHidden()
    page.affected_btn.click()
    assert not page.affected_sets.isHidden() and page.affected_sets.text().splitlines() == [f'sets.S{i}' for i in range(4)]


@pytest.mark.parametrize('snapshot', [{}, {'Alice': []}])
def test_replacements_absent_and_empty_snapshot(qtbot, setup, snapshot):
    ctx, _ = setup
    ctx.inventory_snapshot = snapshot
    page = make_page(qtbot, ctx)
    page._cell_clicked('head')
    assert not page.copy_btn.isEnabled()
    if snapshot:
        assert page.replacement_details.text() == 'No items recorded for Alice.'
    else:
        assert page.replacements.isHidden()


def test_copy_summary_pauses_auto_follow_and_windower_change_clears_it(qtbot, setup):
    ctx, fake = setup
    fix_read(ctx, fake)
    ctx.inventory_snapshot['Alice'].append(row(23101, 'Hashishin Kavuk +3'))
    page = make_page(qtbot, ctx)
    page._cell_clicked('head')
    select_replacement(page, 'Hashishin Kavuk +3')
    ctx.bridge.state = {'player_name': 'Alice', 'main_job': 'RUN'}
    page._game_state(ctx.bridge.state)
    assert page.job_combo.currentData() == 'BLU' and page.copy_btn.isEnabled()
    ctx.windower_dir = ''
    page._windower_changed('')
    assert page._copy_target is None and not page.copy_btn.isEnabled()


def test_selector_labels_are_visible_and_associated_with_their_pickers(qtbot, setup):
    ctx, _ = setup
    page = make_page(qtbot, ctx)
    for text, combo in [('Character', page.character_combo), ('Main job', page.job_combo), ('Sub job', page.sub_combo)]:
        label = page.selector_labels[text]
        assert label.text() == text and label.buddy() is combo and label.isVisible()
        assert combo.accessibleName() == text


def test_sets_offers_wiki_sites_for_current_and_selected_replacement(qtbot, setup):
    ctx, fake = setup
    fix_read(ctx, fake)
    ctx.inventory_snapshot['Alice'].append(row(23101, 'Hashishin Kavuk +3'))
    opened = []
    ctx.open_url = opened.append
    ctx.settings.set('wiki_site', 'ffxiah')
    page = make_page(qtbot, ctx)
    assert page.item_links_btn.isHidden()
    page._cell_clicked('head')
    actions = page.item_links_btn.menu().actions()
    assert [a.text() for a in actions] == ['Open on FFXIAH ↗', 'Open on BG-Wiki ↗', 'Open on FFXIclopedia ↗']
    actions[0].trigger()
    assert opened[-1] == 'https://www.ffxiah.com/item/23100'
    actions[1].trigger()
    assert opened[-1] == 'https://www.bg-wiki.com/ffxi/Hashishin_Kavuk_%2B2'
    select_replacement(page, 'Hashishin Kavuk +3')
    page.replacement_links_btn.menu().actions()[0].trigger()
    assert opened[-1] == 'https://www.ffxiah.com/item/23101'
    page.replacement_links_btn.menu().actions()[2].trigger()
    assert opened[-1] == 'https://ffxiclopedia.fandom.com/wiki/Hashishin_Kavuk_%2B3'
    page._cell_clicked('main')
    assert page.item_links_btn.isHidden() and page.replacement_links_btn.isHidden()
    assert not page.item_links_btn.menu().actions() and not page.replacement_links_btn.menu().actions()


def test_unknown_item_can_copy_selected_correction_without_bulk_guessing(qtbot, setup):
    from PySide6.QtWidgets import QApplication
    ctx, fake = setup
    bad_name = "Nyame's Mail"
    sets = [SetRead('sets.Idle', ['Idle'], {'body': piece('body', bad_name)}),
            SetRead('sets.Other', ['Other'], {'body': piece('body', bad_name)})]
    filename = fix_read(ctx, fake, sets)
    filename.write_text('sets.Idle={body="Nyame\'s Mail"}\nsets.Other={body="Nyame\'s Mail"}\n', encoding='utf-8')
    before = filename.read_bytes()
    ctx.inventory_snapshot['Alice'].append(row(23102, 'Nyame Mail'))
    page = make_page(qtbot, ctx)
    page._select_path('sets.Idle')
    page._cell_clicked('body')
    assert page.grid.cell('body').state == 'unknown'
    select_replacement(page, 'Nyame Mail')
    assert page.copy_btn.isEnabled() and page.copy_all_btn.isHidden()
    assert len(page._copy_plan.targets) == 1
    assert page._copy_target.affected_sets == ['sets.Idle']
    page.copy_btn.click()
    assert QApplication.clipboard().text() == 'body="Nyame Mail",'
    assert filename.read_bytes() == before


def test_stored_copy_with_designated_bag_shows_move_guidance_without_a_snippet(qtbot, setup):
    ctx, fake = setup
    p = piece('head', 'Hashishin Kavuk +2', bag='Wardrobe 1')
    fix_read(ctx, fake, [SetRead('sets.Idle', ['Idle'], {'head': p})])
    ctx.inventory_snapshot['Alice'].append(row(23101, 'Hashishin Kavuk +3', 'Mog Safe 1'))
    page = make_page(qtbot, ctx)
    page._cell_clicked('head')
    select_replacement(page, 'Hashishin Kavuk +3')
    assert 'Move from Mog Safe 1 before use' in page.replacement_details.text()
    assert 'Move this copy' in page.replacement_details.text()
    assert not page.copy_btn.isEnabled() and page.copy_area.isHidden()
    assert page.snippet.toPlainText() == ''


def test_unrelated_blocked_bag_target_does_not_hide_current_copy(qtbot, setup):
    ctx, fake = setup
    plain = SetRead('sets.Idle', ['Idle'], {'head': piece('head', 'Hashishin Kavuk +2')})
    constrained = SetRead('sets.WS', ['WS'], {'head': piece('head', 'Hashishin Kavuk +2', bag='Wardrobe 2')})
    fix_read(ctx, fake, [plain, constrained])
    ctx.inventory_snapshot['Alice'].append(row(23101, 'Hashishin Kavuk +3', 'Mog Safe 1'))
    page = make_page(qtbot, ctx)
    page._select_path('sets.Idle')
    page._cell_clicked('head')
    select_replacement(page, 'Hashishin Kavuk +3')
    assert page.copy_btn.isEnabled() and page.copy_all_btn.isHidden()
    assert page.snippet.toPlainText() == 'head="Hashishin Kavuk +3",'
    assert '1 other edit location' in page.copy_note.text()
    page._select_path('sets.WS')
    page._cell_clicked('head')
    select_replacement(page, 'Hashishin Kavuk +3')
    assert not page.copy_btn.isEnabled() and page.copy_area.isHidden()


def test_inherited_unknown_correction_explains_adding_a_local_override(qtbot, setup):
    ctx, fake = setup
    bad = "Nyame's Mail"
    root = SetRead('sets.Base', ['Base'], {'body': piece('body', bad)})
    child = SetRead('sets.Idle', ['Idle'], {'body': piece('body', bad, inherited_from=root.path, origin_path=root.path)})
    fix_read(ctx, fake, [root, child])
    ctx.inventory_snapshot['Alice'].append(row(23102, 'Nyame Mail'))
    page = make_page(qtbot, ctx)
    page._select_path('sets.Idle')
    page._cell_clicked('body')
    select_replacement(page, 'Nyame Mail')
    assert page.copy_scope.text() == 'Add slot override in Idle · affects 1 sets'
    assert 'Add this field to sets.Idle' in page.copy_note.text()
    assert 'Leave the shared root unchanged' in page.copy_note.text()
    assert 'search for:\nsets.Idle' in page.source_help.text()


def test_focus_refresh_restores_choice_only_after_rebuilding_the_copy(qtbot, setup):
    ctx, fake = setup
    fix_read(ctx, fake)
    ctx.inventory_snapshot['Alice'].append(row(23101, 'Hashishin Kavuk +3'))
    page = make_page(qtbot, ctx)
    page._cell_clicked('head')
    select_replacement(page, 'Hashishin Kavuk +3')
    previous_target = page._copy_target
    page.request(preserve_replacement=True)
    assert not page.copy_btn.isEnabled() and page._copy_target is None
    wait(qtbot, page)
    assert page.copy_btn.isEnabled() and page.snippet.toPlainText() == 'head="Hashishin Kavuk +3",'
    assert page._copy_target is not previous_target
    # A changed file state cannot restore the prior payload, even if the same replacement is owned.
    from dataclasses import replace
    fake.results['BLU'] = replace(page.read, files={**page.read.files, 'changed.lua': 2})
    page.request(preserve_replacement=True)
    wait(qtbot, page)
    assert not page.copy_btn.isEnabled() and page._copy_target is None


def test_paired_slot_shortage_is_visible_before_bulk_copy(qtbot, setup):
    ctx, fake = setup
    s = SetRead('sets.Test', ['Test'], {slot: piece(slot, 'Chirich Ring +1') for slot in ('ring1', 'ring2')})
    fix_read(ctx, fake, [s])
    ctx.inventory_snapshot['Alice'] = [{**row(23114, 'Chirich Ring +1'), 'count': 2}, row(23110, 'Sroda Ring')]
    for item in ctx.inventory_snapshot['Alice']:
        item.pop('character', None)
    page = make_page(qtbot, ctx)
    page._cell_clicked('ring1')
    select_replacement(page, 'Sroda Ring')
    assert page.copy_btn.isEnabled() and page.copy_all_btn.isEnabled()
    assert not page.copy_warning.isHidden() and 'Copy all warning:' in page.copy_warning.text()
    assert 'Ring 1 / Ring 2' in page.copy_warning.text()
    ctx.inventory_snapshot['Alice'][-1]['count'] = 2
    ctx.inventory_changed.emit()
    select_replacement(page, 'Sroda Ring')
    assert page.copy_warning.isHidden()


def test_a_game_job_without_a_file_is_followed_once_not_on_every_update(qtbot, setup, monkeypatch):
    ctx, _fake = setup
    page = make_page(qtbot, ctx)
    fills = []
    real_fill = page._fill_jobs
    monkeypatch.setattr(page, '_fill_jobs', lambda *a, **k: (fills.append(a), real_fill(*a, **k))[1])
    ctx.bridge.state = {'player_name': 'Alice', 'main_job': 'PUP', 'sub_job': 'WAR'}  # Alice has no PUP file
    for _ in range(3):
        ctx.bridge.state_received.emit(ctx.bridge.state)
    wait(qtbot, page)
    assert len(fills) == 1
    assert page.job_combo.currentData() != 'PUP'
    ctx.bridge.state = {'player_name': 'Alice', 'main_job': 'RUN', 'sub_job': 'WAR'}  # a real change is followed
    ctx.bridge.state_received.emit(ctx.bridge.state)
    qtbot.waitUntil(lambda: not page._busy and page.read.job == 'RUN', timeout=5000)
    assert len(fills) == 2
