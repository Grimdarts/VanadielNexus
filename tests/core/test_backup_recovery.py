"""Recovery must preserve player files; all fixtures live under tmp_path."""
import json

import pytest

from vanadiel_nexus.core.database import Database


@pytest.mark.parametrize("invalid", [
    [], None, 7, {"wishlist": [None]}, {"checkpoints": [1]},
    {"jse_by_job": {"WAR": None}}, {"wishlist": [{"slot": None}]},
    {"checkpoints": [{"category": 3}]},
])
def test_invalid_database_shape_recovers_good_backup(tmp_path, invalid):
    primary = tmp_path / "ffxi_database.json"
    backup = tmp_path / "ffxi_database.json.bak"
    rejected = json.dumps(invalid).encode("utf-8")
    original = b'{"schema_version": 2, "player_extra": "kept"}'
    primary.write_bytes(rejected)
    backup.write_bytes(original)

    db = Database(str(tmp_path))

    assert db.data["player_extra"] == "kept"
    assert db.recovered_from_backup is True
    assert backup.read_bytes() == original
    assert (tmp_path / "ffxi_database.json.unreadable").read_bytes() == rejected


@pytest.mark.parametrize("backup_bytes", [None, b"{broken backup", b"[]"])
def test_unrecoverable_files_are_preserved_without_claiming_backup_recovery(tmp_path, backup_bytes):
    primary = tmp_path / "ffxi_database.json"
    backup = tmp_path / "ffxi_database.json.bak"
    evidence = tmp_path / "ffxi_database.json.unreadable"
    primary.write_bytes(b"{new corruption")
    if backup_bytes is not None:
        backup.write_bytes(backup_bytes)
    evidence.write_bytes(b"older corruption")

    db = Database(str(tmp_path))

    assert evidence.read_bytes() == b"older corruption"
    assert (tmp_path / "ffxi_database.json.unreadable.1").read_bytes() == b"{new corruption"
    if backup_bytes is None:
        assert not backup.exists()
    else:
        assert backup.read_bytes() == backup_bytes
    assert db.recovered_from_backup is False
    assert json.loads(primary.read_text(encoding="utf-8")) == db.data


def test_backup_recovery_preserves_corrupt_primary_and_good_backup(tmp_path):
    primary = tmp_path / "ffxi_database.json"
    backup = tmp_path / "ffxi_database.json.bak"
    corrupt = b'{broken player data\xff'
    original = b'{"player_extra": "valuable", "schema_version": 2}'
    primary.write_bytes(corrupt)
    backup.write_bytes(original)

    db = Database(str(tmp_path))

    assert db.data["player_extra"] == "valuable"
    assert db.recovered_from_backup is True
    assert backup.read_bytes() == original
    assert (tmp_path / "ffxi_database.json.unreadable").read_bytes() == corrupt
    assert json.loads(primary.read_text(encoding="utf-8")) == db.data


def test_repeated_recovery_preserves_each_rejected_primary(tmp_path):
    primary = tmp_path / "ffxi_database.json"
    backup = tmp_path / "ffxi_database.json.bak"
    original = b'{"schema_version": 2, "player_extra": "kept"}'
    backup.write_bytes(original)

    for suffix, rejected in (("", b"{first"), (".1", b"{second")):
        primary.write_bytes(rejected)
        assert Database(str(tmp_path)).recovered_from_backup is True
        assert (tmp_path / ("ffxi_database.json.unreadable" + suffix)).read_bytes() == rejected
        assert backup.read_bytes() == original

    assert (tmp_path / "ffxi_database.json.unreadable").read_bytes() == b"{first"
    assert Database(str(tmp_path)).recovered_from_backup is False
    assert backup.read_bytes() == original


def test_missing_primary_recovers_backup_without_creating_corrupt_evidence(tmp_path):
    backup = tmp_path / "ffxi_database.json.bak"
    original = b'{"player_extra": "legacy backup"}'
    backup.write_bytes(original)

    db = Database(str(tmp_path))

    assert db.recovered_from_backup is True
    assert db.data["player_extra"] == "legacy backup"
    assert backup.read_bytes() == original
    assert not list(tmp_path.glob("*.unreadable*"))
    assert json.loads((tmp_path / "ffxi_database.json").read_text(encoding="utf-8")) == db.data
