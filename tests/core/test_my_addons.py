import os

import pytest

from vanadiel_nexus.core import my_addons as m


def test_create_lists_and_installs_without_touching_data(tmp_path):
    my_dir, wdir = str(tmp_path / "mine"), str(tmp_path / "Windower4")
    folder = m.create(my_dir, "PartyHelper", "Jason")
    assert "_addon.name = 'PartyHelper'" in open(os.path.join(folder, "PartyHelper.lua")).read()

    listed = m.list_my_addons(my_dir, wdir)
    assert listed[0]["name"] == "PartyHelper" and not listed[0]["installed"]

    # An installed copy with in-game settings in data/ must keep them
    os.makedirs(os.path.join(wdir, "addons", "PartyHelper", "data"))
    open(os.path.join(wdir, "addons", "PartyHelper", "data", "settings.xml"), "w").write("<mine/>")
    os.makedirs(os.path.join(folder, "data"))
    open(os.path.join(folder, "data", "settings.xml"), "w").write("<template/>")
    copied = m.install(folder, wdir)
    assert copied == ["PartyHelper.lua"]
    assert open(os.path.join(wdir, "addons", "PartyHelper", "data", "settings.xml")).read() == "<mine/>"
    assert m.list_my_addons(my_dir, wdir)[0]["up_to_date"]

    with open(os.path.join(folder, "PartyHelper.lua"), "a") as f:
        f.write("-- change\n")
    assert not m.list_my_addons(my_dir, wdir)[0]["up_to_date"]
    assert m.install(folder, wdir) == ["PartyHelper.lua"]
    assert m.install(folder, wdir) == []


def test_names_are_validated_and_never_overwrite(tmp_path):
    with pytest.raises(ValueError):
        m.create(str(tmp_path), "bad name!")
    m.create(str(tmp_path), "Good")
    with pytest.raises(FileExistsError):
        m.create(str(tmp_path), "Good")


def test_folders_without_main_lua_are_ignored(tmp_path):
    (tmp_path / "Notes").mkdir()
    assert m.list_my_addons(str(tmp_path)) == []
