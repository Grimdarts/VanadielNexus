"""UI and AppContext integration tests for WorldMapPage."""
from __future__ import annotations

import os
import sys

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QGraphicsItem

from vanadiel_nexus.ui.context import AppContext
from vanadiel_nexus.ui.pages.world_map import WorldMapPage


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class _StubContext(QObject):
    zone_changed = Signal(str)

    def __init__(self, data_dir: str):
        super().__init__()
        self.data_dir = str(data_dir)
        self.zone_name = ""
        self.opened_urls: list[str] = []
        self.opened_paths: list[str] = []

    def open_url(self, url: str) -> None:
        self.opened_urls.append(url)

    def open_path(self, path: str) -> None:
        self.opened_paths.append(path)


@pytest.fixture()
def stub_ctx(tmp_path):
    return _StubContext(str(tmp_path))


def test_context_zone_signal(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("VN_DATA_DIR", str(tmp_path))
    ctx = AppContext("0.0.0-test")
    emitted: list[str] = []
    ctx.zone_changed.connect(emitted.append)

    ctx._on_state({"character_name": "Karu", "main_job": "WAR", "zone_name": "Kamihr Drifts"})
    assert ctx.zone_name == "Kamihr Drifts"
    assert emitted == ["Kamihr Drifts"]

    # Identical zone packet does not emit duplicate signal
    ctx._on_state({"character_name": "Karu", "main_job": "WAR", "zone_name": "Kamihr Drifts"})
    assert emitted == ["Kamihr Drifts"]

    # "unknown" zone packet is ignored
    ctx._on_state({"character_name": "Karu", "main_job": "WAR", "zone_name": "unknown"})
    assert ctx.zone_name == "Kamihr Drifts"
    assert emitted == ["Kamihr Drifts"]


def test_page_lazy_load_on_shown(qapp, stub_ctx):
    page = WorldMapPage(stub_ctx)
    assert page.graph is None
    assert len(page.node_items) == 0

    page.on_shown()
    assert page.graph is not None
    assert len(page.node_items) >= 220
    assert len(page.edge_items) >= 280
    assert len(page.halo_items) == 18


def test_node_selection_details(qapp, stub_ctx):
    page = WorldMapPage(stub_ctx)
    page.on_shown()

    # Select Outer Ra'Kaznar [U1/U2/U3] / Sortie (275)
    page.select_zone(275)
    assert page.selected_zone_id == 275
    assert "Sortie" in page.detail_title.text()
    assert page.neighbors_box.count() >= 1

    page._open_selected_wiki()
    assert stub_ctx.opened_urls == ["https://www.bg-wiki.com/ffxi/Category:Sortie"]


def test_neighbor_button_navigation(qapp, stub_ctx):
    page = WorldMapPage(stub_ctx)
    page.on_shown()
    page.select_zone(275)  # Sortie -> connected to Outer Ra'Kaznar (274) and Kamihr Drifts (267)

    assert page.neighbors_box.count() >= 1
    first_btn = page.neighbors_box.itemAt(0).widget()
    assert first_btn is not None
    first_btn.click()
    assert page.selected_zone_id in (274, 267)


def test_era_filter_dimming(qapp, stub_ctx):
    page = WorldMapPage(stub_ctx)
    page.on_shown()
    # Select an Adoulin zone so Port Jeuno isn't kept at 1.0 as selected/route
    page.origin_zone_id = 256  # Western Adoulin
    page.select_zone(256)

    page.set_era_filter("adoulin")
    assert page.node_items[256].opacity() == pytest.approx(1.0)
    assert page.node_items[100].opacity() < 0.5  # West Ronfaure dimmed

    # Endgame filter keeps endgame nodes + their parent entry hubs bright
    page.set_era_filter("endgame")
    assert page.node_items[275].opacity() == pytest.approx(1.0)  # Sortie (endgame)
    assert page.node_items[267].opacity() == pytest.approx(1.0)  # Kamihr Drifts (parent hub of Sortie)


def test_search_input_focus(qapp, stub_ctx):
    page = WorldMapPage(stub_ctx)
    page.on_shown()
    page.search_input.setText("Sortie")
    page._on_search_enter()
    assert page.selected_zone_id == 275


def test_route_finder_ui_highlight(qapp, stub_ctx):
    page = WorldMapPage(stub_ctx)
    page.on_shown()
    page.origin_zone_id = 246  # Port Jeuno
    page.select_zone(267)  # Kamihr Drifts: one Home Point warp

    assert page.active_route is not None
    assert len(page.active_route.steps) == 1
    assert len(page.warp_arc_items) == 1
    assert page.route_steps_box.count() == 1
    row = page.route_steps_box.itemAt(0).widget()
    assert row.wordWrap() and "Kamihr Drifts" in row.text()  # full text, wrapped rather than cut off

    # Uncheck both fast-travel toggles -> walking/portal route
    page.use_hp_chk.setChecked(False)
    page.use_sg_chk.setChecked(False)
    assert page.active_route is not None
    assert len(page.active_route.steps) > 1
    assert len(page.warp_arc_items) == 0


def test_live_player_zone_badge(qapp, stub_ctx):
    page = WorldMapPage(stub_ctx)
    page.on_shown()

    stub_ctx.zone_changed.emit("Kamihr Drifts")
    assert page.live_zone_id == 267
    assert page.origin_zone_id == 267
    assert page.node_items[267].is_live_zone is True
    assert "Kamihr Drifts" in page.live_status_label.text()

    # Unmapped / Mog House zone falls back cleanly to Port Jeuno (246)
    stub_ctx.zone_changed.emit("Residential Area")
    assert page.live_zone_id is None
    assert page.origin_zone_id == 246
    assert "Port Jeuno" in page.live_status_label.text()


def test_arrange_mode_drag_reset(qapp, stub_ctx):
    page = WorldMapPage(stub_ctx)
    page.on_shown()

    jeuno_item = page.node_items[246]
    orig_x, orig_y = jeuno_item.pos().x(), jeuno_item.pos().y()
    assert not bool(jeuno_item.flags() & QGraphicsItem.ItemIsMovable)

    page.toggle_arrange_mode()
    assert page.arrange_mode is True
    assert bool(jeuno_item.flags() & QGraphicsItem.ItemIsMovable)

    jeuno_item.setPos(orig_x + 120.0, orig_y - 80.0)
    page.persist_current_layout()
    assert os.path.isfile(page._override_path)

    page.reset_layout()
    assert not os.path.isfile(page._override_path)
    assert jeuno_item.pos().x() == pytest.approx(orig_x)
    assert jeuno_item.pos().y() == pytest.approx(orig_y)

    # Also test HTML browser export from UI button
    out_html = page.open_in_browser()
    assert os.path.isfile(out_html)
    assert stub_ctx.opened_paths == [out_html]


def test_whole_map_and_escape(qapp, stub_ctx):
    page = WorldMapPage(stub_ctx)
    page.resize(1200, 800)
    page.show()
    page.on_shown()
    qapp.processEvents()
    page.show_whole_map()
    rect = page.scene.itemsBoundingRect()
    visible = page.view.mapToScene(page.view.viewport().rect()).boundingRect()
    assert visible.contains(rect.adjusted(20, 20, -20, -20))

    page.origin_zone_id = 246
    page.select_zone(267)
    page._clear_search_or_selection()  # Esc with an empty search box
    assert page.selected_zone_id == 246
    page.hide()
