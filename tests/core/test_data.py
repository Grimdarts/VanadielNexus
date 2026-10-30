"""Database, settings, JSON safety, Windower folder handling, setup checks and updater helpers."""
import json
import os

from vanadiel_nexus.core import database, jsonfile, setup_check, updater, windower
from vanadiel_nexus.core.settings import Settings


# --- jsonfile ---------------------------------------------------------------
def test_write_keeps_previous_copy_as_bak(tmp_path):
    p = str(tmp_path / "x.json")
    jsonfile.write_json(p, {"v": 1})
    jsonfile.write_json(p, {"v": 2})
    assert json.load(open(p))["v"] == 2
    assert json.load(open(p + ".bak"))["v"] == 1


def test_read_falls_back_to_bak_when_main_is_corrupt(tmp_path):
    p = str(tmp_path / "x.json")
    jsonfile.write_json(p, {"v": 1})
    jsonfile.write_json(p, {"v": 2})
    open(p, "w").write("{broken")
    assert jsonfile.read_json(p) == {"v": 1}


# --- database ---------------------------------------------------------------
def test_new_database_is_seeded_from_defaults(tmp_path):
    db = database.Database(str(tmp_path))
    assert db.data["schema_version"] == database.SCHEMA_VERSION
    assert db.data["jse_by_job"]


def test_v1_database_is_migrated_and_backed_up(tmp_path):
    v1 = {"checkpoints": [{"id": "c", "category": "AEONIC WEAPON (WAR)", "title": "Chango"}],
          "jse_by_job": {"XYZ": []}, "rema_weapons": [], "wishlist": [{"id": "w", "slot": "Earring (SMN)"}],
          "catalog_db": {}, "player_extra": "kept"}
    json.dump(v1, open(tmp_path / "ffxi_database.json", "w"))
    db = database.Database(str(tmp_path))
    assert db.data["checkpoints"][0]["job"] == "WAR"
    assert db.data["wishlist"][0]["job"] == "SMN"
    assert db.data["player_extra"] == "kept"
    assert "XYZ" in db.data["jse_by_job"] and "BLU" in db.data["jse_by_job"]
    assert json.load(open(tmp_path / "ffxi_database.v1-backup.json")) == v1


def test_corrupt_database_without_backup_is_preserved_not_lost(tmp_path):
    open(tmp_path / "ffxi_database.json", "w").write("{not json")
    db = database.Database(str(tmp_path))
    assert db.recovered_from_backup
    assert open(tmp_path / "ffxi_database.json.unreadable").read() == "{not json"


def test_save_roundtrip(tmp_path):
    db = database.Database(str(tmp_path))
    db.data["wishlist"].append({"id": "new", "name": "Test Ring", "job": "BLU"})
    db.save()
    assert any(w["id"] == "new" for w in database.Database(str(tmp_path)).data["wishlist"])


# --- settings ---------------------------------------------------------------
def test_settings_defaults_and_persistence(tmp_path):
    s = Settings(str(tmp_path))
    assert s.get("text_scale") == 1.0
    s.set("text_scale", 1.2)
    assert Settings(str(tmp_path)).get("text_scale") == 1.2


# --- windower ---------------------------------------------------------------
def make_windower(root, init="lua load XIPivot\n// lua load Commented\n"):
    os.makedirs(os.path.join(root, "scripts"))
    open(os.path.join(root, "windower.exe"), "w").close()
    open(os.path.join(root, "scripts", "init.txt"), "w").write(init)
    for name in ("XIPivot", "GearSwap", "libs"):
        os.makedirs(os.path.join(root, "addons", name, "data"))
        if name != "libs":
            open(os.path.join(root, "addons", name, f"{name}.lua"), "w").close()
    open(os.path.join(root, "addons", "GearSwap", "data", "settings.xml"), "w").write("<settings/>")
    os.makedirs(os.path.join(root, "plugins"))
    open(os.path.join(root, "plugins", "Timers.dll"), "w").close()
    return root


def test_find_prefers_saved_then_sibling(tmp_path):
    w = make_windower(str(tmp_path / "Windower4"))
    app = str(tmp_path / "VanadielNexus")
    os.makedirs(app)
    assert windower.find_windower_dir("", app) == w
    assert windower.find_windower_dir(str(tmp_path / "missing"), app) == w


def test_autoloads_ignore_comments(tmp_path):
    w = make_windower(str(tmp_path / "W"))
    assert windower.autoloads(w)["addons"] == {"xipivot"}


def test_list_addons_and_plugins(tmp_path):
    w = make_windower(str(tmp_path / "W"))
    addons = {a["name"]: a for a in windower.list_addons(w)}
    assert set(addons) == {"GearSwap", "XIPivot"}
    assert addons["XIPivot"]["autoload"] and not addons["GearSwap"]["autoload"]
    assert addons["GearSwap"]["settings_file"].endswith("settings.xml")
    assert [p["name"] for p in windower.list_plugins(w)] == ["Timers"]


def test_set_autoload_adds_and_removes_with_backup(tmp_path):
    w = make_windower(str(tmp_path / "W"))
    windower.set_autoload(w, "GearSwap", "addons", True)
    assert "gearswap" in windower.autoloads(w)["addons"]
    windower.set_autoload(w, "XIPivot", "addons", False)
    assert "xipivot" not in windower.autoloads(w)["addons"]
    text = open(windower.init_txt_path(w)).read()
    assert "// lua load Commented" in text
    assert len([f for f in os.listdir(os.path.join(w, "scripts")) if f.endswith(".bak")]) >= 1


def test_set_autoload_noop_writes_nothing(tmp_path):
    w = make_windower(str(tmp_path / "W"))
    windower.set_autoload(w, "XIPivot", "addons", True)
    assert not [f for f in os.listdir(os.path.join(w, "scripts")) if f.endswith(".bak")]


# --- setup checks -----------------------------------------------------------
def test_setup_checks_progress(tmp_path):
    w = make_windower(str(tmp_path / "W"))
    steps = setup_check.run_checks(w)
    assert setup_check.summary(steps) == (1, 3)
    setup_check.install_addon(w)
    windower.set_autoload(w, windower.ADDON_NAME, "addons", True)
    assert setup_check.summary(setup_check.run_checks(w)) == (3, 3)


def test_setup_checks_without_windower(tmp_path):
    steps = setup_check.run_checks(str(tmp_path / "none"))
    assert setup_check.summary(steps) == (0, 3)


# --- updater ----------------------------------------------------------------
def test_version_compare():
    assert updater.is_newer("v2.0.1", "2.0.0")
    assert updater.is_newer("2.10.0", "2.9.9")
    assert not updater.is_newer("2.0.0", "2.0.0")


def test_pick_asset_is_case_insensitive():
    rel = {"assets": [{"name": "notes.txt"}, {"name": "VanadielNexus.exe", "browser_download_url": "u"}]}
    assert updater.pick_asset(rel)["browser_download_url"] == "u"
    assert updater.pick_asset({"assets": []}) is None


def test_swap_script_moves_then_relaunches():
    s = updater.swap_script(r"C:\a\VN.exe.new", r"C:\a\VN.exe")
    assert s.index("move /Y") < s.index('start ""') and "del" in s
