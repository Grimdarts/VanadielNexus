import os
from types import MappingProxyType

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtCore import QObject, Signal, Qt

from vanadiel_nexus.core.equipment_analysis import name_index
from vanadiel_nexus.core.equipment_effects import SourceSnapshot
from vanadiel_nexus.core.gearswap_reader import JobRead, Piece, SetRead
from vanadiel_nexus.core.item_res import Item
from vanadiel_nexus.ui.equipment_analyzer import EquipmentAnalyzer
from vanadiel_nexus.ui.equipment_details import equipment_service
from vanadiel_nexus.ui.equip_grid import EquipGrid

STIKINI = 'MND+8 Magic Accuracy+11\nAll magic skills +8\n"Refresh"+1'


class Settings:
    def get(self, key, default=None):
        return default


class Context(QObject):
    windower_changed = Signal(str)
    inventory_changed = Signal()

    def __init__(self, root):
        super().__init__()
        self.windower_dir = str(root)
        self.settings = Settings()
        self.inventory_snapshot = {'Alice': [{'item_id': 26184, 'bag': 'Wardrobe 2', 'count': 2}]}


@pytest.fixture
def setup(qtbot, tmp_path):
    ctx = Context(tmp_path)
    service = equipment_service(ctx)
    service.source = SourceSnapshot(str(tmp_path), (), 'fictional',
                                   MappingProxyType({26184: Item(26184, 'Stikini Ring +1', slots=24576, jobs=8)}),
                                   MappingProxyType({26184: STIKINI}))
    service.names = name_index(service.source.items)
    service.bags = ({'id': 10, 'en': 'Wardrobe 2', 'equippable': True},)
    a = SetRead('sets.a', ['a'], {'ring1': Piece('ring1', 'ring1', 'Stikini Ring +1')})
    b = SetRead('sets.b', ['b'], {'ring1': Piece('ring1', 'ring1', 'Stikini Ring +1'),
                                'ring2': Piece('ring2', 'ring2', 'Stikini Ring +1')})
    read = JobRead('Alice', 'WHM', '', 'fictional.lua', False, {}, sets=[a, b])
    widget = EquipmentAnalyzer(ctx)
    qtbot.addWidget(widget)
    widget.set_selection(read, a.path)
    yield ctx, service, widget, read
    service.close()


def test_same_scenario_partial_comparison_and_missing_stat_labels(setup):
    ctx, service, widget, read = setup
    assert widget.result.get('refresh').known == 1
    widget.baseline.setCurrentIndex(widget.baseline.findData('sets.b'))
    assert widget.comparison.get('refresh').known == 2
    changes = [widget.table.topLevelItem(i).text(3) for i in range(widget.table.topLevelItemCount())]
    assert '-1 · partial' in changes
    widget.unity.setCurrentIndex(1)
    assert widget.scenario() == {'unity_member': True, 'unity_verified': True, 'unity_rank': 1}
    assert widget.result.get('refresh').known == 1 and widget.comparison.get('refresh').known == 2
    assert 'Resource: fictional' in widget.trace.toPlainText()
    assert 'main: omitted' in widget.trace.toPlainText()


def test_snapshot_loss_and_source_failure_clear_both_sides(setup):
    ctx, service, widget, read = setup
    widget.baseline.setCurrentIndex(widget.baseline.findData('sets.b'))
    ctx.inventory_snapshot = {}
    widget.set_selection(read, 'sets.a')
    assert widget.result is widget.comparison is None
    assert widget.table.topLevelItemCount() == 0 and 'No inventory snapshot' in widget.status.text()
    service._failed('Fictional failure')
    assert 'Fictional failure' in widget.status.text() and widget.trace.toPlainText() == ''
    widget.show_item('ring1', widget.details_button)
    assert widget.card.name.text() == 'Stikini Ring +1'
    assert 'Description unavailable' in widget.card.text.text()
    assert widget.card.payload['observed'] is None


def test_character_switch_does_not_reuse_old_comparison_or_copies(setup):
    ctx, service, widget, read = setup
    widget.baseline.setCurrentIndex(widget.baseline.findData('sets.b'))
    read.character = 'Bob'
    widget.set_selection(read, 'sets.a')
    assert widget.result is None
    assert widget.baseline.currentData() is None
    payload = widget.card_payload('ring1')
    assert payload['observed'] is None and payload['observations'] == []


def test_item_card_keyboard_content_duplicate_identity_and_escape(qtbot, setup):
    ctx, service, widget, read = setup
    widget.resize(900, 600)
    widget.show()
    widget.show_item('ring1', widget.details_button)
    assert widget.card.isVisible()
    assert 'ambiguous' in widget.card.text.text()
    assert 'SOURCE-DESCRIBED' in widget.card.text.text() and STIKINI in widget.card.text.text()
    assert 'WHM' in widget.card.text.text() and 'BLU' not in widget.card.text.text()
    qtbot.keyClick(widget.card, Qt.Key_Escape)
    assert not widget.card.isVisible()


def test_request_invalidation_clears_hover_card_and_contributions(qtbot, setup):
    ctx, service, widget, read = setup
    grid = EquipGrid()
    qtbot.addWidget(grid)
    widget.attach_grid(grid)
    widget.show_item('ring1', widget.details_button)
    widget.invalidate()
    assert widget.result is None and widget.read is None and widget.card.payload is None
    assert widget.table.topLevelItemCount() == 0 and not widget.hover_timer.isActive()


def test_structured_rank_is_unresolved_not_added_to_mnd(setup):
    ctx, service, widget, read = setup
    ctx.inventory_snapshot['Alice'][0].update(count=1, rank=20, path='B')
    widget.set_selection(read, 'sets.a')
    assert widget.result.get('mnd').known == 8
    assert not widget.result.get('mnd').complete
    widget.show_item('ring1', widget.details_button)
    assert 'Rank: 20' in widget.card.text.text() and 'Path: B' in widget.card.text.text()


def test_unrelated_material_stacks_do_not_expand_in_equipment_evaluation(setup, monkeypatch):
    from vanadiel_nexus.core import equipment_effects
    ctx, service, widget, read = setup
    ctx.inventory_snapshot['Alice'].append({'item_id': 1, 'count': 9999, 'bag': 'Wardrobe 2'})
    original, visited = equipment_effects.units, []
    def counted(rows):
        for row in original(rows):
            visited.append(row['item_id'])
            yield row
    monkeypatch.setattr(equipment_effects, 'units', counted)
    service.cache.clear()
    widget.set_selection(read, 'sets.a')
    assert visited == [26184, 26184]
    assert widget.result.get('refresh').known == 1
