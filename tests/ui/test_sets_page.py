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
