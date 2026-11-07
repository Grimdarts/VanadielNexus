_addon.name = 'VanadielNexus'
_addon.author = 'Vana\'diel Nexus'
_addon.version = '1.5.1'
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
    return (s:gsub('[%z\1-\31]', function(c)
        return string.format('\\u%04x', c:byte())
    end))
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

-- Storage slips hold their items as bits in the slip's extdata; bit n is the
-- slip's nth item in res.slips (same decoding as Windower libs/slips.lua).
local slips_by_item
local function slip_defs()
    if slips_by_item then return slips_by_item end
    slips_by_item = {}
    local ok, slip_res = pcall(function() return res.slips end)
    if ok and type(slip_res) == 'table' then
        for _, slip in pairs(slip_res) do
            if type(slip) == 'table' and type(slip.item_id) == 'number' and type(slip.items) == 'table' then
                slips_by_item[slip.item_id] = slip
            end
        end
    end
    return slips_by_item
end

local function add_slip_items(found_slips, char_name, inv_list, mat_counts)
    local defs = slip_defs()
    for slip_id, itm in pairs(found_slips) do
        local slip = defs[slip_id]
        local ext = itm.extdata
        if slip and type(ext) == 'string' then
            local slip_name = slip.en or ('Storage Slip ' .. tostring(slip.id))
            for byte_index = 1, #ext do
                local byte = ext:byte(byte_index)
                for bit = 0, 7 do
                    if math.floor(byte / 2 ^ bit) % 2 == 1 then
                        local stored_id = slip.items[(byte_index - 1) * 8 + bit + 1]
                        local r_item = stored_id and stored_id > 0 and res.items[stored_id]
                        if r_item and r_item.en and r_item.en ~= '' then
                            table.insert(inv_list, {
                                name = r_item.en,
                                count = 1,
                                character = char_name,
                                bag = slip_name,
                                augments = '',
                                category = classify_resource_item(r_item),
                                item_id = stored_id
                            })
                            mat_counts[r_item.en] = (mat_counts[r_item.en] or 0) + 1
                        end
                    end
                end
            end
        end
    end
end

-- Like Windower findAll, an already logged-in load may use the current cache.
-- Zone packets invalidate it; 0x01D commits temporary items after its callback.
local inventory_ready = windower.ffxi.get_info().logged_in == true
local inventory_commit_pending = false

local function scan_all_bags()
    if not inventory_ready then return nil end
    -- get_items() uses named keys, not numeric bag IDs (Windower Lua API).
    local items_data = windower.ffxi.get_items()
    local bag_cache = {}
    local player = windower.ffxi.get_player()
    local char_name = (player and player.name) or 'Main'
    local inv_list = {}
    local equipped_list = {}
    local mat_counts = {}
    local found_slips = {}

    if not items_data then
        return nil
    end

    for _, bdef in ipairs(BAG_DEFS) do
        local ok, bag_tbl = pcall(windower.ffxi.get_items, bdef.id)
        -- Never turn an API failure into an authoritative empty snapshot.
        if not ok or type(bag_tbl) ~= 'table' then return nil end
        bag_cache[bdef.id] = bag_tbl
        local occupied = 0
        if type(bag_tbl) == 'table' then
            for idx, itm in pairs(bag_tbl) do
                if type(idx) == 'number' then
                    if type(itm) ~= 'table' or type(itm.id) ~= 'number' or itm.id < 0
                        or itm.id % 1 ~= 0 or type(itm.count) ~= 'number'
                        or itm.count < 0 or itm.count % 1 ~= 0
                        or (itm.id > 0 and itm.count == 0)
                        or (itm.id == 0 and itm.count ~= 0) then return nil end
                end
                if type(idx) == 'number' and type(itm) == 'table' and itm.id and itm.id > 0 and itm.count and itm.count > 0 then
                    occupied = occupied + 1
                    local r_item = res.items[itm.id]
                    if not r_item or not r_item.en or r_item.en == '' then return nil end
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
                    -- A slip in the recycle bin no longer stores anything.
                    if bdef.id ~= 17 and not found_slips[itm.id] and slip_defs()[itm.id] then
                        found_slips[itm.id] = itm
                    end
                end
            end
        end
        -- count is occupied slots, not the sum of item stack quantities.
        if bag_tbl.count ~= nil and (type(bag_tbl.count) ~= 'number'
            or bag_tbl.count ~= occupied) then return nil end
        if bag_tbl.max ~= nil and (type(bag_tbl.max) ~= 'number'
            or bag_tbl.max < occupied or bag_tbl.max < 0
            or bag_tbl.max % 1 ~= 0) then return nil end
    end
    add_slip_items(found_slips, char_name, inv_list, mat_counts)

    local eq_tbl = items_data.equipment
    if type(eq_tbl) == 'table' then
        for slot_id = 0, 15 do
            local sname = SLOT_NAMES[slot_id]
            local inv_idx = eq_tbl[sname]
            local bag_id = eq_tbl[sname .. '_bag']
            if inv_idx and inv_idx > 0 and bag_id ~= nil and bag_cache[bag_id] then
                local itm = bag_cache[bag_id][inv_idx]
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

