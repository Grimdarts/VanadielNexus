_addon.name = 'VanadielNexus'
_addon.author = 'Vana\'diel Nexus'
_addon.version = '1.2.0'
_addon.commands = {'vn', 'vanadielnexus', 'nexus'}

local socket = require('socket')
local res = require('resources')
local ok_ext, extdata = pcall(require, 'extdata')

local UDP_HOST = '127.0.0.1'
local UDP_SEND_PORT = 5017   -- Python overlay listener
local UDP_LISTEN_PORT = 5018 -- Addon command listener

local udp_out = socket.udp()
local udp_in = socket.udp()
pcall(function()
    udp_in:setsockname(UDP_HOST, UDP_LISTEN_PORT)
    udp_in:settimeout(0)
end)

local state_cache = {
    mote_modes = {
        OffenseMode = 'Normal',
        HybridMode = 'Normal',
        WeaponskillMode = 'Normal',
        IdleMode = 'Normal',
        CastingMode = 'Normal',
        WeaponSet = 'Default'
    },
    magic_haste = 0,
    gear_haste = 25.0,
    dw_needed = 0,
    haste_group = 'MaxHaste'
}

local BAG_DEFS = {
    {id = 0,  name = 'Inventory'},
    {id = 1,  name = 'Mog Safe 1'},
    {id = 2,  name = 'Mog Storage'},
    {id = 4,  name = 'Mog Locker'},
    {id = 5,  name = 'Mog Satchel'},
    {id = 6,  name = 'Mog Sack'},
    {id = 7,  name = 'Mog Case'},
    {id = 8,  name = 'Wardrobe 1'},
    {id = 9,  name = 'Mog Safe 2'},
    {id = 10, name = 'Wardrobe 2'},
    {id = 11, name = 'Wardrobe 3'},
    {id = 12, name = 'Wardrobe 4'},
    {id = 13, name = 'Wardrobe 5'},
    {id = 14, name = 'Wardrobe 6'},
    {id = 15, name = 'Wardrobe 7'},
    {id = 16, name = 'Wardrobe 8'},
    {id = 17, name = 'Recycle'}
}

local SLOT_NAMES = {
    [0] = 'main', [1] = 'sub', [2] = 'range', [3] = 'ammo',
    [4] = 'head', [5] = 'body', [6] = 'hands', [7] = 'legs',
    [8] = 'feet', [9] = 'neck', [10] = 'waist', [11] = 'left_ear',
    [12] = 'right_ear', [13] = 'left_ring', [14] = 'right_ring', [15] = 'back'
}

local function json_escape(s)
    if s == nil then return '' end
    s = tostring(s)
    s = s:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n'):gsub('\r', '\\r'):gsub('\t', '\\t')
    return s
end

local function decode_augments(item_tbl)
    if not ok_ext or not extdata or not item_tbl or not item_tbl.extdata then
        return ''
    end
    local ok, dec = pcall(extdata.decode, item_tbl)
    if not ok or not dec then return '' end
    local parts = {}
    if dec.rank then
        table.insert(parts, 'Rank ' .. tostring(dec.rank))
    end
    if type(dec.augments) == 'table' then
        for _, aug in ipairs(dec.augments) do
            if aug and aug ~= 'none' and aug ~= '' then
                table.insert(parts, tostring(aug))
            end
        end
    end
    return table.concat(parts, ', ')
end

local function classify_resource_item(res_item)
    if not res_item then return 'General' end
    local cat = tostring(res_item.category or '')
    local slots = res_item.slots
    if cat == 'Weapon' then
        if slots and (slots[2] or slots[3]) and not slots[0] then
            return 'Ranged & Ammo'
        end
        return 'Weapons'
    elseif cat == 'Armor' then
        if slots then
            if slots[1] then return 'Shields, Grips & Straps' end
            if slots[4] or slots[9] then return 'Head & Neck' end
            if slots[5] or slots[6] then return 'Body & Hands' end
            if slots[7] or slots[8] or slots[10] then return 'Legs, Feet & Waist' end
            if slots[11] or slots[12] or slots[13] or slots[14] or slots[15] then return 'Rings, Ears & Back' end
        end
        return 'Armor'
    elseif cat == 'Usable' then
        return 'Consumables & Medicines'
    end
    return 'General / Materials'
end

local function scan_all_bags()
    local items_data = windower.ffxi.get_items()
    local player = windower.ffxi.get_player()
    local char_name = (player and player.name) or 'Main'
    local inv_list = {}
    local equipped_list = {}
    local mat_counts = {}

    if not items_data then
        return inv_list, equipped_list, mat_counts
    end

    for _, bdef in ipairs(BAG_DEFS) do
        local bag_tbl = items_data[bdef.id]
        if type(bag_tbl) == 'table' then
            for idx, itm in pairs(bag_tbl) do
                if type(idx) == 'number' and type(itm) == 'table' and itm.id and itm.id > 0 and itm.count and itm.count > 0 then
                    local r_item = res.items[itm.id]
                    if r_item and r_item.en then
                        local iname = r_item.en
                        local aug_str = decode_augments(itm)
                        local icat = classify_resource_item(r_item)
                        table.insert(inv_list, {
                            name = iname,
                            count = itm.count,
                            character = char_name,
                            bag = bdef.name,
                            augments = aug_str,
                            category = icat,
                            item_id = itm.id
                        })
                        mat_counts[iname] = (mat_counts[iname] or 0) + itm.count
                    end
                end
            end
        end
    end

    local eq_tbl = items_data.equipment
    if type(eq_tbl) == 'table' then
        for slot_id = 0, 15 do
            local sname = SLOT_NAMES[slot_id]
            local inv_idx = eq_tbl[sname]
            local bag_id = eq_tbl[sname .. '_bag']
            if inv_idx and inv_idx > 0 and bag_id ~= nil and items_data[bag_id] then
                local itm = items_data[bag_id][inv_idx]
                if type(itm) == 'table' and itm.id and itm.id > 0 then
                    local r_item = res.items[itm.id]
                    if r_item and r_item.en then
                        table.insert(equipped_list, {
                            slot = sname,
                            name = r_item.en,
                            augments = decode_augments(itm)
                        })
                    end
                end
            end
        end
    end

    return inv_list, equipped_list, mat_counts
