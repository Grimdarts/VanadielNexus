--[[ Vana'diel Nexus: run one GearSwap job file the way GearSwap does, with nothing able to touch the disk
or the game, then describe every table under `sets`.

Runs inside a child process (core/gs_worker.py), compiled as a chunk and called with
(cfg, py_read_source, py_resolve, py_exists). Boot order (docs/SET-MANAGER-ENG-REVIEW.md section 4.2):
  1. runaway guard first: jit.off(); jit.flush(); count hook
  2. capture the real functions the sandbox itself needs
  3. Lua-only loader and package.loaded stubs for game-touching libs
  4. the real Windower libs (they call debug.setmetatable at load, so before the scrub)
  5. scrub the real globals in place (io, os, string, debug, package, loaders)
  6. user_env from cfg.user_env_keys (refresh.lua:114-147)
  7. the job file body, 8. get_sets, 9. walk `sets` into nodes and edges
]]
local cfg, py_read_source, py_resolve, py_exists = ...

-- 1. Runaway guard. JIT-compiled code never fires the count hook, and jit.off() alone keeps already-compiled
-- traces, so flush them too (probe: 14.5 s past the limit without flush).
jit.off()
jit.flush()
local sethook = debug.sethook
local LIMIT = cfg.instruction_limit or 200000000
local STEP = 1000
local steps = 0
local timed_out = false
local function guard()
    steps = steps + STEP
    if steps >= LIMIT then
        timed_out = true
        error('took too long to load', 0)
    end
end
sethook(guard, '', STEP)

-- 2. Real functions the sandbox keeps for itself.
local traceback = debug.traceback
local real_loadstring, setfenv, getfenv = loadstring, setfenv, getfenv
local setmetatable, getmetatable, rawget, rawset, rawequal = setmetatable, getmetatable, rawget, rawset, rawequal
local next, pairs, ipairs, type, tostring, tonumber, select = next, pairs, ipairs, type, tostring, tonumber, select
local error, pcall, xpcall, unpack, assert = error, pcall, xpcall, unpack, assert
local lower, sub, byte, find, gsub, match = string.lower, string.sub, string.byte, string.find, string.gsub, string.match
local sort, concat = table.sort, table.concat
local co_create, co_resume = coroutine.create, coroutine.resume
local real_collectgarbage = collectgarbage
local G = _G

local NOT_AVAILABLE = " is not available in Vana'diel Nexus"
local function denied(name)
    return function() error(name .. NOT_AVAILABLE, 2) end
end
local function noop() end

local windower_dir = cfg.windower_dir          -- ends with '/'
local gearswap_dir = windower_dir .. 'addons/GearSwap/'
local libs_dir = windower_dir .. 'addons/libs/'

local function compile(src, chunkname)
    if type(src) ~= 'string' then
        return nil, 'source is not a string'
    end
    if byte(src, 1) == 27 then
        error('loadstring of bytecode' .. NOT_AVAILABLE, 3)
    end
    return real_loadstring(src, chunkname)
end

local function basename(path)
    return match(path, '([^/\\]+)$') or path
end

-- 3. Lua-only loader (no C modules, no cpath) and stubs for libs that would touch the game or the disk.
local function lua_loader(name)
    local rel = gsub(name, '%.', '/') .. '.lua'
    for _, base in ipairs({gearswap_dir, libs_dir}) do
        local src = py_read_source(base .. rel)
        if src then
            local f, err = compile(src, '@' .. rel)
            if not f then
                error(err, 0)
            end
            return f
        end
    end
    return "\n\tno file '" .. rel .. "' (Vana'diel Nexus loads Lua libraries only)"
end
package.loaders = {function(name)
    local loaded = package.preload[name]
    if loaded then
        return loaded
    end
    return lua_loader(name)
end}
package.cpath = ''
package.path = ''

-- A table whose every unknown method is a no-op returning nil: texts, images, prims and friends.
local function null_object()
    local object = {}
    return setmetatable(object, {__index = function() return noop end, __call = function() return null_object() end})
