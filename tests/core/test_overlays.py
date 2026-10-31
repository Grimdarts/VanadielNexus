"""Overlay layout core: finding addon windows, reading and writing every storage style, screen math."""
import os

import pytest

from vanadiel_nexus.core import overlays

XML = '<?xml version="1.1" ?>\n<settings>\n{}\n</settings>\n'


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


@pytest.fixture
def win(tmp_path):
    a = tmp_path / "addons"
    write(a / "PetTP/PetTP.lua", "")
    write(a / "PetTP/data/settings.xml", XML.format(
        "<global><pos><x>1280</x><y>1063</y></pos><flags><right>false</right></flags></global>"
        "<alice><pos><x>1596</x><y>1009.5</y></pos></alice>"))
    write(a / "distance/distance.lua", "")
    write(a / "distance/data/settings.xml", XML.format(
        "<global><pos><x>-178</x><y>21</y></pos><flags><right>true</right></flags></global>"))
    write(a / "xivbar/xivbar.lua", "")
    write(a / "xivbar/data/settings.xml", XML.format("<global><Bars><OffsetX>0</OffsetX><OffsetY>-200</OffsetY></Bars></global>"))
    write(a / "XIVPetBar/XIVPetBar.lua", "")
    write(a / "XIVPetBar/data/settings.xml", XML.format("<global><OffsetX>0</OffsetX><OffsetY>0</OffsetY></global>"))
    write(a / "parse/parse.lua", "dofile(name..'_positions.lua')")
    write(a / "parse/data/settings.xml", XML.format(
        "<global><display>" + "".join(f"<{k}><pos><x>{i}</x><y>{i}</y></pos></{k}>"
                                      for i, k in enumerate(("melee", "ranged", "magic", "defense"))) + "</display></global>"))
    write(a / "GearSwap/gearswap.lua", "")
    write(a / "GearSwap/data/Alice-SMN-hud.lua", "return {x=1476, y=234}\n")
    write(a / "MyHud/MyHud.lua", "")
    write(a / "MyHud/data/settings.xml", XML.format("<global><box><pos><x>5</x><y>6</y></pos></box></global>"))
    write(a / "TParty/TParty.lua", "")
    write(a / "TParty/data/settings.xml", XML.format("<global><pos><x>1</x><y>1</y></pos></global>"))
    return str(tmp_path)


def by_id(ovs):
    return {o.id: o for o in ovs}


def test_finds_known_and_discovered_windows_but_not_unmovable(win):
    ids = by_id(overlays.find_overlays(win, "Alice"))
    assert {"PetTP", "distance", "xivbar", "XIVPetBar", "parse.melee", "GearSwap.smn_hud", "MyHud.box"} <= set(ids)
    assert ids["MyHud.box"].discovered
    assert not any(i.startswith("TParty") for i in ids)
    # The SMN HUD file is optional: another character without it has no such window.
    assert "GearSwap.smn_hud" not in by_id(overlays.find_overlays(win, "Bob"))


def test_reads_character_section_over_global_and_each_file_style(win):
    pos = overlays.read_all(overlays.find_overlays(win, "Alice"), "Alice")
    assert pos["PetTP"] == [1596, 1009.5]
    assert pos["distance"] == [-178, 21]
    assert pos["xivbar"] == [0, -200]
    assert pos["parse.ranged"] == [1, 1]  # no positions file yet: falls back to settings.xml
    assert pos["GearSwap.smn_hud"] == [1476, 234]
    assert overlays.read_all(overlays.find_overlays(win, "Bob"), "Bob")["PetTP"] == [1280, 1063]


def test_writes_into_the_characters_section_and_leaves_global_alone(win):
    ovs = overlays.find_overlays(win, "Bob")
    changed = overlays.write_positions(ovs, "Bob", {"PetTP": [10, 20]}, backup=False)
    assert len(changed) == 1
    text = open(os.path.join(win, "addons/PetTP/data/settings.xml"), encoding="utf-8").read()
    assert text.startswith('<?xml version="1.1" ?>')
    assert "<bob>" in text and "<x>1280</x>" in text
    assert overlays.read_position(by_id(ovs)["PetTP"], "Bob") == [10, 20]
    assert overlays.read_position(by_id(ovs)["PetTP"], "Alice") == [1596, 1009.5]
    assert not [f for f in os.listdir(os.path.join(win, "addons/PetTP/data")) if f.endswith(".bak")]


