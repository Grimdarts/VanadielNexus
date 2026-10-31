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