end
local function null_lib(fields)
    local lib = fields or {}
    return setmetatable(lib, {__index = function(_, key)
        if key == 'new' or key == 'create' then
            return function() return null_object() end
        end
        return noop
    end})
end

local player = {
    name = cfg.character, main_job = cfg.job, main_job_full = cfg.job_long, main_job_id = cfg.job_id,
    sub_job = cfg.sub_job, sub_job_full = cfg.sub_job_long, sub_job_id = cfg.sub_job_id,
    main_job_level = 99, sub_job_level = 49, jobs = {}, equipment = {}, status = 'Idle', status_id = 0,
    buffs = {}, hp = 1000, hpp = 100, mp = 1000, mpp = 100, tp = 0, max_hp = 1000, max_mp = 1000,
    race_id = 1, superior_level = 0, skills = {}, merits = {}, job_points = {}, target_locked = false,
    in_combat = false, vitals = {hp = 1000, hpp = 100, mp = 1000, mpp = 100, tp = 0}, id = 1, index = 1,
}
if cfg.job then player.jobs[cfg.job] = 99 end
if cfg.sub_job then player.jobs[cfg.sub_job] = 49 end

local function safe_info()
    return {logged_in = true, moon_phase = 0, moon = 0, time = 0, day = 0, weather = 0, zone = 0,
            language = 'english', mog_house = false}
end
local function bag_info()
    return {max = 80, count = 0, enabled = true}
end
local ffxi = setmetatable({
    get_player = function() return player end,
    get_info = safe_info,
    get_items = function(bag, index)
        if bag == nil then
            return setmetatable({max_inventory = 80, gil = 0, equipment = {}}, {__index = function() return bag_info() end})
        end
        if index ~= nil then
            return {id = 0, count = 0, status = 0}
        end
        return bag_info()
    end,
    get_bag_info = function(bag)
        if bag == nil then
            return setmetatable({}, {__index = function() return bag_info() end})
        end
        return bag_info()
    end,
}, {__index = function(_, key)
    if type(key) == 'string' and sub(key, 1, 4) == 'get_' then
        return function() return {} end
    end
    return noop
end})

local event_id = 0
local function register_event()
    event_id = event_id + 1
    return event_id
end
local function exists(kind)
    return function(path)
        return py_exists(tostring(path), kind) and true or false
    end
end
local windower = setmetatable({
    ffxi = ffxi, ffxi_path = windower_dir, addon_path = gearswap_dir, windower_path = windower_dir,
    register_event = register_event, raw_register_event = register_event, unregister_event = noop,
    send_command = noop, add_to_chat = noop, chat = null_lib(), text = null_lib(), prim = null_lib(),
    file_exists = exists('file'), dir_exists = exists('dir'), create_dir = noop,
    get_dir = function(path)
        if path == windower_dir .. 'res/' then
            local names = {}
            for i, name in ipairs(cfg.res_names or {}) do
                names[i] = name .. '.lua'
            end
            return names
        end
        return {}
    end,
    wc_match = function() return false end, convert_auto_trans = function(s) return s end,
    from_shift_jis = function(s) return s end, to_shift_jis = function(s) return s end,
    get_windower_settings = function() return {ui_x_res = 1920, ui_y_res = 1080, x_res = 1920, y_res = 1080} end,
    play_sound = noop, debug = noop, packets = null_lib(),
}, {__index = function() return noop end})
G.windower = windower

local extdata = {decode = function() return {} end, compare_augments = function() return false end}
package.loaded.extdata = extdata
package.loaded.texts = null_lib()
package.loaded.images = null_lib()
package.loaded.packets = null_lib({parse = function() return {} end})
package.loaded.socket = null_lib({gettime = function() return os.time() end})
package.loaded.mime = null_lib()
package.loaded.logger = null_lib()
package.loaded.config = null_lib({
    load = function(a, b)
        if type(b) == 'table' then return b end
        if type(a) == 'table' then return a end
        return {}
    end,
    save = noop, register = noop, reload = noop,
})
package.loaded.pack = true  -- GearSwap's require 'pack' returns nothing, so include('pack') skips it
G.log, G.notice, G.warning, G.flog = noop, noop, noop, noop

