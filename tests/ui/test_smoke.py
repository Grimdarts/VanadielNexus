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
    qtbot.wait(50)
    assert window.sidebar.width() == 64
    window.resize(1300, 800)
    qtbot.wait(50)
    assert window.sidebar.width() == 220


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
