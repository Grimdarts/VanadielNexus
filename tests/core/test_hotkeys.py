"""Conflict rules, against a Windower tree shaped like a real player's (file names from Jason's setup)."""
import os

from vanadiel_nexus.core import hotkeys


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def bind(key, cmd):
    return f"send_command('bind {key} {cmd}')\n"


def make_windower(root):
    gs = os.path.join(root, "addons", "GearSwap")
    write(os.path.join(root, "scripts", "init.txt"),
          "// comment line\nbind f12 showfps\nbind ^f10 drawdistance set 1\n")
    write(os.path.join(root, "settings.xml"), "<settings>\n  <consolekey>Insert</consolekey>\n</settings>\n")
    write(os.path.join(gs, "libs", "Mote-Globals.lua"), bind("f9", "gs c cycle OffenseMode") + bind("^f10", "gs c cycle PDT"))
    # Active job files: each binds the same keys, but only one loads at a time
    write(os.path.join(gs, "data", "Someonesmall_BLU.lua"), bind("^e", "input /item") + bind("f9", "gs c toggle TP"))
    write(os.path.join(gs, "data", "Someonesmall-SMN.lua"), bind("^e", "input /item"))
    write(os.path.join(gs, "data", "Someonesmall-SMN-sets.lua"), bind("@w", "gs c toggle tplock"))
    write(os.path.join(gs, "data", "Someonesmall_SCH.lua"), bind("^e", "input /item"))
    write(os.path.join(gs, "data", "user-globals.lua"), "include('x')\n")
    # Backups GearSwap never loads
    write(os.path.join(gs, "data", "Other LUAs", "SpicyRyan_BLU.lua"), bind("^e", "input /item") + bind("f12", "gs c idle"))
    write(os.path.join(gs, "data", "Other LUAs", "BLU.lua"), bind("^e", "input /item"))
    return root


def by(entries, system_part, key):
    return [e for e in entries if system_part in e["system"] and e["norm_key"] == hotkeys.normalize_hotkey_string(key)]


def test_job_files_never_conflict_with_each_other(tmp_path):
    entries = hotkeys.scan_all_hotkeys_and_conflicts(make_windower(str(tmp_path)))
    for e in by(entries, "Someonesmall", "^e"):
        assert not e["conflict"], e["system"]


def test_subfolder_files_are_inactive_and_never_conflict(tmp_path):
    entries = hotkeys.scan_all_hotkeys_and_conflicts(make_windower(str(tmp_path)))
    spicy = by(entries, "SpicyRyan_BLU", "f12")
    assert spicy and spicy[0]["inactive"] and not spicy[0]["conflict"]
    assert by(entries, "(BLU.lua)", "^e")[0]["inactive"]


def test_character_folder_is_loadable(tmp_path):
    root = make_windower(str(tmp_path))
    data = os.path.join(root, "addons", "GearSwap", "data")
    write(os.path.join(data, "Someonesmall", "Someonesmall_RUN.lua"), bind("^r", "x"))
    scope = hotkeys.classify_gearswap_lua(os.path.join(data, "Someonesmall", "Someonesmall_RUN.lua"), data)
    assert scope == {"scope": "job", "job": "RUN"}


def test_job_file_overriding_mote_default_is_not_a_conflict(tmp_path):
    entries = hotkeys.scan_all_hotkeys_and_conflicts(make_windower(str(tmp_path)))
    blu_f9 = by(entries, "Someonesmall_BLU", "f9")[0]
    # Still clashes with the game's own F9 key, but not with Mote-Globals
    assert "Mote-Globals" not in blu_f9["conflict_summary"]


def test_init_txt_vs_gearswap_is_a_real_conflict(tmp_path):
    entries = hotkeys.scan_all_hotkeys_and_conflicts(make_windower(str(tmp_path)))
    init = by(entries, "init.txt", "^f10")
    assert init and init[0]["conflict"]
    assert "Mote-Globals" in init[0]["conflict_summary"]


def test_inactive_init_bind_has_no_fake_entries(tmp_path):
    entries = hotkeys.scan_all_hotkeys_and_conflicts(make_windower(str(tmp_path)))
    init_keys = {e["norm_key"] for e in entries if e["system"] == "Windower init.txt"}
    assert init_keys == {hotkeys.normalize_hotkey_string("f12"), hotkeys.normalize_hotkey_string("^f10")}


def test_missing_windower_returns_only_builtin_entries(tmp_path):
    entries = hotkeys.scan_all_hotkeys_and_conflicts(str(tmp_path / "nowhere"))
    assert all(e["system"] in ("FFXI Base Game", "Windower Core (settings.xml)") for e in entries)


def test_console_key_line_is_read_from_settings(tmp_path):
    entries = hotkeys.scan_all_hotkeys_and_conflicts(make_windower(str(tmp_path)))
    core = [e for e in entries if "settings.xml" in e["system"]][0]
    assert core["raw_key"] == "Insert" and core["line_num"] == 2


def test_normalize_modifiers():
    assert hotkeys.normalize_hotkey_string("^f10") == hotkeys.normalize_hotkey_string("Ctrl+F10")
    assert hotkeys.normalize_hotkey_string("!f10") == hotkeys.normalize_hotkey_string("Alt+F10")


def test_disable_and_rebind_edit_the_source_line_with_backup(tmp_path):
    root = make_windower(str(tmp_path))
    entries = hotkeys.scan_all_hotkeys_and_conflicts(root)
    init_f12 = by(entries, "init.txt", "f12")[0]
    assert hotkeys.rebind(init_f12, "Ctrl+F7")
    text = open(os.path.join(root, "scripts", "init.txt")).read()
    assert "bind ^f7 showfps" in text.lower()
    entries = hotkeys.scan_all_hotkeys_and_conflicts(root)
    moved = by(entries, "init.txt", "^f7")[0]
    assert hotkeys.disable_bind(moved)
    assert "// [disabled" in open(os.path.join(root, "scripts", "init.txt")).read()
    assert [f for f in os.listdir(os.path.join(root, "scripts")) if f.endswith(".bak")]