-- res/<name>.lua read through py_read_source, run with an empty env (the files are plain table constructors).
local function res_dofile(path)
    local src = py_read_source(tostring(path))
    if not src then
        error('Cannot read ' .. basename(tostring(path)), 2)
    end
    local f = assert(compile(src, '@res/' .. basename(tostring(path))))
    setfenv(f, {})
    return f()
end

-- 4. The real Windower libs: every player has them, so job files see the same T{}, S{}, L{} and helpers.
local load_errors = {}
local function load_lib(name)
    if not package.loaded[name] then
        local ok, err = pcall(require, name)
        if not ok then
            load_errors[#load_errors + 1] = name .. ': ' .. tostring(err)
        end
    end
end
local function load_resources()
    -- The real resources lib loads res files with dofile; give it a read-only one (its own env, nothing else).
    local src = py_read_source(libs_dir .. 'resources.lua')
    local res
    if src then
        local f = compile(src, '@resources.lua')
        if f then
            setfenv(f, setmetatable({dofile = res_dofile}, {__index = G, __newindex = G}))
            local ok, value = pcall(f)
            if ok and type(value) == 'table' then
                res = value
            else
                load_errors[#load_errors + 1] = 'resources: ' .. tostring(value)
            end
        end
    end
    if not res then
        -- Fallback: plain lazy tables.
        res = setmetatable({}, {__index = function(t, key)
            if type(key) ~= 'string' then return nil end
            local ok, value = pcall(res_dofile, windower_dir .. 'res/' .. key .. '.lua')
            value = ok and type(value) == 'table' and value or {}
            if G.T then value = G.T(value) end
            rawset(t, key, value)
            return value
        end})
    end
    package.loaded.resources = res
end
for _, name in ipairs({'functions', 'maths', 'tables', 'sets', 'lists', 'strings', 'queues'}) do
    load_lib(name)
end
load_resources()
for _, name in ipairs({'files', 'json', 'chat', 'luau'}) do
    load_lib(name)
end
local resources = package.loaded.resources

-- 5. Scrub the real globals IN PLACE, so every route (globals, package.loaded, include('io'), require, getfenv)
-- sees the safe versions.
local function to_path(path)
    path = tostring(path)
    if not match(path, '^%a:[/\\]') and not match(path, '^[/\\]') then
        path = windower_dir .. path
    end
    return path
end

local function text_file(text)
    local pos = 1
    local file = {}
    local function read_line(keep)
        if pos > #text then return nil end
        local stop = find(text, '\n', pos, true)
        local line
        if stop then
            line = sub(text, pos, keep and stop or stop - 1)
            pos = stop + 1
        else
            line = sub(text, pos)
            pos = #text + 1
        end
        if not keep then line = gsub(line, '\r$', '') end
        return line
    end
    local function read_one(fmt)
        fmt = fmt or '*l'
        if type(fmt) == 'number' then
            if pos > #text then return nil end
            local chunk = sub(text, pos, pos + fmt - 1)
            pos = pos + fmt
            return chunk
        end
        if fmt == '*a' or fmt == '*all' or fmt == 'a' then
            local rest = sub(text, pos)
            pos = #text + 1
            return rest
        elseif fmt == '*L' or fmt == 'L' then
            return read_line(true)
        elseif fmt == '*n' or fmt == 'n' then
            local number_text, stop = match(text, '^%s*([%-%+]?%d*%.?%d+[eE]?[%-%+]?%d*)()', pos)
            if not number_text then return nil end
            pos = stop
            return tonumber(number_text)
        end
        return read_line(false)
    end
    function file:read(...)
        if select('#', ...) == 0 then return read_one('*l') end
        local results = {}
        for i = 1, select('#', ...) do
            results[i] = read_one((select(i, ...)))
        end
        return unpack(results, 1, select('#', ...))
    end
    function file:lines()
        return function() return read_line(false) end
    end
    function file:close() return true end
    function file:seek(whence, offset)
        if whence == 'set' then pos = (offset or 0) + 1 elseif whence == 'end' then pos = #text + 1 + (offset or 0) end
        return pos - 1
    end
    function file:write() return nil, "writing" .. NOT_AVAILABLE end
    function file:flush() return true end
    function file:setvbuf() return true end
    return file
end

local function safe_open(path, mode)
    mode = tostring(mode or 'r')
    if find(mode, '[wa+]') then
        return nil, tostring(path) .. ': writing' .. NOT_AVAILABLE
    end
    local text = py_read_source(to_path(path))
    if not text then
        return nil, tostring(path) .. ': not available in Vana\'diel Nexus'
    end
    return text_file(text)
end

local real_io = io
for key in pairs(real_io) do
    real_io[key] = nil
end
real_io.open = safe_open
real_io.lines = function(path)
    if path == nil then
        error('io.lines()' .. NOT_AVAILABLE, 2)
    end
    local f, err = safe_open(path, 'r')
    if not f then error(err, 2) end
    return f:lines()
end
real_io.type = function(object) return type(object) == 'table' and object.lines and 'file' or nil end
for _, name in ipairs({'write', 'output', 'input', 'popen', 'read', 'tmpfile', 'close'}) do
    real_io[name] = denied('io.' .. name)
end

local real_os = os
real_os.getenv = function() return nil end
for _, name in ipairs({'exit', 'execute', 'remove', 'rename', 'tmpname', 'setlocale'}) do
    real_os[name] = denied('os.' .. name)
end

string.dump = denied('string.dump')

for key in pairs(debug) do
    debug[key] = denied('debug.' .. key)
end

coroutine.schedule = noop
coroutine.sleep = noop
coroutine.create = function(f)
    local co = co_create(f)
    sethook(co, guard, '', STEP)  -- hooks are per coroutine in Lua 5.1
    return co
end
local function wrap_results(ok, ...)
    if not ok then error((...), 0) end
    return ...
end
coroutine.wrap = function(f)
    local co = coroutine.create(f)
    return function(...) return wrap_results(co_resume(co, ...)) end
end

local job_env = nil  -- set once user_env exists
local function safe_loadstring(src, chunkname)
    local f, err = compile(src, chunkname)
    if not f then return nil, err end
    setfenv(f, job_env or G)
    return f
end
local function safe_load(chunk, chunkname)
    if type(chunk) ~= 'string' then
        error('load(function)' .. NOT_AVAILABLE, 2)
    end
    return safe_loadstring(chunk, chunkname)
end

G.python = nil
G.jit = nil
G.loadstring = safe_loadstring
G.load = safe_load
G.dofile = denied('dofile')
G.loadfile = denied('loadfile')
G.newproxy = denied('newproxy')
G.module = denied('module')
G.collectgarbage = function(option)
    if option == 'count' then return real_collectgarbage('count') end
    error('collectgarbage' .. NOT_AVAILABLE, 2)
end
package.loadlib = denied('package.loadlib')
package.seeall = nil
package.loaders = {lua_loader}
package.cpath = ''
for key in pairs(package.preload) do
    package.preload[key] = nil
end
for _, name in ipairs({'ffi', 'jit', 'debug', 'python', 'jit.opt', 'jit.util'}) do
    package.loaded[name] = nil
end

-- 6. The job file's environment: every key from refresh.lua:114-147.
local empty = {}
local include_path_value = nil
local includes = {}
local user_env = {}
job_env = user_env
local function keyfilter(key)
    return type(key) == 'string' and lower(key) or key
end

local SLOTS = {main = 'main', sub = 'sub', range = 'range', ranged = 'range', ammo = 'ammo', head = 'head',
    body = 'body', hands = 'hands', legs = 'legs', feet = 'feet', neck = 'neck', waist = 'waist', ear1 = 'ear1',
    ear2 = 'ear2', left_ear = 'ear1', right_ear = 'ear2', learring = 'ear1', rearring = 'ear2', lear = 'ear1',
    rear = 'ear2', left_ring = 'ring1', right_ring = 'ring2', lring = 'ring1', rring = 'ring2', ring1 = 'ring1',
    ring2 = 'ring2', back = 'back'}
local function slot_of(key)
    return type(key) == 'string' and SLOTS[lower(key)] or nil
end
local slot_map = setmetatable({main = 0, sub = 1, range = 2, ranged = 2, ammo = 3, head = 4, body = 5, hands = 6,
    legs = 7, feet = 8, neck = 9, waist = 10, ear1 = 11, ear2 = 12, left_ear = 11, right_ear = 12, learring = 11,
    rearring = 12, lear = 11, rear = 12, left_ring = 13, right_ring = 14, lring = 13, rring = 14, ring1 = 13,
    ring2 = 14, back = 15}, {__index = function(t, k) return rawget(t, keyfilter(k)) end})
local default_slot_map = {[0] = 'main', 'sub', 'range', 'ammo', 'head', 'body', 'hands', 'legs', 'feet', 'neck',
    'waist', 'left_ear', 'right_ear', 'left_ring', 'right_ring', 'back'}

-- set_combine: slot keys only, canonical names, left to right (helper_functions.lua:304-330). Records each
-- slot's source table and value, so provenance can be checked against both later (eng review D21).
local combine_origin = setmetatable({}, {__mode = 'k'})
local function set_combine(...)
    local count = select('#', ...)
    local args = {...}
    for i = 1, count do
        -- GearSwap checks and merges with pairs (table.all/table.map), so nil arguments are skipped silently.
        if args[i] ~= nil and type(args[i]) ~= 'table' then
            error('Trying to combine non-gear sets.', 2)
        end
    end
    local result, origin = {}, {}
    for i = 1, count do
        local source = args[i] or empty
        for key, value in next, source do
            local slot = slot_of(key)
            if slot then
                result[slot] = value
                origin[slot] = {source = source, value = value}
            end
        end
    end
    combine_origin[result] = origin
    return result
end

local function find_file(names)
    for _, name in ipairs(names) do
        local path = py_resolve(name, include_path_value)
        if path then
            return path, nil, name
        end
    end
    return false
end

-- include / require: GearSwap's include_user (user_functions.lua:300-333).
local function include_user(str, dest)
    if type(str) ~= 'string' then
        error('\nGearSwap: include() was passed an invalid value (' .. tostring(str) .. '). (must be a string)', 2)
    end
    str = lower(str)
    if str == 'ffi' or str == 'jit' or str == 'debug' then
        error("require('" .. str .. "')" .. NOT_AVAILABLE, 2)
    end
    if type(package.loaded[str]) == 'table' then
        return package.loaded[str]
    elseif str == 'pack' then
        return
    end
    if sub(str, -4) ~= '.lua' then str = str .. '.lua' end
    local path = find_file({str})
    if not path then
        error('\nGearSwap: Cannot find the include file (' .. tostring(str) .. ').', 2)
    end
    local src = py_read_source(path)
    local f, err = compile(src, '@' .. basename(path))
    includes[#includes + 1] = path
    if f and not err then
        if type(dest) == 'table' then
            setmetatable(dest, {__index = user_env._G})
            setfenv(f, dest)
            pcall(f, dest)
            return dest
        else
            setfenv(f, user_env)
            return f()
        end
    else
        error('\nGearSwap: Error loading file (' .. tostring(str) .. '): ' .. tostring(err), 2)
    end
end

local gearswap = setmetatable({
    res = resources, extdata = extdata, pathsearch = find_file, slot_map = slot_map,
    default_slot_map = default_slot_map, encumbrance_table = {}, gearswap_disabled = false, language = 'english',
    empty = empty, set_combine = set_combine, include_user = include_user,
}, {__index = function() return nil end})

local alliance = {{}, {}, {}}
local values = {
    gearswap = gearswap, _global = {}, _settings = {}, _addon = {name = 'GearSwap', version = cfg.gearswap_version},
    equip = noop, cancel_spell = noop, change_target = noop, cast_delay = noop, print_set = noop,
    set_combine = set_combine, disable = noop, enable = noop, send_command = noop, windower = windower,
    include = include_user, midaction = function() return false end, pet_midaction = function() return false end,
    set_language = noop, show_swaps = noop, debug_mode = noop,
    include_path = function(path) include_path_value = type(path) == 'string' and path or nil end,
    register_unhandled_command = noop, move_spell_target = noop, language = 'english',
    string = string, math = math, table = table, set = G.set or {}, list = G.list or {}, queue = G.queue or {},
    T = G.T, S = G.S, L = G.L, Q = G.Q, pack = {}, functions = G.functions or {},
    os = os, texts = package.loaded.texts, bit = G.bit, type = type, tostring = tostring, tonumber = tonumber,
    pairs = pairs, ipairs = ipairs, print = noop, add_to_chat = noop, unpack = unpack, next = next,
    select = select, lua_base_path = gearswap_dir, empty = empty, file = package.loaded.files or null_lib(),
    loadstring = safe_loadstring, assert = assert, error = error, pcall = pcall, io = io, dofile = G.dofile,
    debug = debug, coroutine = coroutine, setmetatable = setmetatable, getmetatable = getmetatable,
    rawset = rawset, rawget = rawget, require = include_user, _libs = G._libs or {},
    buffactive = {}, player = player,
    world = {weather_element = 'None', day_element = 'Fire', area = '', zone = '', weather = 'Clear',
             day = 'Firesday', moon = 0, moon_pct = 0, weather_id = 0, real_weather = 'Clear',
             real_weather_element = 'None', mog_house = false, in_mog_house = false},
    pet = {isvalid = false, name = '', status = 'Idle', hpp = 0, tp = 0},
    fellow = {isvalid = false}, alliance = alliance, party = alliance[1],
    sets = {naked = {main = empty, sub = empty, range = empty, ammo = empty, head = empty, neck = empty,
                     ear1 = empty, ear2 = empty, body = empty, hands = empty, ring1 = empty, ring2 = empty,
                     back = empty, waist = empty, legs = empty, feet = empty}},
}
for _, key in ipairs(cfg.user_env_keys) do
    user_env[key] = values[key]
end
user_env._G = user_env

-- 7 and 8. The job file body, then get_sets.
local result = {includes = includes, load_errors = load_errors}
local function first_line(message)
    -- "file.lua:3: \nGearSwap: Cannot find…" reads as one line: location, then the first real line.
    message = gsub(tostring(message), '^([^\n]-:%d+:)%s*\n%s*', '%1 ')
    return match(message, '^%s*([^\n]*)') or message
end
local function handler(err)
    return {message = tostring(err), details = traceback(tostring(err), 2)}
end
local function fail(err, partial)
    result.error = timed_out and 'took too long to load' or first_line(err.message)
    result.error_details = err.details
    result.timed_out = timed_out
    result.partial = partial
end

local src = py_read_source(cfg.job_path)
local body, compile_error
if src then
    local ok, f, err = pcall(compile, src, '@' .. basename(cfg.job_path))
    if not ok then compile_error = f elseif not f then compile_error = err else body = f end
else
    compile_error = basename(cfg.job_path) .. ': not readable'
end
local ran = false
if not body then
    fail({message = tostring(compile_error), details = tostring(compile_error)}, false)
else
    setfenv(body, user_env)
    local ok, err = xpcall(body, handler)
    if not ok then
        fail(err, false)  -- GearSwap refuses the file (refresh.lua:166-172)
    else
        ran = true
        local get_sets = rawget(user_env, 'get_sets')
        if type(get_sets) == 'function' then
            local ok2, err2 = xpcall(get_sets, handler)
            if not ok2 then
                fail(err2, true)  -- GearSwap keeps the sets it has (refresh.lua:178-182)
            end
        end
    end
end
sethook()

-- 9. Walk `sets`: every table reached, every edge in walk order (numbers ascending, then strings
-- case-insensitively). Canonical paths and aliases are chosen in Python (gearswap_reader).
if not ran then
    return result
end

local function sorted_keys(t)
    local numbers, strings = {}, {}
    for key in next, t do
        if type(key) == 'number' then
            numbers[#numbers + 1] = key
        elseif type(key) == 'string' then
            strings[#strings + 1] = key
        end
    end
    sort(numbers)
    sort(strings, function(a, b)
        local la, lb = lower(a), lower(b)
        if la ~= lb then return la < lb end
        return a < b
    end)
    for _, key in ipairs(strings) do
        numbers[#numbers + 1] = key
    end
    return numbers
end

local function kind_of(t)
    if t == empty then return nil end
    local has_slot, has_table, has_any = false, false, false
    for key, value in next, t do
        has_any = true
        if slot_of(key) then
            has_slot = true
        elseif type(value) == 'table' then
            has_table = true
        end
    end
    if has_slot then return 'set' end
    if not has_any then return 'empty' end
    if has_table then return 'container' end
    return nil
end

local ids, nodes, edges, tables_by_id = {}, {}, {}, {}
local next_id = 0
local function visit(t, id)
    for _, key in ipairs(sorted_keys(t)) do
        local value = rawget(t, key)
        if type(value) == 'table' and value ~= empty and not slot_of(key) then
            local kind = kind_of(value)
            if kind then
                local child = ids[value]
                local new = not child
                if new then
                    next_id = next_id + 1
                    child = next_id
                    ids[value] = child
                    tables_by_id[child] = value
                    nodes[#nodes + 1] = {id = child, kind = kind}
                end
                edges[#edges + 1] = {parent = id, key = key, child = child}
                if new then visit(value, child) end
            end
        end
    end
end

local sets = rawget(user_env, 'sets')
if type(sets) == 'table' then
    ids[sets] = 0
    visit(sets, 0)
end

local item_ids = {}
local next_item = 0
local function slot_value(t, slot)
    -- The value GearSwap would use for this slot: the canonical key wins over aliases.
    local value = rawget(t, slot)
    if value ~= nil then return value, slot end
    for _, key in ipairs(sorted_keys(t)) do
        if slot_of(key) == slot then return rawget(t, key), key end
    end
end

local function describe(slot, key, value)
    local piece = {slot = slot, original_key = key}
    if value == empty then
        piece.empty = true
        return piece
    end
    if type(value) == 'string' then
        if value == '' then return nil end
        piece.name = value
        return piece
    end
    if type(value) ~= 'table' then return nil end
    local name = rawget(value, 'name')
    if type(name) ~= 'string' then return nil end  -- GearSwap ignores tables without a name
    piece.name = name
    local augments = rawget(value, 'augments')
    if not augments and rawget(value, 'augment') ~= nil then
        augments = {rawget(value, 'augment')}
    end
    local list = {}
    if type(augments) == 'table' then
        for _, index in ipairs(sorted_keys(augments)) do
            local augment = rawget(augments, index)
            if type(augment) == 'string' and augment ~= 'none' then
                list[#list + 1] = augment
            end
        end
    end
    piece.augments = list
    local priority = rawget(value, 'priority')
    if type(priority) == 'number' then piece.priority = priority end
    local bag = rawget(value, 'bag')
    if type(bag) == 'string' then piece.bag = bag end
    if not item_ids[value] then
        next_item = next_item + 1
        item_ids[value] = next_item
    end
    piece.table_id = item_ids[value]
    return piece
end

for _, node in ipairs(nodes) do
    if node.kind == 'set' then
        local t = tables_by_id[node.id]
        local origin = combine_origin[t]
        local pieces = {}
        local seen = {}
        for _, key in ipairs(sorted_keys(t)) do
            local slot = slot_of(key)
            if slot and not seen[slot] then
                seen[slot] = true
                local value, used_key = slot_value(t, slot)
                local piece = describe(slot, used_key, value)
                if piece then
                    local record = origin and origin[slot]
                    if record and ids[record.source] and kind_of(record.source) == 'set'
                            and rawequal(value, record.value)
                            and rawequal((slot_value(record.source, slot)), record.value) then
                        piece.from = ids[record.source]
                    end
                    pieces[#pieces + 1] = piece
                end
            end
        end
        node.pieces = pieces
    end
end

result.nodes = nodes
result.edges = edges
return result
