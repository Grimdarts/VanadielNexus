"""Layout manager and page: saving, switching with the job, in-game layout mode, game link checks."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.core.test_overlays import win  # noqa: F401,E402  (fake Windower folder fixture)
from vanadiel_nexus.core import overlays  # noqa: E402


@pytest.fixture
def ctx(qapp, tmp_path, monkeypatch, win):
    data = tmp_path / "vn-data"
    monkeypatch.setenv("VN_DATA_DIR", str(data))
    from vanadiel_nexus.ui.context import AppContext
    from vanadiel_nexus.ui.layout_manager import LayoutManager
    import vanadiel_nexus.ui.layout_manager as lm
    monkeypatch.setattr(lm, "UNLOAD_SETTLE_MS", 10)
    os.makedirs(os.path.join(win, "scripts"), exist_ok=True)
    with open(os.path.join(win, "scripts", "init.txt"), "w") as f:
        f.write("lua load PetTP\nlua load distance\nlua load xivbar\n")
    c = AppContext("test")
    c.windower_dir = win
    c.settings.set("layout_character", "Alice")
    c.bridge.sent = []
    c.bridge.send = c.bridge.sent.append
    c.layouts = LayoutManager(c)
    yield c
    c.bridge._sock.close()


def pettp(win, char="Alice"):
    return overlays.read_all(overlays.find_overlays(win, char), char)["PetTP"]


def game(ctx, job):
    ctx.bridge.connected = True
    ctx.bridge.state = {"player_name": "Alice", "main_job": job, "ui_x_res": 1920, "ui_y_res": 1080}
    ctx.bridge.state_received.emit(ctx.bridge.state)


def test_default_layout_is_what_is_on_screen_now(ctx, win):
    layout = ctx.layouts.layout_for("SMN")
    assert layout["positions"]["PetTP"] == [1596, 1009.5]
    assert ctx.layouts.store.has("Alice", "Default")


def test_saving_offline_writes_files_for_the_last_job(ctx, win):
    ctx.settings.set("layout_last_job", "SMN")
    layout = ctx.layouts.layout_for("SMN")
    layout["positions"]["PetTP"] = [10, 20]
    ctx.layouts.save_layout("SMN", layout)
    assert pettp(win) == [10, 20]
    layout = ctx.layouts.layout_for("BLU")
    layout["positions"]["PetTP"] = [30, 40]
    ctx.layouts.save_layout("BLU", layout)
    assert pettp(win) == [10, 20]  # BLU isn't the job the files are set up for


def test_job_change_moves_windows_and_hides_per_job(ctx, win, qtbot):
    smn = ctx.layouts.layout_for("SMN")
    smn["positions"]["PetTP"] = [111, 222]
    smn["shown"]["PetTP"] = True
    ctx.layouts.store.put("Alice", "SMN", smn)
    blu = ctx.layouts.layout_for("BLU")
    blu["shown"]["PetTP"] = False
    ctx.layouts.store.put("Alice", "BLU", blu)

    game(ctx, "BLU")  # first word from the game: nothing moves
    assert ctx.bridge.sent == [] and pettp(win) == [1596, 1009.5]
    game(ctx, "SMN")
    assert "ADDON|unload|PetTP" not in ctx.bridge.sent  # hidden on BLU: just load it in its SMN spot
    qtbot.waitUntil(lambda: pettp(win) == [111, 222], timeout=2000)
    assert "ADDON|load|PetTP" in ctx.bridge.sent
    ctx.bridge.sent.clear()
    game(ctx, "BLU")
    qtbot.waitUntil(lambda: pettp(win) == [1596, 1009.5], timeout=2000)
    assert ctx.bridge.sent[0] == "ADDON|unload|PetTP" and "ADDON|load|PetTP" not in ctx.bridge.sent


def test_switch_with_job_can_be_turned_off(ctx, win):
    smn = ctx.layouts.layout_for("SMN")
    smn["positions"]["PetTP"] = [5, 5]
    ctx.layouts.store.put("Alice", "SMN", smn)
    ctx.settings.set("layout_switch_with_job", False)
    game(ctx, "BLU")
    game(ctx, "SMN")
    assert pettp(win) == [1596, 1009.5]


def test_in_game_layout_round_trip(ctx, win, qtbot):
    game(ctx, "SMN")
    ctx.bridge.sent.clear()
    ctx.layouts._on_layout_message({"type": "LAYOUT_REQUEST"})
    items = [m for m in ctx.bridge.sent if m.startswith("LAYOUT_ITEM|")]
    assert ctx.bridge.sent[0] == "LAYOUT_BEGIN" and ctx.bridge.sent[-1] == "LAYOUT_SHOW"
    assert "LAYOUT_ITEM|distance|1672|21|70|24|distance" in items
    ctx.bridge.sent.clear()
    # The game sends top-left screen spots; right-aligned distance keeps its right-edge style.
    ctx.layouts._on_layout_message({"type": "LAYOUT_RESULT",
                                    "positions": {"distance": [1700, 30], "PetTP": [10, 10], "bogus": [1, 1]}})
    assert ctx.layouts.store.get("Alice", "SMN")["positions"]["distance"] == [-150, 30]
    qtbot.waitUntil(lambda: pettp(win) == [10, 10], timeout=2000)
    assert overlays.read_all(overlays.find_overlays(win, "Alice"), "Alice")["distance"] == [-150, 30]


def test_bridge_only_passes_layout_messages_from_the_verified_session(ctx):
    seen = []
    bridge = ctx.bridge
    bridge.layout_message.connect(seen.append)
    bridge._handle_payload({"type": "LAYOUT_RESULT", "session_id": "s", "update_seq": 1, "positions": {}})
    assert seen == []
    bridge._session_id, bridge._session_challenge = "s", "c"
    bridge._highest_update_seq = bridge._published_update_seq = 0
    bridge._handle_payload({"type": "LAYOUT_RESULT", "session_id": "s", "challenge": "wrong", "update_seq": 2})
    bridge._handle_payload({"type": "LAYOUT_RESULT", "session_id": "s", "challenge": "c", "update_seq": 3,
                            "positions": {}})
    assert [p["update_seq"] for p in seen] == [3]


def test_page_drag_and_save(ctx, win, qtbot):
    from vanadiel_nexus.ui.pages.layout import LayoutPage
    ctx.settings.set("layout_last_job", "SMN")
    page = LayoutPage(ctx)
    qtbot.addWidget(page)
    page.show()
    page.on_shown()
    assert page.job == "SMN"
    assert {"PetTP", "xivbar", "XIVPetBar", "MyHud.box"} <= set(page.scene.boxes)
    pet_bar_x = page.scene.boxes["XIVPetBar"].pos().x()
    page.scene.boxes["xivbar"].moveBy(100, 0)
    assert page.scene.boxes["XIVPetBar"].pos().x() == pet_bar_x + 100
    page.scene.boxes["PetTP"].setPos(400, 300)
    assert page.dirty
    page.save()
    assert pettp(win) == [400, 300]
    assert ctx.layouts.store.get("Alice", "SMN")["positions"]["xivbar"] == [100, -200]


def test_moving_the_smn_hud_reloads_gearswap_by_its_own_command(ctx, win, qtbot):
    """GearSwap is never shown/hidden by layouts, so it has no 'shown' entry; a moved HUD still needs 'gs reload'."""
    game(ctx, "SMN")
    layout = ctx.layouts.layout_for("SMN")
    assert "GearSwap" not in layout["shown"]
    layout["positions"]["GearSwap.smn_hud"] = [500, 300]
    ctx.bridge.sent.clear()
    ctx.layouts.save_layout("SMN", layout)
    assert "CMD|gs reload" in ctx.bridge.sent
    assert not any(m.startswith("ADDON|") and "GearSwap" in m for m in ctx.bridge.sent)  # never unload/load


def test_cancelling_the_background_picker_keeps_the_background_unless_removal_is_confirmed(ctx, qtbot, monkeypatch):
    from vanadiel_nexus.ui.pages import layout as layout_page
    page = layout_page.LayoutPage(ctx)
    qtbot.addWidget(page)
    ctx.settings.set("layout_background", "C:/shots/ffxi.png")
    monkeypatch.setattr(layout_page.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    monkeypatch.setattr(page, "confirm", lambda *a, **k: False)
    page.pick_background()
    assert ctx.settings.get("layout_background") == "C:/shots/ffxi.png"
    monkeypatch.setattr(page, "confirm", lambda *a, **k: True)
    page.pick_background()
    assert ctx.settings.get("layout_background") == ""
