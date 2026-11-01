"""In-game layout mode in the real addon (sandboxed Lua): frames from the app, drag, save back."""
import json

from tests.test_inventory_lua import addon, decode_sent  # noqa: F401  (pytest fixture)

LIBS = '''
    windower.get_windower_settings = function() return {ui_x_res=1920, ui_y_res=1080} end
    created = {}
    local function obj(kind, settings)
        local o = {kind=kind, x=settings.pos.x, y=settings.pos.y, visible=false,
                   w=(settings.size or {}).width or 80, h=(settings.size or {}).height or 20, alive=true}
        function o:pos(x, y) if x == nil then return self.x, self.y end self.x, self.y = x, y end
        function o:show() self.visible = true end
        function o:destroy() self.alive = false end
        function o:color(r, g, b) self.rgb = {r, g, b} end
        function o:alpha(a) self.a = a end
        function o:hover(x, y) return x >= self.x and x <= self.x + self.w and y >= self.y and y <= self.y + self.h end
        created[#created + 1] = o
        return o
    end
    package.preload.images = function() return {new=function(s) return obj('image', s) end} end
    package.preload.texts = function() return {new=function(text, s) local o = obj('text', s); o.text = text; return o end} end
'''


def run_prerender(lua, *messages):
    for m in messages or (None,):
        lua.globals().queued = m
        lua.execute('os.clock=function() return os_tick end; os_tick=(os_tick or 100)+1; events["prerender"]()')


def test_state_reports_ui_resolution(addon):
    addon.execute(LIBS + "events['load']()")
    _, state = decode_sent(addon)
    assert (state["ui_x_res"], state["ui_y_res"]) == (1920, 1080)


def test_layout_frames_drag_and_save(addon):
    addon.execute(LIBS)
    addon.execute('sent={}; events["addon command"]("layout")')
    request = json.loads(addon.globals().sent[1])
    assert request["type"] == "LAYOUT_REQUEST" and "session_id" in request
    run_prerender(addon, "LAYOUT_BEGIN", "LAYOUT_ITEM|parse.melee|100|200|330|150|Parse: melee",
                  "LAYOUT_ITEM|xivbar|724|820|472|60|xivbar", "LAYOUT_SHOW")
    images = [o for o in addon.globals().created.values() if o.kind == "image"]
    assert len(images) == 2 and all(i.visible for i in images)
    images[0].x, images[0].y = 300.4, 250.6  # dragged
    run_prerender(addon)  # labels follow their frames
    label = [o for o in addon.globals().created.values() if o.kind == "text" and o.text == "Parse: melee"][0]
    assert (label.x, label.y) == (304.4, 252.6)
    addon.execute('sent={}; events["addon command"]("layout", "save")')
    result = json.loads(addon.globals().sent[1])
    assert result["type"] == "LAYOUT_RESULT"
    assert result["positions"] == {"parse.melee": [300, 251], "xivbar": [724, 820]}
    assert result["update_seq"] > request["update_seq"]
    assert not any(o.alive for o in addon.globals().created.values())


def test_clicking_cancel_closes_without_sending(addon):
    addon.execute(LIBS)
    run_prerender(addon, "LAYOUT_BEGIN", "LAYOUT_ITEM|a|1|2|3|4|A", "LAYOUT_SHOW")
    cancel = [o for o in addon.globals().created.values() if o.kind == "text" and o.text == "Cancel"][0]
    addon.execute('sent={}')
    blocked = addon.eval(f'events["mouse"](1, {cancel.x + 2}, {cancel.y + 2}, 0, false)')
    assert blocked is True
    addon.eval(f'events["mouse"](2, {cancel.x + 2}, {cancel.y + 2}, 0, false)')
    assert len(addon.globals().sent) == 0
    assert not any(o.alive for o in addon.globals().created.values())



def press(lua, dik, pressed=True):
    return lua.eval(f'events["keyboard"]({dik}, {"true" if pressed else "false"}, 0, false)')


def test_keyboard_moves_the_selected_frame_and_saves(addon):
    addon.execute(LIBS)
    run_prerender(addon, "LAYOUT_BEGIN", "LAYOUT_ITEM|a|100|200|300|100|A",
                  "LAYOUT_ITEM|b|500|600|100|50|B", "LAYOUT_SHOW")
    frames = [o for o in addon.globals().created.values() if o.kind == "image"]
    assert frames[0].a == 150 and frames[1].a == 90          # first frame selected
    assert press(addon, 0xCD) is True and press(addon, 0xCD, False) is True   # Right: kept from the game
    assert (frames[0].x, frames[0].y) == (101, 200)
    press(addon, 0x2A)                                        # Shift held
    assert press(addon, 0xC8) is True                         # Up 10
    press(addon, 0x2A, False)
    assert (frames[0].x, frames[0].y) == (101, 190)
    assert press(addon, 0x0F) is True                         # Tab: next frame
    assert frames[1].a == 150 and frames[0].a == 90
    press(addon, 0xD0)                                        # Down 1 on frame b
    assert (frames[1].x, frames[1].y) == (500, 601)
    assert not press(addon, 0x1E)                             # other keys (A) reach the game
    addon.execute('sent={}')
    assert press(addon, 0x1C) is True                         # Enter saves
    result = json.loads(addon.globals().sent[1])
    assert result["positions"] == {"a": [101, 190], "b": [500, 601]}
    assert press(addon, 0x1C, False) is True                  # its release is swallowed too
    assert not press(addon, 0xCD)                             # layout closed: arrows reach the game


def test_escape_cancels_and_clicking_a_frame_selects_it(addon):
    addon.execute(LIBS)
    run_prerender(addon, "LAYOUT_BEGIN", "LAYOUT_ITEM|a|100|200|300|100|A",
                  "LAYOUT_ITEM|b|500|600|100|50|B", "LAYOUT_SHOW")
    frames = [o for o in addon.globals().created.values() if o.kind == "image"]
    addon.eval('events["mouse"](1, 520, 620, 0, false)')
    assert frames[1].a == 150 and frames[0].a == 90
    addon.execute('sent={}')
    assert press(addon, 0x01) is True
    assert len(addon.globals().sent) == 0
    assert not any(o.alive for o in addon.globals().created.values())