def test_global_only_addons_and_unchanged_positions(win):
    ovs = overlays.find_overlays(win, "Alice")
    assert overlays.write_positions(ovs, "Alice", {"xivbar": [0, -200]}) == []
    overlays.write_positions(ovs, "Alice", {"xivbar": [30, -150]}, backup=True)
    text = open(os.path.join(win, "addons/xivbar/data/settings.xml"), encoding="utf-8").read()
    assert "<alice>" not in text and "<OffsetX>30</OffsetX>" in text
    assert [f for f in os.listdir(os.path.join(win, "addons/xivbar/data")) if f.endswith(".bak")]


def test_parse_positions_file_is_created_with_every_window_then_updated(win):
    ovs = overlays.find_overlays(win, "Alice")
    overlays.write_positions(ovs, "Alice", {"parse.melee": [900, 600]})
    path = os.path.join(win, "addons/parse/data/Alice_positions.lua")
    text = open(path, encoding="utf-8").read()
    assert "['melee'] = {x = 900, y = 600}" in text and "['defense'] = {x = 3, y = 3}" in text
    overlays.write_positions(ovs, "Alice", {"parse.magic": [7, 8]})
    pos = overlays.read_all(ovs, "Alice")
    assert pos["parse.melee"] == [900, 600] and pos["parse.magic"] == [7, 8]


def test_unpatched_parse_uses_settings_xml(win):
    write(os.path.join(win, "addons/parse/parse.lua"), "-- stock parse")
    ovs = overlays.find_overlays(win, "Alice")
    overlays.write_positions(ovs, "Alice", {"parse.melee": [42, 43]}, backup=False)
    assert not os.path.exists(os.path.join(win, "addons/parse/data/Alice_positions.lua"))
    assert overlays.read_all(ovs, "Alice")["parse.melee"] == [42, 43]


def test_smn_hud_file(win):
    ovs = overlays.find_overlays(win, "Alice")
    overlays.write_positions(ovs, "Alice", {"GearSwap.smn_hud": [100.4, 50]})
    assert open(os.path.join(win, "addons/GearSwap/data/Alice-SMN-hud.lua")).read() == "return {x=100, y=50}\n"


def test_screen_math_round_trips_for_every_anchor(win):
    ovs = overlays.find_overlays(win, "Alice")
    pos = overlays.read_all(ovs, "Alice")
    scr = overlays.Screen(ovs, "Alice", 1920, 1080)
    assert scr.to_screen("distance", [-178, 21], pos) == (1920 - 178 - 70, 21)
    assert scr.to_screen("xivbar", [0, -200], pos) == (960 - 236, 1080 - 60 - 200)
    pet = scr.to_screen("XIVPetBar", [0, 0], pos)
    assert pet == (960 - 150, 1080 - 260 + 47)
    for oid in ("distance", "xivbar", "XIVPetBar", "PetTP", "MyHud.box"):
        s = scr.to_screen(oid, pos[oid], pos)
        assert scr.from_screen(oid, s, pos) == [round(v) for v in pos[oid]]
    # The pet bar rides along when xivbar moves.
    moved = dict(pos, xivbar=[100, -200])
    assert scr.to_screen("XIVPetBar", [0, 0], moved)[0] == pet[0] + 100


def test_layout_store_falls_back_to_default(tmp_path):
    store = overlays.LayoutStore(str(tmp_path))
    store.put("Alice", "Default", {"positions": {"a": [1, 2], "b": [3, 4]}, "shown": {"A": True}})
    store.put("Alice", "SMN", {"positions": {"a": [9, 9]}, "shown": {"A": False}})
    assert store.get("Alice", "SMN") == {"positions": {"a": [9, 9], "b": [3, 4]}, "shown": {"A": False}}
    assert store.get("Alice", "BLU")["positions"]["a"] == [1, 2]
    assert overlays.LayoutStore(str(tmp_path)).jobs("Alice") == ["SMN"]
    store.remove("Alice", "SMN")
    assert not store.has("Alice", "SMN")


def test_plan_switch_only_touches_what_changes(win):
    ovs = overlays.find_overlays(win, "Alice")
    current = {"PetTP": [1, 1], "distance": [2, 2], "xivbar": [0, 0]}
    target = {"PetTP": [5, 5], "distance": [2, 2], "xivbar": [0, 10]}
    plan = overlays.plan_switch(current, target, {"PetTP": True, "xivbar": True, "distance": True},
                                {"PetTP": False, "xivbar": True, "distance": True}, ovs)
    assert plan["write"] == {"PetTP": [5, 5], "xivbar": [0, 10]}
    assert plan["unload"] == ["PetTP"] and plan["load"] == []
    assert plan["reload"] == ["xivbar"]
    # Unknown shown state on either side never loads or unloads anything.
    plan = overlays.plan_switch(current, target, {}, {"PetTP": False}, ovs)
    assert plan["unload"] == [] and plan["reload"] == []
