"""Addons startup controls use temporary installs and never a real game connection."""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def page(qtbot, tmp_path, monkeypatch):
    from PySide6.QtCore import QObject, Signal
    from vanadiel_nexus.core.settings import Settings
    from vanadiel_nexus.ui.pages.addons import AddonsPage
    from vanadiel_nexus.ui.widgets import DataTable

    class Events(QObject):
        windower_changed = Signal(str)
        connection_changed = Signal(bool)
        connected = False

    events = Events()
    settings = Settings(str(tmp_path / "data"))
    settings.set("my_addons_dir", str(tmp_path / "my-addons"))
    monkeypatch.setattr(DataTable, "store", settings)
    root = tmp_path / "Windower"
    for name in ("GearSwap", "Included", "XIPivot"):
        folder = root / "addons" / name
        folder.mkdir(parents=True)
        (folder / (name + ".lua")).touch()
    (root / "scripts").mkdir()
    (root / "scripts" / "init.txt").write_text("lua load XIPivot; exec extra.txt\n")
    (root / "scripts" / "extra.txt").write_text("lua load Included\n")
    (root / "settings.xml").write_text(
        '<settings><autoload><addon>GearSwap</addon></autoload></settings>')
    ctx = SimpleNamespace(windower_dir=str(root), settings=settings, bridge=events,
                          windower_changed=events.windower_changed)
    widget = AddonsPage(ctx)
    qtbot.addWidget(widget)
    return widget


@pytest.mark.parametrize("name, source", [("GearSwap", "settings.xml"), ("Included", "scripts/extra.txt")])
def test_managed_startup_toggle_disabled_with_origin(page, name, source):
    from PySide6.QtCore import QPoint, Qt, QTimer
    from PySide6.QtWidgets import QMenu

    row = next(r for r in page.table.model_.rows if r["name"] == name)
    page.table.select_row(row)
    assert not page.autoload_btn.isEnabled()
    assert source in page.autoload_btn.toolTip()
    columns = page.table.model_.columnCount()
    headers = [page.table.model_.headerData(i, Qt.Orientation.Horizontal) for i in range(columns)]
    origin_column = headers.index("Startup source")
    index = page.table.model_.rows.index(row)
    assert source in page.table.model_.data(page.table.model_.index(index, origin_column))
    assert "configured" in page.hint.text().lower()
    assert "live" in page.hint.text().lower()
    captured = []

    def close_menu():
        for menu in page.findChildren(QMenu):
            captured.append(menu.actions()[0].isEnabled())
            menu.close()

    QTimer.singleShot(0, close_menu)
    page._context_menu(QPoint())
    assert captured == [False]


def test_init_managed_startup_can_be_toggled_without_live_connection(page):
    row = next(r for r in page.table.model_.rows if r["name"] == "XIPivot")
    page.table.select_row(row)
    assert page.autoload_btn.isEnabled()
    assert not page.load_btn.isEnabled()
    page._toggle_autoload()
    row = next(r for r in page.table.model_.rows if r["name"] == "XIPivot")
    assert row["autoload"] is False
    page.table.select_row(row)
    page._toggle_autoload()
    row = next(r for r in page.table.model_.rows if r["name"] == "XIPivot")
    assert row["autoload"] is True
    assert row["autoload_sources"] == ["scripts/init.txt"]


def test_toggle_handles_new_external_source_without_claiming_success(page, monkeypatch):
    from pathlib import Path

    row = next(r for r in page.table.model_.rows if r["name"] == "XIPivot")
    page.table.select_row(row)
    xml = Path(page.ctx.windower_dir) / "settings.xml"
    xml.write_text('<settings><autoload><addon>XIPivot</addon></autoload></settings>')
    statuses = []
    monkeypatch.setattr(page, "status", statuses.append)
    page._toggle_autoload()
    assert len(statuses) == 1 and "settings.xml" in statuses[0]
    assert "will not" not in statuses[0]
    row = next(r for r in page.table.model_.rows if r["name"] == "XIPivot")
    page.table.select_row(row)
    assert row["autoload"] is True
    assert not page.autoload_btn.isEnabled()
