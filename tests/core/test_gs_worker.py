"""The GearSwap sandbox, run in-process (no child process): what it reads, what it refuses, what it returns.

Fixtures are synthetic: tests/fixtures/gearswap holds a mini res/ and few-line stand-ins for Windower's libs.
"""
import hashlib
import os
import shutil
from pathlib import Path

import pytest

if os.environ.get('VN_LUA_RUNTIME'):
    import sys
    sys.path.insert(0, os.environ['VN_LUA_RUNTIME'])

pytest.importorskip('lupa.luajit21', reason='GearSwap sandbox requires lupa (VN_LUA_RUNTIME supported)')

from vanadiel_nexus.core import gearswap_reader, gs_worker  # noqa: E402

FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'gearswap'


@pytest.fixture(autouse=True)
def quiet_faulthandler():
    """LuaJIT raises Lua errors as Windows SEH exceptions; pytest's faulthandler would print each one."""
    import faulthandler
    enabled = faulthandler.is_enabled()
    faulthandler.disable()
    yield
    if enabled:
        faulthandler.enable()


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / 'Windower'
    shutil.copytree(FIXTURE, root)
    return root


def run(tree, body, name='Alice_BLU.lua', job='BLU', unchanged=False, **extra):
    """Write the job file and read it. unchanged=True also checks nothing on disk changed during the read."""
    path = tree / 'addons' / 'GearSwap' / 'data' / name
    path.write_text(body, encoding='utf-8')
    before = fs_hash(tree.parent) if unchanged else None
    args = {'windower_dir': str(tree), 'character': 'Alice', 'job': job, 'job_long': 'Blue Mage', 'job_id': 16,
            'job_path': str(path), 'appdata': str(tree.parent / 'appdata')}
    args.update(extra)
    raw = gs_worker.run(args)
    if unchanged:
        assert fs_hash(tree.parent) == before, 'the read changed files on disk'
    return raw


def sets_of(raw, texts=()):
    return {s.path: s for s in gearswap_reader.build_sets(raw, gearswap_reader.alias_lines(texts))}


