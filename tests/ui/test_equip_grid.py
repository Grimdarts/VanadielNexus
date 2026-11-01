import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFont, QFontMetrics  # noqa: E402

from vanadiel_nexus.ui.equip_grid import STATES, CellData, EquipGrid, describe, elide_two_lines  # noqa: E402


@pytest.fixture
def grid(qtbot):
    widget = EquipGrid()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_sixteen_cells_in_game_order(grid):
    assert list(grid.cells) == ['main', 'sub', 'range', 'ammo', 'head', 'neck', 'ear1', 'ear2',
                                'body', 'hands', 'ring1', 'ring2', 'back', 'waist', 'legs', 'feet']
    positions = [grid.grid.getItemPosition(grid.grid.indexOf(cell))[:2] for cell in grid.cells.values()]
    assert positions == [(i // 4, i % 4) for i in range(16)]


def test_missing_slots_render_not_set_and_every_state_reads_in_words(grid):
    grid.set_cells({'head': CellData('head', 'Hashishin Kavuk +2', 'owned', 'Wardrobe 3', badge='↑')})
    assert grid.cell('body').state == 'not_set'
    assert grid.cells['body'].accessibleName() == 'Body: not specified'
    assert grid.cells['head'].accessibleName() == 'Head: Hashishin Kavuk +2, owned, Wardrobe 3, upgrade available'
    for state in STATES:
        grid.set_cells({'neck': CellData('neck', 'Fotia Gorget', state, 'word')})
        grid.cells['neck'].grab()  # paints without error
        assert grid.cell('neck').state == state
    assert describe(CellData('ring2', 'Sroda Ring', 'unreachable', '⚠ Mog Safe 1')) == \
        'Ring 2: Sroda Ring, unreachable, Mog Safe 1'
    assert describe(CellData('feet', state='empty')) == 'Feet: unequip'
    grid.set_cells({'neck': CellData('neck', 'x', 'bogus')})
    assert grid.cell('neck').state == 'not_set'


def test_click_selects_and_emits(grid, qtbot):
    with qtbot.waitSignal(grid.cell_clicked) as signal:
        qtbot.mouseClick(grid.cells['ring2'], Qt.LeftButton)
    assert signal.args == ['ring2'] and grid.selected() == 'ring2'
    assert grid.cells['ring2'].selected and not grid.cells['ring2'].focused  # selection ≠ focus
    grid.select('head')
    assert grid.cells['head'].selected and not grid.cells['ring2'].selected


def test_arrow_keys_move_focus_in_grid_order_and_enter_opens(grid, qtbot):
    grid.setFocus(Qt.TabFocusReason)
    qtbot.keyClick(grid, Qt.Key_Right)
    qtbot.keyClick(grid, Qt.Key_Down)
    assert grid.focused_slot() == 'neck'
    assert grid.cells['neck'].focused and not grid.cells['neck'].selected
    qtbot.keyClick(grid, Qt.Key_Down)
    qtbot.keyClick(grid, Qt.Key_Down)
    qtbot.keyClick(grid, Qt.Key_Down)  # clamps at the last row
    assert grid.focused_slot() == 'waist'
    with qtbot.waitSignal(grid.cell_clicked) as signal:
        qtbot.keyClick(grid, Qt.Key_Return)
    assert signal.args == ['waist'] and grid.selected() == 'waist'
    assert grid.accessibleName().startswith('Waist:')


def test_names_keep_their_tier_suffix_when_elided():
    font = QFont()
    font.setPixelSize(13)
    metrics = QFontMetrics(font)
    width = metrics.horizontalAdvance("Chasseur's Culottes")
    lines = elide_two_lines("Chasseur's Culottes Extraordinaire Magnifique +3", metrics, width)
    assert lines[0] == "Chasseur's Culottes" and lines[1].endswith('+3') and '…' in lines[1]
    assert elide_two_lines('Sroda Ring', metrics, metrics.horizontalAdvance('Sroda Ring')) == ['Sroda Ring']


def test_cells_grow_with_text_scale(grid):
    assert grid.cells['main'].width() == 112
    grid.set_scale(1.3)
    assert grid.cells['main'].width() == round(112 * 1.3) and grid.cells['main'].height() == round(128 * 1.3)
    grid.cells['main'].grab()