-- Nonce combines independent per-load VM/socket identity and high-resolution
-- clocks; it is an ordering namespace, not a security credential.
local session_id = string.format('%.6f-%.6f-%s-%s', socket.gettime(), os.clock(), tostring({}), tostring(udp_out))
local update_sequence = 0
local bridge_challenge = ''
local function send_snapshot(payload, sequence)
    -- Stay below the UDP maximum even with the JSON envelope. Hex encoding
    -- permits splitting arbitrary UTF-8 bytes without corrupting item names.
    local chunk_bytes = 10000
    local total = math.ceil(#payload / chunk_bytes)
    if #payload > 2097152 or total > 256 then return end
    local stamp = socket.gettime()
    local scan_id = tostring(sequence)
    for index = 0, total - 1 do
        local fragment = payload:sub(index * chunk_bytes + 1, (index + 1) * chunk_bytes)
        local hex = fragment:gsub('.', function(c) return string.format('%02x', c:byte()) end)
        local packet = string.format(
            '{"type":"SNAPSHOT_CHUNK","session_id":"%s","challenge":"%s","update_seq":%d,"scan_id":"%s","scan_time":%.6f,"index":%d,"total":%d,"data":"%s"}',
            json_escape(session_id), bridge_challenge, sequence, scan_id, stamp, index, total, hex)
        local ok, sent = pcall(function() return udp_out:sendto(packet, UDP_HOST, UDP_SEND_PORT) end)
        if not ok or not sent then return end
    end
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

    local inv_list, eq_list, mat_counts
    if include_bags then
        inv_list, eq_list, mat_counts = scan_all_bags()
        include_bags = inv_list ~= nil
    end
    if include_bags then
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

    local payload = string.format(
        '{"type":"STATE_UPDATE","state":{"player_name":"%s","main_job":"%s","main_job_lvl":%d,"sub_job":"%s","sub_job_lvl":%d,"master_lvl":%d,"zone_name":"%s","materials":%s,"equipped":%s,"inventory":%s}}',
        json_escape(p.name or 'Player'),
        json_escape(p.main_job or 'WAR'),
        p.main_job_level or 99,
        json_escape(p.sub_job or 'SAM'),
        p.sub_job_level or 49,
        p.superior_level or 0,
        json_escape(zone_name),
        mat_json,
        eq_json,
        inv_json
    )

    -- The UI resolution is the coordinate space addon windows are placed in (layout page).
    local ok_res, ws = pcall(windower.get_windower_settings)
    if ok_res and type(ws) == 'table' and tonumber(ws.ui_x_res) and tonumber(ws.ui_y_res) then
        payload = payload:sub(1, -3) .. string.format(',"ui_x_res":%d,"ui_y_res":%d}}', ws.ui_x_res, ws.ui_y_res)
    end
    payload = payload:sub(1, -3) .. ',"snapshot_complete":' .. tostring(include_bags) .. '}}'
    update_sequence = update_sequence + 1
    payload = string.format('{"session_id":"%s","challenge":"%s","update_seq":%d,', json_escape(session_id), bridge_challenge, update_sequence) .. payload:sub(2)
    if include_bags then
        send_snapshot(payload, update_sequence)
    else
        pcall(function() udp_out:sendto(payload, UDP_HOST, UDP_SEND_PORT) end)
    end
end

-- Layout mode (//vn layout): labeled frames stand in for every addon window, because one addon
-- can't move another's. The app sends the frames and writes the final spots into each addon.
-- FFXI reads the left mouse button itself, so a plain left-drag also walks the character; the
-- keyboard controls (Tab / arrows / Enter / Esc) and right-button-held dragging avoid that.
local layout = {active = false, items = {}, frames = {}, buttons = {}, selected = 0, shift = false, swallow = {}}
local FRAME_COLOR = {90, 34, 211, 238}
local SELECTED_COLOR = {150, 233, 196, 106}
local DIK = {esc = 0x01, tab = 0x0F, enter = 0x1C, numpad_enter = 0x9C, lshift = 0x2A, rshift = 0x36}
local ARROWS = {[0xC8] = {0, -1}, [0xD0] = {0, 1}, [0xCB] = {-1, 0}, [0xCD] = {1, 0}}

local function send_message(kind, body)
    update_sequence = update_sequence + 1
    local packet = string.format('{"session_id":"%s","challenge":"%s","update_seq":%d,"type":"%s"%s}',
        json_escape(session_id), bridge_challenge, update_sequence, kind, body or '')
    pcall(function() udp_out:sendto(packet, UDP_HOST, UDP_SEND_PORT) end)
end

local function layout_clear()
    for _, f in ipairs(layout.frames) do
        f.box:destroy()
        f.label:destroy()
    end
    for _, b in pairs(layout.buttons) do b:destroy() end
    if layout.hint then layout.hint:destroy() end
    layout.frames, layout.buttons, layout.hint, layout.active, layout.selected = {}, {}, nil, false, 0
end

local function layout_button(text, x, y, r, g, b)
    local texts = require('texts')
    local t = texts.new(text, {
        pos = {x = x, y = y},
        text = {size = 12, font = 'Arial', stroke = {width = 1, alpha = 255}},
        bg = {alpha = 235, red = r, green = g, blue = b},
        padding = 6,
        flags = {draggable = false, bold = true},
    })
    t:show()
    return t
end

-- The selected frame is the one the arrow keys move
local function layout_select(index)
    for n, f in ipairs(layout.frames) do
        local c = n == index and SELECTED_COLOR or FRAME_COLOR
        f.box:color(c[2], c[3], c[4])
        f.box:alpha(c[1])
    end
    layout.selected = index
end

local function layout_show()
    layout_clear()
    local ok_libs, images, texts = pcall(function() return require('images'), require('texts') end)
    if not ok_libs then return end
    for _, it in ipairs(layout.items) do
        local box = images.new({
            pos = {x = it.x, y = it.y},
            size = {width = it.w, height = it.h},
            color = {alpha = FRAME_COLOR[1], red = FRAME_COLOR[2], green = FRAME_COLOR[3], blue = FRAME_COLOR[4]},
            draggable = true,
        })
        local label = texts.new(it.label, {
            pos = {x = it.x + 4, y = it.y + 2},
            text = {size = 10, font = 'Arial', stroke = {width = 1, alpha = 255}},
            bg = {alpha = 0},
            flags = {draggable = false, bold = true},
        })
        box:show()
        label:show()
        table.insert(layout.frames, {id = it.id, box = box, label = label})
    end
    local ws = windower.get_windower_settings()
    local cx = math.floor(ws.ui_x_res / 2)
    layout.buttons.save = layout_button('Save layout', cx - 130, 40, 14, 165, 198)
    layout.buttons.cancel = layout_button('Cancel', cx + 30, 40, 38, 50, 77)
    layout.hint = texts.new('Tab: next frame    Arrows: move (Shift = 10 px)    Enter: save    Esc: cancel\n'
        .. 'Mouse: hold the RIGHT button, then drag a frame with the left (left alone walks you)', {
        pos = {x = cx - 300, y = 82},
        text = {size = 10, font = 'Arial', stroke = {width = 1, alpha = 255}},
        bg = {alpha = 200, red = 20, green = 24, blue = 36},
        padding = 6,
        flags = {draggable = false},
    })
    layout.hint:show()
    layout.active = true
    if #layout.frames > 0 then layout_select(1) end
    windower.add_to_chat(207, '[VanadielNexus] Layout mode: Tab picks a frame, arrows move it (Shift = 10 px), Enter saves, Esc cancels. '
        .. 'To drag with the mouse, hold the right button first. (//vn layout save | //vn layout cancel)')
end

local function layout_finish(save)
    if not layout.active then return end
    if save then
        local parts = {}
        for _, f in ipairs(layout.frames) do
            local x, y = f.box:pos()
            table.insert(parts, string.format('"%s":[%d,%d]', json_escape(f.id), math.floor(x + 0.5), math.floor(y + 0.5)))
        end
        send_message('LAYOUT_RESULT', ',"positions":{' .. table.concat(parts, ',') .. '}')
        windower.add_to_chat(207, '[VanadielNexus] Layout sent to the app. Your addons move in a moment.')
    else
        windower.add_to_chat(207, '[VanadielNexus] Layout mode closed without saving.')
    end
    layout_clear()
end

-- Mouse kinds: 1 left down, 2 left up. The buttons act on release; a click on a frame selects it.
windower.register_event('mouse', function(kind, x, y, delta, blocked)
    if not layout.active then return end
    for name, b in pairs(layout.buttons) do
        if b:hover(x, y) then
            if kind == 2 then layout_finish(name == 'save') end
            return kind == 1 or kind == 2
        end
    end
    if kind == 1 then
        for n, f in ipairs(layout.frames) do
            if f.box:hover(x, y) then
                layout_select(n)
                return
            end
        end
    end
end)

-- Layout keys are kept from the game, press and release, while layout mode is open
windower.register_event('keyboard', function(dik, pressed, flags, blocked)
    if dik == DIK.lshift or dik == DIK.rshift then
        layout.shift = pressed
        return
    end
    if not pressed and layout.swallow[dik] then
        layout.swallow[dik] = nil
        return true
    end
    if not layout.active or not pressed then return end
    local info = windower.ffxi.get_info()
    if info and info.chat_open then return end   -- typing in the chat line
    if ARROWS[dik] then
        local f = layout.frames[layout.selected]
        if f then
            local step = layout.shift and 10 or 1
            local x, y = f.box:pos()
            f.box:pos(x + ARROWS[dik][1] * step, y + ARROWS[dik][2] * step)
        end
    elseif dik == DIK.tab then
        if #layout.frames > 0 then layout_select(layout.selected % #layout.frames + 1) end
    elseif dik == DIK.enter or dik == DIK.numpad_enter then
        layout_finish(true)
    elseif dik == DIK.esc then
        layout_finish(false)
    else
        return
    end
    layout.swallow[dik] = true
    return true
end)

windower.register_event('incoming chunk', function(id, original, modified, injected, blocked)
    if injected or blocked then return end
    local lo, hi
    if type(original) == 'string' then lo, hi = original:byte(3, 4) end
    local sequence = lo and hi and (lo + 256 * hi) or nil
    if id == 0x00A or id == 0x00B then
        inventory_ready = false
        inventory_commit_pending = false
    elseif inventory_commit_pending and sequence and sequence ~= inventory_commit_pending then
        -- Wait for a different network sequence, not another chunk in the same
        -- packet. get_items() must see the committed 0x01D data first.
        inventory_commit_pending = false
        inventory_ready = true
        build_and_send_state(true)
    elseif id == 0x01D and not inventory_ready and sequence then
        inventory_commit_pending = sequence
    end
end)

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
    if cmd == 'scan' then
        build_and_send_state(true)
        windower.add_to_chat(207, '[VanadielNexus] Scanned all 17 bags and your storage slips and sent update to overlay.')
    elseif cmd == 'layout' then
        local sub = args[1] and args[1]:lower()
        if sub == 'save' or sub == 'cancel' then
            layout_finish(sub == 'save')
        elseif layout.active then
            layout_finish(false)
        else
            send_message('LAYOUT_REQUEST')
            windower.add_to_chat(207, '[VanadielNexus] Asking the app for your layout. Vana\'diel Nexus must be open.')
        end
    else
        windower.add_to_chat(207, '[VanadielNexus] Commands: //vn scan | //vn layout (no keys are bound).')
    end
end)

local last_poll = 0
windower.register_event('prerender', function()
    if layout.active then
        for _, f in ipairs(layout.frames) do
            local x, y = f.box:pos()
            f.label:pos(x + 4, y + 2)
        end
    end
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
            if not parts[2] then
                build_and_send_state(true)
            elseif parts[3] == session_id and #parts[2] == 32 and parts[2]:match('^%x+$') then
                bridge_challenge = parts[2]
                build_and_send_state(true)
            elseif parts[3] ~= session_id then
                -- A bridge still targeting the prior load needs discovery,
                -- never adoption of a nonce meant for another Lua instance.
                build_and_send_state(false)
            end
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
        elseif action == 'LAYOUT_BEGIN' then
            layout.items = {}
        elseif action == 'LAYOUT_ITEM' and #parts >= 7 then
            local x, y, w, h = tonumber(parts[3]), tonumber(parts[4]), tonumber(parts[5]), tonumber(parts[6])
            if x and y and w and h then
                table.insert(layout.items, {id = parts[2], x = x, y = y, w = w, h = h, label = parts[7]})
            end
        elseif action == 'LAYOUT_SHOW' then
            layout_show()
        end
    end
end)