def fs_hash(root):
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob('*')):
        digest.update(str(path).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def write(tree, rel, text):
    path = tree / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


# ---------------------------------------------------------------- reading sets

def test_plain_table_set(tree):
    raw = run(tree, 'function get_sets() sets.Idle = {head="Hashishin Kavuk +2", Body="Nyame Mail"} end')
    assert not raw.get('error')
    idle = sets_of(raw)['sets.Idle']
    assert idle.pieces['head'].name == 'Hashishin Kavuk +2'
    assert idle.pieces['body'].original_key == 'Body'  # slot keys are case-insensitive
    assert set(idle.pieces) == {'head', 'body'}


def test_slot_aliases_become_canonical_slots(tree):
    raw = run(tree, 'sets.A = {left_ear="Moonshade Earring", rear="Ishvara Earring", lring="Sroda Ring", '
                    'right_ring="Chirich Ring +1", ranged="Thibron"}')
    pieces = sets_of(raw)['sets.A'].pieces
    assert {s: p.original_key for s, p in pieces.items()} == {
        'ear1': 'left_ear', 'ear2': 'rear', 'ring1': 'lring', 'ring2': 'right_ring', 'range': 'ranged'}


def test_registry_item_tables_augments_bag_priority_and_augment(tree):
    raw = run(tree, '''
gear = {helm = {name="Herculean Helm", augments={'Accuracy+20', '"Fast Cast"+5', 'none'}, priority=10, bag="Wardrobe 2"}}
function get_sets()
    sets.A = {head=gear.helm, back={name="Rosmerta's Cape", augment='DEX+20'}}
    sets.B = {head=gear.helm}
end''')
    found = sets_of(raw)
    helm = found['sets.A'].pieces['head']
    assert (helm.name, helm.augments, helm.priority, helm.bag) == (
        'Herculean Helm', ['Accuracy+20', '"Fast Cast"+5'], 10, 'Wardrobe 2')  # 'none' dropped like GearSwap
    assert found['sets.A'].pieces['back'].augments == ['DEX+20']  # augment= becomes a one-item list
    assert helm.table_id and found['sets.B'].pieces['head'].table_id == helm.table_id
    assert helm.shared_count == 2
    assert found['sets.A'].pieces['back'].shared_count == 1


def test_empty_identity_and_empty_set_and_naked(tree):
    raw = run(tree, 'function get_sets() sets.A = {head=empty, body={}} sets.Blank = {} end')
    found = sets_of(raw)
    assert found['sets.A'].pieces['head'].empty
    assert 'body' not in found['sets.A'].pieces  # a table without a name does nothing in GearSwap
    assert found['sets.Blank'].empty_in_file and not found['sets.Blank'].pieces
    assert all(p.empty for p in found['sets.naked'].pieces.values())


def test_string_list_index_and_functions_are_not_sets(tree):
    raw = run(tree, '''function get_sets()
    sets.SavageBlade = {}
    sets.SavageBlade.Attack = {head="Hashishin Kavuk +2"}
    sets.SavageBlade.index = {'Attack', 'Accuracy'}
    sets.fn = function() end
end''')
    found = sets_of(raw)
    assert 'sets.SavageBlade.Attack' in found
    assert not any('index' in p or p.endswith('.fn') for p in found)
    assert 'sets.SavageBlade' not in found  # a container, not a set


def test_sets_with_slots_and_subsets_are_both_walked(tree):
    raw = run(tree, 'sets.engaged = {head="Nyame Mail"} sets.engaged.Acc = {body="Nyame Mail"}')
    assert {'sets.engaged', 'sets.engaged.Acc'} <= set(sets_of(raw))


def test_two_level_set_combine_provenance_string_and_registry(tree):
    raw = run(tree, '''
gear = {helm_wsd = {name="Herculean Helm", augments={'Weapon skill damage +4%'}}}
function get_sets()
    sets.WS = {neck="Fotia Gorget", head=gear.helm_wsd}
    sets.WS.Savage = set_combine(sets.WS, {waist="Fotia Belt"})
    sets.WS.Savage.Acc = set_combine(sets.WS.Savage, {body="Nyame Mail"})
end''')
    found = sets_of(raw)
    acc = found['sets.WS.Savage.Acc']
    for slot in ('neck', 'head'):
        assert acc.pieces[slot].inherited_from == 'sets.WS.Savage'
        assert acc.pieces[slot].origin_path == 'sets.WS'
    assert acc.pieces['waist'].origin_path == 'sets.WS.Savage'
    assert acc.pieces['body'].inherited_from == '' and acc.pieces['body'].origin_path == ''
    assert found['sets.WS'].pieces['neck'].origin_path == ''


def test_provenance_cleared_when_derived_slot_changes(tree):
    raw = run(tree, '''function get_sets()
    sets.A = {head="Hashishin Kavuk +2"}
    sets.B = set_combine(sets.A, {})
    sets.B.head = "Hashishin Kavuk +3"
end''')
    head = sets_of(raw)['sets.B'].pieces['head']
    assert head.name == 'Hashishin Kavuk +3' and head.inherited_from == '' and head.origin_path == ''


def test_provenance_cleared_when_source_slot_changes(tree):
    raw = run(tree, '''function get_sets()
    sets.A = {head="Hashishin Kavuk +2"}
    sets.B = set_combine(sets.A, {})
    sets.A.head = "Hashishin Kavuk +3"
end''')
    found = sets_of(raw)
    assert found['sets.B'].pieces['head'].name == 'Hashishin Kavuk +2'
    assert found['sets.B'].pieces['head'].inherited_from == ''  # sets.A no longer holds this value (D21)


def test_alias_paths_list_one_canonical_set(tree):
    raw = run(tree, '''function get_sets()
    sets.midcast = {Pet = {}}
    sets.midcast.Pet.MagicalBloodPactRage = {head="Hashishin Kavuk +2"}
    sets.magicalpact = sets.midcast.Pet.MagicalBloodPactRage
end''')
    found = sets_of(raw)
    assert 'sets.magicalpact' not in found
    assert found['sets.midcast.Pet.MagicalBloodPactRage'].aliases == ['sets.magicalpact']


def test_bare_alias_lines_are_never_canonical(tree):
    body = '''function get_sets()
    sets.midcast = {Pet = {}}
    sets.midcast.Pet.MagicalBloodPactRage = {head="Hashishin Kavuk +2"}
    sets.midcast.Pet.IfritMagicalBloodPactRage = sets.midcast.Pet.MagicalBloodPactRage
    sets.magicalpact = sets.midcast.Pet.MagicalBloodPactRage
end'''
    raw = run(tree, body)
    found = sets_of(raw, [body])
    canonical = found['sets.midcast.Pet.MagicalBloodPactRage']
    assert sorted(canonical.aliases) == ['sets.magicalpact', 'sets.midcast.Pet.IfritMagicalBloodPactRage']
    assert 'sets.midcast.Pet.IfritMagicalBloodPactRage' not in found
    # Without the source text the tie goes to walk order (Ifrit sorts first): the alias rule is what fixes it.
    assert 'sets.midcast.Pet.IfritMagicalBloodPactRage' in sets_of(raw)


def test_path_rendering_forms_and_odd_paths(tree):
    raw = run(tree, r'''function get_sets()
    sets.precast = {WS = {}}
    sets.precast.WS['Savage Blade'] = {head="Hashishin Kavuk +2"}
    sets.precast.WS["Rudra's Storm"] = {head="Hashishin Kavuk +2"}
    sets[1] = {head="Hashishin Kavuk +2"}
    sets['back\\slash'] = {head="Hashishin Kavuk +2"}
    sets['both\'"'] = {head="Hashishin Kavuk +2"}
    sets['both\'"'].child = {head="Hashishin Kavuk +2"}
    sets['line\nbreak'] = {head="Hashishin Kavuk +2"}
    sets['end'] = {head="Hashishin Kavuk +2"}
end''')
    found = sets_of(raw)
    assert "sets.precast.WS['Savage Blade']" in found
    assert 'sets.precast.WS["Rudra\'s Storm"]' in found and not found['sets.precast.WS["Rudra\'s Storm"]'].odd_path
    assert 'sets[1]' in found and "sets['end']" in found
    assert found["sets['back\\\\slash']"].odd_path
    assert found["sets['line\\nbreak']"].odd_path
    both = [s for p, s in found.items() if p.startswith("sets['both")]
    assert len(both) == 2 and all(s.odd_path for s in both)  # and everything below it


def test_walk_order_numbers_then_strings_case_insensitive(tree):
    raw = run(tree, 'sets.b = {head="x"} sets.A = {head="x"} sets[2] = {head="x"} sets[1] = {head="x"} sets.C = {head="x"}')
    assert [s.path for s in gearswap_reader.build_sets(raw)] == [
        'sets[1]', 'sets[2]', 'sets.A', 'sets.b', 'sets.C', 'sets.naked']


def test_cycles_are_walked_once(tree):
    raw = run(tree, 'sets.A = {head="x"} sets.A.loop = sets.A')
    found = sets_of(raw)
    assert found['sets.A'].aliases == []  # the self-reference is not a second path
    assert list(found) == ['sets.A', 'sets.naked']


# ---------------------------------------------------------------- include and the GearSwap API

def test_mote_style_get_sets_through_include(tree):
    write(tree, 'addons/GearSwap/libs/mote-include.lua', '''
function get_sets()
    sets.precast = {}
    sets.idle = {}
    init_gear_sets()
end''')
    raw = run(tree, '''
function get_sets()
    include('Mote-Include.lua')  -- lowercased by include, like GearSwap
    get_sets()
end
function init_gear_sets() sets.idle.Town = {body="Nyame Mail"} end''')
    assert not raw.get('error'), raw.get('error_details')
    assert 'sets.idle.Town' in sets_of(raw)
    assert any(p.endswith('mote-include.lua') for p in raw['includes'])


def test_include_into_a_table_and_pack_skip(tree):
    write(tree, 'addons/GearSwap/data/Alice-gear.lua', 'helm = {name="Herculean Helm"}\nerror("swallowed")')
    raw = run(tree, '''
local g = include('alice-gear.lua', {})
local p = include('pack')
function get_sets() sets.A = {head=g.helm, body=(p == nil) and "Nyame Mail" or nil} end''')
    assert not raw.get('error'), raw.get('error_details')
    pieces = sets_of(raw)['sets.A'].pieces
    assert pieces['head'].name == 'Herculean Helm'  # include(name, dest) runs in pcall and returns dest
    assert pieces['body'].name == 'Nyame Mail'


def test_missing_include_is_an_error(tree):
    raw = run(tree, "include('Nope.lua')")
    assert 'Cannot find the include file (nope.lua)' in raw['error']
    assert raw['nodes'] == []


def test_windower_ffxi_coroutine_and_real_res_work(tree):
    raw = run(tree, '''
local recasts = windower.ffxi.get_ability_recasts()
local info = windower.ffxi.get_info()
coroutine.schedule(function() error('never runs') end, 1)
local res = require('resources')
local moon = res.moon_phases[4].en
windower.register_event('load', function() end)
send_command('wait 1; input /echo')
function get_sets()
    sets.A = {head=moon == "Full Moon" and "Hashishin Kavuk +2" or "x", body=info.logged_in and "Nyame Mail" or "x"}
    sets.B = {head=(next(recasts) == nil) and "Hashishin Kavuk +3" or "x"}
end''')
    assert not raw.get('error'), raw.get('error_details')
    found = sets_of(raw)
    assert found['sets.A'].pieces['head'].name == 'Hashishin Kavuk +2'
    assert found['sets.A'].pieces['body'].name == 'Nyame Mail'
    assert found['sets.B'].pieces['head'].name == 'Hashishin Kavuk +3'


def test_windower_libs_load_after_their_load_time_debug_calls(tree):
    raw = run(tree, '''
local t = T{1, 2}
local s = S{'a'}
function get_sets()
    sets.A = {head=(t:contains(2) and s:contains('a') and ("abc"):startswith("a") and L{} and Q{}) and "Hashishin Kavuk +2" or "x"}
end''')
    assert not raw.get('error'), raw.get('error_details')
    assert sets_of(raw)['sets.A'].pieces['head'].name == 'Hashishin Kavuk +2'
    assert not raw['load_errors'] or all(e.startswith('luau') or e.startswith('resources') for e in raw['load_errors'])


def test_env_has_every_gearswap_user_env_key(tree):
    keys = "', '".join(gs_worker.GEARSWAP_USER_ENV_KEYS)
    raw = run(tree, f'''
local missing = {{}}
for _, key in ipairs({{'{keys}'}}) do
    if rawget(_G, key) == nil then missing[#missing + 1] = key end
end
function get_sets() sets.A = {{head = (#missing == 0 and _G._G == _G) and "ok" or table.concat(missing, ',')}} end''')
    assert sets_of(raw)['sets.A'].pieces['head'].name == 'ok'
    assert len(gs_worker.GEARSWAP_USER_ENV_KEYS) == len(set(gs_worker.GEARSWAP_USER_ENV_KEYS))
    assert 'include_path' in gs_worker.GEARSWAP_USER_ENV_KEYS
    assert 'user_include_path' not in gs_worker.GEARSWAP_USER_ENV_KEYS


# ---------------------------------------------------------------- errors

def test_syntax_error_is_an_error_with_no_sets(tree):
    raw = run(tree, 'function get_sets(\n')
    assert raw['error'].startswith('Alice_BLU.lua:')
    assert not raw['partial'] and raw['nodes'] == []


def test_body_error_is_an_error_with_no_sets(tree):
    raw = run(tree, 'sets.A = {head="x"}\nlocal x = nil + 1')
    assert 'Alice_BLU.lua:2' in raw['error'] and 'arithmetic' in raw['error']
    assert not raw['partial'] and raw['nodes'] == [] and 'traceback' in raw['error_details']


def test_get_sets_error_keeps_the_sets_made_before_it(tree):
    raw = run(tree, '''function get_sets()
    sets.A = {head="x"} sets.B = {head="x"} sets.C = {head="x"}
    error("boom")
end''')
    assert raw['partial'] and 'boom' in raw['error']
    assert {'sets.A', 'sets.B', 'sets.C'} <= set(sets_of(raw))


# ---------------------------------------------------------------- fail-soft writes and denied functions

def test_nova_install_style_writes_fail_soft_and_change_nothing(tree):
    raw = run(tree, unchanged=True, body='''
Nova = {}
function Nova.export_controls()
    local f = io.open(windower.addon_path .. 'data/Nova-controls-live.json', 'w')
    if f then f:write('{}') f:close() end
    local ok = pcall(dofile, windower.addon_path .. 'data/user-globals.lua')
    local fh = file.new('data/export.txt')
    fh:write('x')
end
function Nova.install()
    local wrapped = get_sets
    get_sets = function() wrapped() Nova.export_controls() end
end
function get_sets() sets.Idle = {head="Hashishin Kavuk +2"} end
Nova.install()''')
    assert 'sets.Idle' in sets_of(raw)
    # files.write hits io.open(...,'w') → nil and then fails, inside get_sets: a partial read, not a crash.
    assert raw['partial'] and 'attempt to index' in raw['error']


def test_io_open_write_returns_nil_and_creates_nothing(tree):
    raw = run(tree, unchanged=True, body='''
local f, err = io.open('x.txt', 'w')
local a = io.open(windower.addon_path .. 'data/y.txt', 'a+')
function get_sets() sets.A = {head=(f == nil and a == nil and err:find('writing') ~= nil) and "ok" or "x"} end''')
    assert sets_of(raw)['sets.A'].pieces['head'].name == 'ok'


def test_io_open_read_inside_gearswap_data_works(tree):
    write(tree, 'addons/GearSwap/data/notes.txt', 'Hashishin Kavuk +2\nsecond')
    raw = run(tree, '''
local f = io.open(windower.addon_path .. 'data/notes.txt', 'r')
local first = f:read('*l')
local rest = f:read('*a')
f:close()
local count = 0
for line in io.lines(windower.addon_path .. 'data/notes.txt') do count = count + 1 end
function get_sets() sets.A = {head=first, body=(rest == "second" and count == 2) and "ok" or "x"} end''')
    assert not raw.get('error'), raw.get('error_details')
    pieces = sets_of(raw)['sets.A'].pieces
    assert pieces['head'].name == 'Hashishin Kavuk +2' and pieces['body'].name == 'ok'


@pytest.mark.parametrize('code, name', [
    ("os.remove('x')", 'os.remove'),
    ('os.exit()', 'os.exit'),
    ("os.execute('dir')", 'os.execute'),
    ("require('ffi')", "require('ffi')"),
    ("require('jit')", "require('jit')"),
    ('debug.getinfo(1)', 'debug.getinfo'),
    ('string.dump(print)', 'string.dump'),
    ('("").dump(print)', 'string.dump'),
    ("loadstring('\\27LJ')", 'loadstring of bytecode'),
    ("io.popen('dir')", 'io.popen'),
    ("dofile('x.lua')", 'dofile'),
    ("include('package').loadlib('x', 'y')", 'package.loadlib'),
    ("include('package').loaded.os.remove('x')", 'os.remove'),
    ("include('os').execute('x')", 'os.execute'),
])
def test_denied_functions_raise_and_name_themselves(tree, code, name):
    raw = run(tree, code, unchanged=True)
    assert name + " is not available in Vana'diel Nexus" in raw['error']


def test_io_open_outside_the_roots_returns_nil(tree, tmp_path):
    outside = tmp_path / 'secret.txt'
    outside.write_text('secret', encoding='utf-8')
    path = str(outside).replace('\\', '/')
    raw = run(tree, f'''
local f, err = io.open('{path}', 'r')
local w = io.open('C:/Windows/win.ini')
function get_sets() sets.A = {{head=(f == nil and w == nil and err:find('not available') ~= nil) and "ok" or "x"}} end''')
    assert sets_of(raw)['sets.A'].pieces['head'].name == 'ok'


def test_escape_routes_are_closed(tree):
    raw = run(tree, '''
local function check(ok) return ok and "ok" or "x" end
local pkg = include('package')
local io2 = include('io')
local rio = require('io')
local w = io2.open('x.txt', 'w')
local loader_count = #pkg.loaders
function get_sets()
    sets.A = {
        head = check(getfenv == nil and setfenv == nil and rawget(_G, 'python') == nil and jit == nil),
        body = check(w == nil and rio == io2 and rio.open == io.open),
        hands = check(loader_count == 1 and pkg.cpath == '' and pkg.loaded.ffi == nil and pkg.loaded.jit == nil),
        legs = check(pkg.loaded.python == nil and package == nil and load == nil),
        feet = check(not pcall(string.dump, print) and not pcall(debug.sethook)),
    }
end''')
    assert not raw.get('error'), raw.get('error_details')
    assert {s: p.name for s, p in sets_of(raw)['sets.A'].pieces.items()} == {
        'head': 'ok', 'body': 'ok', 'hands': 'ok', 'legs': 'ok', 'feet': 'ok'}


def test_runaway_loops_stop(tree):
    for loop in ('while true do end', 'for i = 1, 1e12 do end',
                 'local f = function() for i = 1, 1e12 do end end f()',
                 'coroutine.wrap(function() while true do end end)()'):
        raw = run(tree, loop, instruction_limit=5_000_000)
        assert raw['error'] == 'took too long to load', loop
        assert raw['timed_out']


def test_warm_loop_compiled_before_the_guard_still_stops(tree):
    # A hot loop that LuaJIT would compile: the guard runs jit.off(); jit.flush() first (probe: 14.5 s without).
    raw = run(tree, '''
local function hot(n) local s = 0 for i = 1, n do s = s + i end return s end
for i = 1, 200 do hot(1000) end
hot(1e12)''', instruction_limit=20_000_000)
    assert raw['error'] == 'took too long to load'


def test_set_combine_skips_nil_arguments_like_gearswap(tree):
    # GearSwap checks and merges with pairs, so a missing set (a typo, an index lookup) is skipped silently.
    raw = run(tree, '''function get_sets()
    sets.A = {head="Hashishin Kavuk +2"}
    sets.B = set_combine(sets.Missing, sets.A, nil, {body="Nyame Mail"})
end''')
    assert not raw.get('error'), raw.get('error_details')
    assert set(sets_of(raw)['sets.B'].pieces) == {'head', 'body'}
    assert 'non-gear sets' in run(tree, 'sets.B = set_combine("x")')['error']


def test_windower_syntax_extensions_are_rewritten():
    src = '''local a = '%s':format(1)
local b = "x":upper()
local c = function() return 1 end()
local d = 1:max(2) and true:fn()
local e = f"x" .. "y" .. g{1}
-- 'comment':format() stays
local s = "it's ':' here"'''
    out = gs_worker.windower_syntax(src)
    assert "('%s'):format(1)" in out and '("x"):upper()' in out
    assert '(function() return 1 end)()' in out and '(1):max(2)' in out and '(true):fn()' in out
    assert 'f"x" .. "y" .. g{1}' in out  # concatenation and call arguments untouched
    assert "-- 'comment':format() stays" in out and '''"it's ':' here"''' in out
