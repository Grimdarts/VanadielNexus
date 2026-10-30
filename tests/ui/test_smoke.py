"""The window builds, every page opens, and editing round-trips through the database."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("VN_DATA_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text('{"setup_dismissed": true}')
    from vanadiel_nexus import __version__
    from vanadiel_nexus.ui import theme
    from vanadiel_nexus.ui.context import AppContext
    from vanadiel_nexus.ui.main_window import MainWindow

    ctx = AppContext(__version__)
    from PySide6.QtWidgets import QApplication

    theme.apply(QApplication.instance())
    win = MainWindow(ctx)
    qtbot.addWidget(win)
    win.show()
    return win


def test_every_page_opens(window):
    for page in window.pages:
        window.show_page(page.key)
        assert window.stack.currentWidget() is page
        assert window.page_title.text() == page.title


def test_sidebar_collapses_in_narrow_window(window, qtbot):
    window.resize(950, 700)
    qtbot.waitUntil(lambda: window.sidebar.width() == 64, timeout=2000)
    window.resize(1300, 800)
    qtbot.waitUntil(lambda: window.sidebar.width() == 220, timeout=2000)


def test_gear_goal_step_saves(window):
    gear = window.pages[0]
    gear.tabs.setCurrentIndex(2)
    goals = gear.goals.model_.rows
    if not goals:
        pytest.skip("default database has no goals")
    gear.goals.selectRow(0)
    row = gear.goals.selected_row()
    before = row.get("current", 0)
    gear._step_goal(1)
    assert row["current"] == before + 1
    from vanadiel_nexus.core.database import Database
    saved = Database(window.ctx.data_dir).data["checkpoints"]
    assert any(c["id"] == row["id"] and c["current"] == before + 1 for c in saved)


def test_text_scale_applies(window):
    window.apply_text_scale(1.2)
    assert window.ctx.settings.get("text_scale") == 1.2


def test_guide_counts_materials_from_inventory(window):
    ctx = window.ctx
    ctx.inventory_snapshot = {"Me": [{"name": "Pluton", "count": 900, "bag": "Mog Case"}]}
    ctx.db.data["checkpoints"].append({"id": "g1", "title": "Test goal", "job": "All", "current": 0, "target": 1,
                                       "materials": [{"name": "Pluton", "need": 1500}]})
    ctx.save_db()
    gear = window.pages[0]
    gear.tabs.setCurrentIndex(2)
    gear.job_combo.setCurrentText("All jobs")
    row = next(r for r in gear.goals.model_.rows if r.get("id") == "g1")
    assert round(row["_mat_pct"]) == 60
    gear.goals.select_row(row)
    assert "60%" in gear.guide.bar_label.text()


def test_wishlist_track_as_goal_copies_materials(window):
    ctx = window.ctx
    ctx.db.data["wishlist"].append({"id": "wl-x", "name": "Test Earring", "job": "All",
                                    "materials": [{"name": "Kei's Shard", "need": 3}]})
    ctx.save_db()
    wish = window.pages[1]
    wish.job_combo.setCurrentText("All jobs")
    wish.table.select_row(next(r for r in wish.table.model_.rows if r["id"] == "wl-x"))
    wish._track_as_goal()
    wish._track_as_goal()  # second click must not duplicate
    goals = [g for g in ctx.db.data["checkpoints"] if g.get("fromWishlist") == "wl-x"]
    assert len(goals) == 1 and goals[0]["materials"][0]["need"] == 3


def test_addon_settings_dialog_edits_and_saves(window, tmp_path):
    from PySide6.QtWidgets import QCheckBox, QSpinBox

    from vanadiel_nexus.ui.addon_settings_dialog import AddonSettingsDialog

    folder = tmp_path / "addons" / "demo"
    (folder / "data").mkdir(parents=True)
    xml = folder / "data" / "settings.xml"
    xml.write_text('<?xml version="1.1" ?>\n<settings><global><pos><x>500</x></pos><show>true</show>'
                   "<bg><alpha>72</alpha><blue>0</blue><green>0</green><red>0</red></bg></global></settings>\n")
    dlg = AddonSettingsDialog(window, window.ctx, {"name": "demo", "folder": str(folder),
                                                   "settings_file": str(xml)})
    spin = dlg.tree.itemWidget(dlg.tree.topLevelItem(0).child(0).child(0), 1)
    assert isinstance(spin, QSpinBox)
    spin.setValue(640)
    check = dlg.tree.itemWidget(dlg.tree.topLevelItem(0).child(1), 1)
    assert isinstance(check, QCheckBox)
    check.setChecked(False)
    dlg._save()  # game not connected: writes immediately
    text = xml.read_text()
    assert "<x>640</x>" in text and "<show>false</show>" in text and text.startswith('<?xml version="1.1"')


def test_hotkey_conflict_chip_filters_to_one_key(window, qtbot):
    page = next(p for p in window.pages if p.key == "hotkeys")
    page._scan_done([
        {"norm_key": "F10", "system": "A", "action": "x", "conflict": True},
        {"norm_key": "CTRL+F10", "system": "B", "action": "y", "conflict": True},
        {"norm_key": "F9", "system": "C", "action": "z", "conflict": False},
    ])
    page._focus_key("F10")
    assert page.table.visible_count() == 1
    page._focus_key("")
    assert page.table.visible_count() == 3
