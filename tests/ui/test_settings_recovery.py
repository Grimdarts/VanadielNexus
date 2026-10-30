"""Settings recovery messages reflect real, temporary database recovery outcomes."""
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QLabel

from vanadiel_nexus.core.database import Database
from vanadiel_nexus.core.settings import Settings
from vanadiel_nexus.ui.pages.settings import SettingsPage


@pytest.mark.parametrize("primary, backup, source", [
    (b"{broken", None, "defaults"),
    (b"{broken", b"[]", "defaults"),
    (b"{broken", b'{"schema_version": 2}', "backup"),
    (None, b'{"schema_version": 2}', "backup"),
    (None, b"{broken", "defaults"),
    (None, None, None),
    (b'{"schema_version": 2}', None, None),
])
def test_settings_recovery_warning(qtbot, tmp_path, primary, backup, source):
    class Events(QObject):
        windower_changed = Signal(str)

    if primary is not None:
        (tmp_path / "ffxi_database.json").write_bytes(primary)
    if backup is not None:
        (tmp_path / "ffxi_database.json.bak").write_bytes(backup)
    events = Events()
    db = Database(str(tmp_path))
    ctx = SimpleNamespace(db=db, data_dir=str(tmp_path), settings=Settings(str(tmp_path)),
                          version="test", windower_dir="", windower_changed=events.windower_changed)
    page = SettingsPage(ctx)
    qtbot.addWidget(page)
    warnings = [label.text() for label in page.findChildren(QLabel)
                if "#F59E0B" in label.styleSheet()]

    if source is None:
        assert warnings == []
        assert db.recovery_source is None
        assert db.unreadable_path is None
        return

    assert len(warnings) == 1
    warning = warnings[0]
    if source == "defaults":
        assert "defaults were loaded" in warning
        assert "no usable backup" in warning
        assert "last good copy was loaded" not in warning
    else:
        assert "backup was loaded" in warning
        assert "defaults were loaded" not in warning
    assert db.recovery_source == source
    if primary is not None:
        assert "unreadable file was kept" in warning
        assert db.unreadable_path is not None
        assert db.unreadable_path in warning
        from pathlib import Path
        assert Path(db.unreadable_path).read_bytes() == primary
    else:
        assert "primary database was missing" in warning
        assert "unreadable file was kept" not in warning
        assert db.unreadable_path is None