end

local function build_and_send_state(include_bags)
    local p = windower.ffxi.get_player()
    local info = windower.ffxi.get_info()
    if not p then return end

    local zone_name = 'Unknown'
    if info and info.zone and res.zones[info.zone] then
        zone_name = res.zones[info.zone].en
    end

    local inv_json = '[]'
    local eq_json = '[]'
    local mat_json = '{}'

    if include_bags then
        local inv_list, eq_list, mat_counts = scan_all_bags()
        local inv_parts = {}
        for _, it in ipairs(inv_list) do
            table.insert(inv_parts, string.format(
                '{"name":"%s","count":%d,"character":"%s","bag":"%s","augments":"%s","category":"%s","item_id":%d}',
                json_escape(it.name), it.count, json_escape(it.character),
                json_escape(it.bag), json_escape(it.augments),
                json_escape(it.category), it.item_id or 0
            ))
        end
        inv_json = '[' .. table.concat(inv_parts, ',') .. ']'

        local eq_parts = {}
        for _, eq in ipairs(eq_list) do
            table.insert(eq_parts, string.format(
                '{"slot":"%s","name":"%s","augments":"%s"}',
                json_escape(eq.slot), json_escape(eq.name), json_escape(eq.augments)
            ))
        end
        eq_json = '[' .. table.concat(eq_parts, ',') .. ']'

        local mat_parts = {}
        for k, v in pairs(mat_counts) do
            table.insert(mat_parts, string.format('"%s":%d', json_escape(k), v))
        end
        mat_json = '{' .. table.concat(mat_parts, ',') .. '}'
    end

    local mote_parts = {}
    for k, v in pairs(state_cache.mote_modes) do
        table.insert(mote_parts, string.format('"%s":"%s"', json_escape(k), json_escape(v)))
    end
    local mote_json = '{' .. table.concat(mote_parts, ',') .. '}'

    local payload = string.format(
        '{"type":"STATE_UPDATE","state":{"player_name":"%s","main_job":"%s","main_job_lvl":%d,"sub_job":"%s","sub_job_lvl":%d,"master_lvl":%d,"zone_name":"%s","magic_haste":%.2f,"gear_haste":%.1f,"dw_needed":%d,"haste_group":"%s","mote_modes":%s,"materials":%s,"equipped":%s,"inventory":%s}}',
        json_escape(p.name or 'Player'),
        json_escape(p.main_job or 'WAR'),
        p.main_job_level or 99,
        json_escape(p.sub_job or 'SAM'),
        p.sub_job_level or 49,
        p.superior_level or 0,
        json_escape(zone_name),
        state_cache.magic_haste,
        state_cache.gear_haste,
        state_cache.dw_needed,
        json_escape(state_cache.haste_group),
        mote_json,
        mat_json,
        eq_json,
        inv_json
    )

    pcall(function()
        udp_out:sendto(payload, UDP_HOST, UDP_SEND_PORT)
    end)
end

-- F10 hotkey is intentionally NOT bound so F8-F12 and modifiers stay free for GearSwap.
windower.register_event('load', function()
    build_and_send_state(true)
end)

windower.register_event('job change', function()
    build_and_send_state(true)
end)

windower.register_event('zone change', function()
    build_and_send_state(false)
end)

windower.register_event('addon command', function(cmd, ...)
    cmd = cmd and cmd:lower() or 'help'
    local args = {...}
    if cmd == 'hud' then
        pcall(function()
            udp_out:sendto('{"type":"TOGGLE_HUD"}', UDP_HOST, UDP_SEND_PORT)
        end)
    elseif cmd == 'scan' then
        build_and_send_state(true)
        windower.add_to_chat(207, '[VanadielNexus] Scanned all 17 bags and sent update to overlay.')
    elseif cmd == 'mote_sync' and args[1] and args[2] then
        local mode_name = args[1]
        local mode_val = table.concat(args, ' ', 2)
        state_cache.mote_modes[mode_name] = mode_val
        build_and_send_state(false)
    else
        windower.add_to_chat(207, '[VanadielNexus] Commands: //vn scan | //vn hud (No F8-F12 hotkeys bound).')
    end
end)

local last_poll = 0
windower.register_event('prerender', function()
    local now = os.clock()
    if now - last_poll < 0.25 then return end
    last_poll = now

    while true do
        local msg = udp_in:receive()
        if not msg then break end
        local parts = {}
        for part in string.gmatch(msg, '([^|]+)') do
            table.insert(parts, part)
        end
        local action = parts[1]
        if action == 'SCAN' then
            build_and_send_state(true)
        elseif action == 'SCAN_GS' then
            windower.send_command('gs validate')
            build_and_send_state(true)
        elseif action == 'GS' and parts[2] then
            windower.send_command('gs c ' .. parts[2])
        elseif action == 'WARP' and parts[2] then
            windower.send_command(parts[2])
        elseif action == 'ADDON' and parts[2] and parts[3] then
            windower.send_command('lua ' .. parts[2] .. ' ' .. parts[3])
        elseif action == 'CMD' and parts[2] then
            windower.send_command(parts[2])
        end
    end
end)
