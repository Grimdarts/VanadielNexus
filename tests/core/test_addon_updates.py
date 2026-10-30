"""Update checks against a fake GitHub (no network)."""
import hashlib
import os
import zipfile

import pytest

from vanadiel_nexus.core import addon_updates as u


def sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


REMOTE_FILES = {
    "addons/Treasury/Treasury.lua": b"-- treasury v2\n",
    "addons/Treasury/data/settings.xml": b"<defaults/>",
    "addons/findAll/findAll.lua": b"-- findall\n",
}
THIRD_PARTY = {"GearInfo.lua": b"-- gearinfo new\n", "res/Gifts.lua": b"return {}\n"}


def fake_get_json(url):
    if url.endswith("/repos/Someone/GearInfo"):
        return {"default_branch": "master"}
    if "/repos/Windower/Lua/git/trees/nope" in url:
        raise RuntimeError("404")
    if "/repos/Windower/Lua/git/trees/dev" in url:
        return {"tree": [{"path": p, "type": "blob", "sha": sha(d)} for p, d in REMOTE_FILES.items()]}
    if "/repos/Someone/GearInfo/git/trees/master" in url:
        return {"tree": [{"path": p, "type": "blob", "sha": sha(d)} for p, d in THIRD_PARTY.items()]}
    raise AssertionError(url)


def fake_get_bytes(url):
    for path, data in list(REMOTE_FILES.items()):
        if url.endswith("/dev/" + path):
            return data
    for path, data in THIRD_PARTY.items():
        if url.endswith("/master/" + path):
            return data
    raise AssertionError(url)


def addon(tmp_path, name, files):
    folder = tmp_path / "addons" / name
    for rel, data in files.items():
        p = folder / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return {"name": name, "folder": str(folder)}


def test_blob_sha_matches_git(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"hello\n")
    assert u.blob_sha(str(p)) == "ce013625030ba8dba906f756967f9e9ca394464a"  # git hash-object


def test_parse_source_formats():
    assert u.parse_source("Someone/GearInfo") == {"owner": "Someone", "repo": "GearInfo", "path": "", "branch": ""}
    assert u.parse_source("https://github.com/a/b/tree/main/addons/X") == \
        {"owner": "a", "repo": "b", "path": "addons/X", "branch": "main"}
    assert u.parse_source("a/b/sub/dir@dev")["path"] == "sub/dir"
    assert u.parse_source("not a source") is None


def test_scan_finds_outdated_current_and_unknown(tmp_path):
    addons = [
        addon(tmp_path, "Treasury", {"Treasury.lua": b"-- treasury v1\n", "data/settings.xml": b"<mine/>"}),
        addon(tmp_path, "findAll", {"findAll.lua": b"-- findall\n"}),
        addon(tmp_path, "MyThing", {"MyThing.lua": b"x"}),
    ]
    res = u.scan(addons, {}, fake_get_json)
    assert res["Treasury"]["status"] == "update_available" and res["Treasury"]["changed"] == ["Treasury.lua"]
    assert res["findAll"]["status"] == "up_to_date"
    assert res["MyThing"]["status"] == "no_source"


def test_update_backs_up_verifies_and_keeps_settings(tmp_path):
    a = addon(tmp_path, "Treasury", {"Treasury.lua": b"-- treasury v1\n", "data/settings.xml": b"<mine/>"})
    res = u.scan([a], {}, fake_get_json)["Treasury"]
    backup = u.apply_update(a["folder"], res, str(tmp_path / "backups"), fake_get_bytes)
    assert open(os.path.join(a["folder"], "Treasury.lua"), "rb").read() == b"-- treasury v2\n"
    assert open(os.path.join(a["folder"], "data", "settings.xml"), "rb").read() == b"<mine/>"
    assert "Treasury/Treasury.lua" in zipfile.ZipFile(backup).namelist()
    assert u.scan([a], {}, fake_get_json)["Treasury"]["status"] == "up_to_date"


def test_tampered_download_changes_nothing(tmp_path):
    a = addon(tmp_path, "Treasury", {"Treasury.lua": b"-- treasury v1\n"})
    res = u.scan([a], {}, fake_get_json)["Treasury"]
    with pytest.raises(RuntimeError):
        u.apply_update(a["folder"], res, str(tmp_path / "backups"), lambda url: b"evil")
    assert open(os.path.join(a["folder"], "Treasury.lua"), "rb").read() == b"-- treasury v1\n"
    assert not (tmp_path / "backups").exists()


def test_third_party_source_uses_its_own_repo(tmp_path):
    a = addon(tmp_path, "GearInfo", {"GearInfo.lua": b"-- gearinfo old\n", "res/Gifts.lua": b"return {}\n"})
    res = u.scan([a], {"gearinfo": "Someone/GearInfo"}, fake_get_json)["GearInfo"]
    assert res["status"] == "update_available" and res["changed"] == ["GearInfo.lua"]
    assert res["source"]["branch"] == "master"


def test_network_errors_are_reported_not_raised(tmp_path):
    a = addon(tmp_path, "Treasury", {"Treasury.lua": b"x"})

    def down(url):
        raise OSError("offline")

    assert u.scan([a], {}, down)["Treasury"]["status"] == "error"
