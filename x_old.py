#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
  Vana'diel Nexus v1.2 — All-in-One FFXI Windower 4 Overlay & Game Assistant
  File: vanadielnexus_overlay.py
================================================================================
  What's New in v1.2:
  1. F10 Hotkey Removed:
     - F8–F12 (plus Ctrl/Alt/Shift/Win modifiers) are 100% untouched by
       Vana'diel Nexus so your GearSwap .lua files and Windower binds work
       without interference.
  2. Page 1 (JSE, REMA & Checkpoint Tracker):
     - Remove Tracked Item with confirmation prompt on all 3 tables (plus Delete
       key & right-click menu).
     - Add Gear / JSE / REMA / Checkpoint outside .lua files (supports unowned
       items, upgrade goals, and job assignment).
     - Add Item via Wiki URL (paste any BG-Wiki, FFXIAH, or FFXIclopedia URL to
       extract the item, assign a job, and add to Page 1 or Page 2).
     - Filter by Current Job or Show All Jobs toggle.
     - Multi-Wiki buttons (BG-Wiki, FFXIAH, FFXIclopedia) + right-click menu on
       all gear tables, laid out cleanly for both windowed and fullscreen modes.
  3. Page 4 (Inventory, Categories & Multi-Bag Browser):
     - Automatic 10-Category Item Classification with collapsible category tree
       folders (or flat view toggle).
     - Smart Stackable & Currency Rollup (totals items like Alexandrite,
       Beitetsu, Pluton, Cards across all bags/characters) while keeping
       same-name gear with different augments strictly separated!
     - Scattered / Multi-Bag Detection (flags items split across 2+ bags or
       characters with a ⚠️ SCATTERED badge and full location breakdown).
     - One-click "📌 Track Selected on Page 1 (Assign Job)" dialog.
     - Auto-import from Windower4 findAll character storage & GearSwap exports.
  4. Page 6 (⌨️ Hotkey & Conflict Manager):
     - Scans & lists hotkeys across FFXI Base Game, Windower scripts/init.txt,
       GearSwap .lua files (Mote & custom job binds), and Addons/Plugins.
     - Flags conflicting keybinds automatically (e.g. F11, F12, Ctrl+F10,
       Alt+F10, F8, F9) and shows exact file paths, line numbers, in-game
       commands, and 1-click Rebind / Comment-Out / Open File tools.
================================================================================
"""

import ctypes
import glob
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    tk = None
    ttk = None
    filedialog = None
    messagebox = None

# ==============================================================================
# PATHS & NETWORK CONFIGURATION
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODULES_DIR = os.path.join(BASE_DIR, "modules")
HOOK_DIR = os.path.join(BASE_DIR, "gearswap_hook")
ADDON_BACKUP_DIR = os.path.join(BASE_DIR, "windower_addon")
DB_FILE = os.path.join(DATA_DIR, "ffxi_database.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# Version & self-update (GitHub Releases). Bump APP_VERSION and tag vX.Y.Z to ship.
APP_VERSION = "1.2.0"
GITHUB_REPO = "Grimdarts/VanadielNexus"
IS_FROZEN = getattr(sys, "frozen", False)


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(settings: dict):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[Warn] Could not save {SETTINGS_FILE}: {e}")


def find_windower_dir() -> str:
    """Saved choice first, then a Windower4 folder next to this app, then common install spots."""
    saved = load_settings().get("windower_dir", "")
    candidates = [
        saved,
        os.path.join(os.path.dirname(BASE_DIR), "Windower4"),
        os.path.join(BASE_DIR, "Windower4"),
        r"C:\Windower4",
        r"C:\Program Files (x86)\Windower4",
        r"C:\Program Files\Windower4",
        os.path.join(os.path.expanduser("~"), "Games", "Windower4"),
    ]
    for c in candidates:
        if c and os.path.isfile(os.path.join(c, "windower.exe")):
            return c
    for c in candidates:
        if c and os.path.isdir(os.path.join(c, "addons")):
            return c
    return saved or candidates[1]


def _version_tuple(ver: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", ver)[:3]) or (0,)


def set_windower_dir(path: str):
    global DEFAULT_WINDOWER_DIR, DEFAULT_ADDON_DIR
    DEFAULT_WINDOWER_DIR = path
    DEFAULT_ADDON_DIR = os.path.join(path, "addons", "VanadielNexus")
    settings = load_settings()
    settings["windower_dir"] = path
    save_settings(settings)


DEFAULT_WINDOWER_DIR = find_windower_dir()
DEFAULT_ADDON_DIR = os.path.join(DEFAULT_WINDOWER_DIR, "addons", "VanadielNexus")

UDP_HOST = "127.0.0.1"
UDP_LISTEN_PORT = 5017  # Receives JSON state from VanadielNexus.lua
UDP_SEND_PORT = 5018    # Sends commands to VanadielNexus.lua

ALL_FFXI_JOBS = [
    "BLU", "SMN", "RUN", "SCH", "RDM", "WAR", "COR", "PLD",
    "THF", "BST", "NIN", "WHM", "BLM", "DRK", "SAM", "DRG",
    "MNK", "RNG", "BRD", "DNC", "GEO", "PUP", "All"
]

# ==============================================================================
# EMBEDDED WINDOWER 4 ADDON CODE (F10 REMOVED) & MOTE HOOK
# ==============================================================================
VANADIEL_NEXUS_LUA_CODE = r"""_addon.name = 'VanadielNexus'
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
"""

MOTE_HOOK_LUA_CODE = """-- Vana'diel Nexus — 1-Click Mote-Include GearSwap Auto-Hook (Mote_Nexus_Hook.lua)
DW_needed = DW_needed or 0
DW        = DW or false

function nexus_push_mote_states()
    if not state then return end
    local tracked = {'OffenseMode', 'HybridMode', 'WeaponskillMode', 'IdleMode', 'CastingMode', 'WeaponSet'}
    for _, sname in ipairs(tracked) do
        if state[sname] and state[sname].value then
            send_command('vn mote_sync ' .. sname .. ' ' .. tostring(state[sname].value))
        end
    end
end

function nexus_determine_haste_group()
    if not classes or not classes.CustomMeleeGroups then return end
    classes.CustomMeleeGroups:clear()
    if DW == true then
        if DW_needed <= 1 then classes.CustomMeleeGroups:append('MaxHaste')
        elseif DW_needed <= 11 then classes.CustomMeleeGroups:append('HighHaste')
        elseif DW_needed <= 21 then classes.CustomMeleeGroups:append('MidHaste')
        else classes.CustomMeleeGroups:append('LowHaste') end
    else
        classes.CustomMeleeGroups:append('MaxHaste')
    end
end

local _orig_job_self_command = job_self_command
function job_self_command(cmdParams, eventArgs)
    if cmdParams and cmdParams[1] and cmdParams[1]:lower() == 'hasteinfo' then
        local val = tonumber(cmdParams[2])
        if val then
            DW_needed = val
            DW = (DW_needed > 0)
            nexus_determine_haste_group()
            if not midaction() and handle_equipping_gear and player then
                handle_equipping_gear(player.status)
            end
        end
        return
    end
    if _orig_job_self_command then _orig_job_self_command(cmdParams, eventArgs) end
    nexus_push_mote_states()
end

if not include_mote_hook_self_cmd and type(self_command) == 'function' and not state then
    include_mote_hook_self_cmd = true
    local _orig_self_command = self_command
    function self_command(command)
        if type(command) == 'string' and command:lower():match('^hasteinfo') then
            local val = tonumber(command:match('hasteinfo%s+(%d+)'))
            if val then
                DW_needed = val
                DW = (DW_needed > 0)
            end
            return
        end
        return _orig_self_command(command)
    end
end

local _orig_display_current_state = display_current_state
function display_current_state(eventArgs)
    if _orig_display_current_state then _orig_display_current_state(eventArgs) end
    nexus_push_mote_states()
end

coroutine.schedule(nexus_push_mote_states, 2)
"""

EXAMPLE_MODULE_PY_CODE = (
    "# Drop-in Custom Plugin Module for Vana'diel Nexus (modules/sortie_helper.py)\n"
    "MODULE_METADATA = {\n"
    "    \"id\": \"mod-sortie-helper\",\n"
    "    \"name\": \"Sortie & Odyssey Daily Checklist Module\",\n"
    "    \"category\": \"Custom Plugin (modules/)\",\n"
    "    \"loaded\": True,\n"
    "    \"autoJob\": \"All Jobs\",\n"
    "    \"desc\": \"Tracks daily Sortie Sector A-H objectives, Old Case +1/+2 counts, and Odyssey Mogolophone timers.\",\n"
    "}\n\n"
    "def on_action(send_udp_func):\n"
    "    send_udp_func(\"SCAN\")\n"
    "    return \"Triggered Sortie/Odyssey inventory & currency refresh via UDP!\"\n"
)

# ==============================================================================
# DEFAULT DATABASE
# ==============================================================================
DEFAULT_DATABASE = {
    "checkpoints": [
        {
            "id": "cp-1",
            "job": "WAR",
            "category": "AEONIC WEAPON (WAR)",
            "title": "Chango (119 AG) — Escha Ru'Aun Step",
            "current": 12,
            "target": 12,
            "unit": "Ru'Aun NMs Cleared",
            "note": "Stopped at Kammavaca & Warder of Courage. Pop items ready in Satchel.",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Chango",
            "pinned": True
        },
        {
            "id": "cp-2",
            "job": "PLD",
            "category": "MYTHIC WEAPON (PLD)",
            "title": "Burtgang — Duties, Tasks, and Deeds",
            "current": 19660,
            "target": 30000,
            "unit": "Alexandrite (18,420 Traded + 1,240 in Case)",
            "note": "All 50 Assaults & Nyzul Token/Ichor steps DONE. Trade remaining at Nashmau.",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Burtgang",
            "pinned": True
        },
        {
            "id": "cp-3",
            "job": "WAR",
            "category": "SORTIE EMPYREAN +3 (WAR)",
            "title": "Boii Lorica +2 -> +3 Upgrade",
            "current": 64250,
            "target": 70000,
            "unit": "Gallimaufry (Need 1x Starstone)",
            "note": "1 more Sortie 8-boss run to hit 70,000 Gallimaufry.",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Boii_Lorica_%2B3",
            "pinned": True
        }
    ],
    "jse_by_job": {
        "BLU": [
            {"id": "blu-af-head", "set": "AF", "slot": "Head", "name": "Assimilator's Keffiyeh +2", "tier": "+2", "location": "Wardrobe 1", "mats": "Need P. BLU Cards (Omen) for +3", "ready": False},
            {"id": "blu-af-body", "set": "AF", "slot": "Body", "name": "Assimilator's Jubbah +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete (Limbus +4 available)", "ready": False},
            {"id": "blu-af-hands", "set": "AF", "slot": "Hands", "name": "Assimilator's Bazubands +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "blu-af-legs", "set": "AF", "slot": "Legs", "name": "Assimilator's Shalwar +2", "tier": "+2", "location": "Wardrobe 1", "mats": "Need P. BLU Cards (Omen) for +3", "ready": False},
            {"id": "blu-af-feet", "set": "AF", "slot": "Feet", "name": "Assimilator's Charuqs +2", "tier": "+2", "location": "Wardrobe 1", "mats": "Need P. BLU Cards (Omen) for +3", "ready": False},
            {"id": "blu-relic-head", "set": "Relic", "slot": "Head", "name": "Luhlaza Keffiyeh +1", "tier": "+1", "location": "Wardrobe 1", "mats": "Dynamis [D] BLU wave clear + Voidhead: BLU for +2/+3", "ready": False},
            {"id": "blu-relic-body", "set": "Relic", "slot": "Body", "name": "Luhlaza Jubbah +2", "tier": "+2", "location": "Wardrobe 1", "mats": "Need Voidtorso: BLU x3 (Dynamis [D]) for +3", "ready": False},
            {"id": "blu-relic-hands", "set": "Relic", "slot": "Hands", "name": "Luhlaza Bazubands +1", "tier": "+1", "location": "Wardrobe 1", "mats": "Need Torsoshard: BLU / Voidhand: BLU", "ready": False},
            {"id": "blu-relic-legs", "set": "Relic", "slot": "Legs", "name": "Luhlaza Shalwar +2", "tier": "+2", "location": "Wardrobe 1", "mats": "Need Voidleg: BLU x3 for +3", "ready": False},
            {"id": "blu-relic-feet", "set": "Relic", "slot": "Feet", "name": "Luhlaza Charuqs +1", "tier": "+1", "location": "Wardrobe 1", "mats": "Need Footshard: BLU / Voidfoot: BLU", "ready": False},
            {"id": "blu-empy-head", "set": "Empy", "slot": "Head", "name": "Hashishin Kavuk +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry + Sapphires for +2/+3", "ready": False},
            {"id": "blu-empy-body", "set": "Empy", "slot": "Body", "name": "Hashishin Mintan +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry + Sapphires for +2/+3", "ready": False},
            {"id": "blu-empy-hands", "set": "Empy", "slot": "Hands", "name": "Hashishin Bazubands +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry + Sapphires for +2/+3", "ready": False},
            {"id": "blu-empy-legs", "set": "Empy", "slot": "Legs", "name": "Hashishin Tayt +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry + Sapphires for +2/+3", "ready": False},
            {"id": "blu-empy-feet", "set": "Empy", "slot": "Feet", "name": "Hashishin Basmak +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry + Sapphires for +2/+3", "ready": False}
        ],
        "SMN": [
            {"id": "smn-af-head", "set": "AF", "slot": "Head", "name": "Convoker's Horn +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "smn-af-body", "set": "AF", "slot": "Body", "name": "Convoker's Doublet +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "smn-af-hands", "set": "AF", "slot": "Hands", "name": "Convoker's Bracers +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "smn-af-legs", "set": "AF", "slot": "Legs", "name": "Convoker's Spats +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "smn-af-feet", "set": "AF", "slot": "Feet", "name": "Convoker's Pigaches +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "smn-relic-head", "set": "Relic", "slot": "Head", "name": "Glyphic Horn +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "smn-relic-body", "set": "Relic", "slot": "Body", "name": "Glyphic Doublet +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "smn-relic-hands", "set": "Relic", "slot": "Hands", "name": "Glyphic Bracers +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "smn-relic-legs", "set": "Relic", "slot": "Legs", "name": "Glyphic Spats +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "smn-relic-feet", "set": "Relic", "slot": "Feet", "name": "Glyphic Pigaches +2", "tier": "+2", "location": "Wardrobe 1", "mats": "Need Voidfoot: SMN x3 for +3", "ready": False},
            {"id": "smn-empy-head", "set": "Empy", "slot": "Head", "name": "Beckoner's Horn +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "smn-empy-body", "set": "Empy", "slot": "Body", "name": "Beckoner's Doublet +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "smn-empy-hands", "set": "Empy", "slot": "Hands", "name": "Beckoner's Bracers +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "smn-empy-legs", "set": "Empy", "slot": "Legs", "name": "Beckoner's Spats +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "smn-empy-feet", "set": "Empy", "slot": "Feet", "name": "Beckoner's Pigaches +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False}
        ],
        "RUN": [
            {"id": "run-af-head", "set": "AF", "slot": "Head", "name": "Runeist Bandeau +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "run-af-body", "set": "AF", "slot": "Body", "name": "Runeist's Coat +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "run-af-hands", "set": "AF", "slot": "Hands", "name": "Runeist's Mitons +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "run-af-legs", "set": "AF", "slot": "Legs", "name": "Rune. Trousers +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "run-af-feet", "set": "AF", "slot": "Feet", "name": "Runeist's Boots +3", "tier": "+3", "location": "Wardrobe 1", "mats": "+3 Complete", "ready": False},
            {"id": "run-relic-head", "set": "Relic", "slot": "Head", "name": "Futhark Bandeau +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Dynamis [D] RUN upgrades for +2/+3", "ready": False},
            {"id": "run-relic-body", "set": "Relic", "slot": "Body", "name": "Futhark Coat +3", "tier": "+3", "location": "Wardrobe 2", "mats": "+3 Complete", "ready": False},
            {"id": "run-relic-hands", "set": "Relic", "slot": "Hands", "name": "Futhark Mitons +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Dynamis [D] RUN upgrades for +2/+3", "ready": False},
            {"id": "run-relic-legs", "set": "Relic", "slot": "Legs", "name": "Futhark Trousers +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Dynamis [D] RUN upgrades for +2/+3", "ready": False},
            {"id": "run-relic-feet", "set": "Relic", "slot": "Feet", "name": "Futhark Boots +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Dynamis [D] RUN upgrades for +2/+3", "ready": False},
            {"id": "run-empy-head", "set": "Empy", "slot": "Head", "name": "Erilaz Galea +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "run-empy-body", "set": "Empy", "slot": "Body", "name": "Erilaz Surcoat +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "run-empy-hands", "set": "Empy", "slot": "Hands", "name": "Erilaz Gauntlets +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "run-empy-legs", "set": "Empy", "slot": "Legs", "name": "Eri. Leg Guards +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "run-empy-feet", "set": "Empy", "slot": "Feet", "name": "Erilaz Greaves +1", "tier": "+1", "location": "Wardrobe 2", "mats": "Sortie Gallimaufry for +2/+3", "ready": False}
        ],
        "SCH": [
            {"id": "sch-af-head", "set": "AF", "slot": "Head", "name": "Academic's Mortarboard +1", "tier": "+1", "location": "Wardrobe 3", "mats": "Omen P. SCH Cards for +2/+3", "ready": False},
            {"id": "sch-relic-head", "set": "Relic", "slot": "Head", "name": "Pedagogy Mortarboard +1", "tier": "+1", "location": "Wardrobe 3", "mats": "Dynamis [D] SCH upgrades for +2/+3", "ready": False},
            {"id": "sch-relic-body", "set": "Relic", "slot": "Body", "name": "Pedagogy Gown +1", "tier": "+1", "location": "Wardrobe 3", "mats": "Dynamis [D] SCH upgrades for +2/+3", "ready": False},
            {"id": "sch-relic-legs", "set": "Relic", "slot": "Legs", "name": "Pedagogy Pants +1", "tier": "+1", "location": "Wardrobe 3", "mats": "Dynamis [D] SCH upgrades for +2/+3", "ready": False},
            {"id": "sch-empy-head", "set": "Empy", "slot": "Head", "name": "Arbatel Bonnet +1", "tier": "+1", "location": "Wardrobe 3", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "sch-empy-body", "set": "Empy", "slot": "Body", "name": "Arbatel Gown +1", "tier": "+1", "location": "Wardrobe 3", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "sch-empy-hands", "set": "Empy", "slot": "Hands", "name": "Arbatel Bracers +1", "tier": "+1", "location": "Wardrobe 3", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "sch-empy-legs", "set": "Empy", "slot": "Legs", "name": "Arbatel Pants +1", "tier": "+1", "location": "Wardrobe 3", "mats": "Sortie Gallimaufry for +2/+3", "ready": False},
            {"id": "sch-empy-feet", "set": "Empy", "slot": "Feet", "name": "Arbatel Loafers +1", "tier": "+1", "location": "Wardrobe 3", "mats": "Sortie Gallimaufry for +2/+3", "ready": False}
        ],
        "RDM": [
            {"id": "rdm-af-body", "set": "AF", "slot": "Body", "name": "Atrophy Tabard +3", "tier": "+3", "location": "Wardrobe 4", "mats": "50/50 P. RDM Cards • Ready for +4!", "ready": True},
            {"id": "rdm-relic-head", "set": "Relic", "slot": "Head", "name": "Vitiation Chapeau +3", "tier": "+3", "location": "Wardrobe 4", "mats": "Max Augmented (Path C Rank 25/25)", "ready": False},
            {"id": "rdm-empy-legs", "set": "Empy", "slot": "Legs", "name": "Lethargy Fuseau +3", "tier": "+3", "location": "Wardrobe 4", "mats": "Complete (Sortie +3 Unlocked)", "ready": False}
        ],
        "WAR": [
            {"id": "war-af-head", "set": "AF", "slot": "Head", "name": "Pummeler's Mask +3", "tier": "+3", "location": "Wardrobe 1", "mats": "35/35 P. WAR Cards • 1/1 Maliya. Orb (Ready for +4!)", "ready": True},
            {"id": "war-af-body", "set": "AF", "slot": "Body", "name": "Pummeler's Lorica +3", "tier": "+3", "location": "Wardrobe 1", "mats": "18/50 P. WAR Cards • 0/3 Lightweave Silk", "ready": False},
            {"id": "war-af-hands", "set": "AF", "slot": "Hands", "name": "Pummeler's Mufflers +3", "tier": "+3", "location": "Wardrobe 1", "mats": "12/35 P. WAR Cards • 1/3 Cyan Orb", "ready": False},
            {"id": "war-af-legs", "set": "AF", "slot": "Legs", "name": "Pummeler's Cuisses +3", "tier": "+3", "location": "Wardrobe 1", "mats": "35/40 P. WAR Cards • 2/3 Niobium Ore", "ready": False},
            {"id": "war-af-feet", "set": "AF", "slot": "Feet", "name": "Pummeler's Calligae +3", "tier": "+3", "location": "Wardrobe 1", "mats": "35/35 P. WAR Cards • Ready for +4!", "ready": True},
            {"id": "war-relic-head", "set": "Relic", "slot": "Head", "name": "Agoge Mask +3", "tier": "+3", "location": "Wardrobe 1", "mats": "Max Augmented (Path A Rank 25/25)", "ready": False},
            {"id": "war-relic-legs", "set": "Relic", "slot": "Legs", "name": "Agoge Cuisses +2", "tier": "+2", "location": "Porter Slip 25", "mats": "3/3 Voidleg: WAR • 1/3 Corpselight (Need 2)", "ready": False},
            {"id": "war-empy-head", "set": "Empy", "slot": "Head", "name": "Boii Mask +3", "tier": "+3", "location": "Wardrobe 2", "mats": "Complete (Sortie +3 Unlocked)", "ready": False},
            {"id": "war-empy-body", "set": "Empy", "slot": "Body", "name": "Boii Lorica +2", "tier": "+2", "location": "Wardrobe 2", "mats": "64,250/70,000 Gallimaufry • 1/1 Starstone", "ready": False},
            {"id": "war-empy-legs", "set": "Empy", "slot": "Legs", "name": "Boii Cuisses +3", "tier": "+3", "location": "Wardrobe 2", "mats": "Complete (Sortie +3 Unlocked)", "ready": False}
        ],
        "COR": [
            {"id": "cor-af-body", "set": "AF", "slot": "Body", "name": "Laksamana's Frac +3", "tier": "+3", "location": "Wardrobe 3", "mats": "40/50 P. COR Cards • 2/2 Siren's Hair", "ready": False},
            {"id": "cor-relic-head", "set": "Relic", "slot": "Head", "name": "Lanun Tricorne +3", "tier": "+3", "location": "Wardrobe 3", "mats": "Max Augmented (Luzaf's Ring / Phantom Roll)", "ready": False},
            {"id": "cor-empy-feet", "set": "Empy", "slot": "Feet", "name": "Chasseur's Bottes +3", "tier": "+3", "location": "Wardrobe 3", "mats": "Complete (Sortie +3 Unlocked)", "ready": False},
            {"id": "cor-empy-body", "set": "Empy", "slot": "Body", "name": "Chasseur's Frac +2", "tier": "+2", "location": "Wardrobe 3", "mats": "64,250/70,000 Gallimaufry • 0/1 Starstone", "ready": False}
        ],
        "PLD": [
            {"id": "pld-af-body", "set": "AF", "slot": "Body", "name": "Reverence Surcoat +3", "tier": "+3", "location": "Wardrobe 2", "mats": "22/50 P. PLD Cards", "ready": False},
            {"id": "pld-relic-body", "set": "Relic", "slot": "Body", "name": "Caballarius Surcoat +3", "tier": "+3", "location": "Porter Slip 25", "mats": "Path A Rank 20/25", "ready": False},
            {"id": "pld-empy-hands", "set": "Empy", "slot": "Hands", "name": "Chevalier's Gauntlets +3", "tier": "+3", "location": "Wardrobe 2", "mats": "Complete (Sortie +3 Unlocked)", "ready": False}
        ]
    },
    "rema_weapons": [
        {"id": "rema-nirvana", "name": "Nirvana", "type": "Mythic", "job": "SMN", "stage": "iLvl 119 III", "progressPct": 100, "detail": "Equipped / Owned (Garland of Bliss & Blood Pact Dmg +40)", "rp": "Augmented via Riftborn Boulders"},
        {"id": "rema-tizona", "name": "Tizona", "type": "Mythic", "job": "BLU", "stage": "iLvl 119 III", "progressPct": 100, "detail": "Equipped / Owned (Expiacion & MP Return Aftermath)", "rp": "Augmented via Beitetsu / Pluton"},
        {"id": "rema-epeolatry", "name": "Epeolatry", "type": "Ergon", "job": "RUN", "stage": "iLvl 119 III", "progressPct": 100, "detail": "Equipped / Owned (Dimidiation & Liement Aftermath)", "rp": "Augmented via Beitetsu"},
        {"id": "rema-lionheart", "name": "Lionheart", "type": "Aeonic", "job": "RUN", "stage": "iLvl 119 III (Ultimate SC)", "progressPct": 100, "detail": "Equipped / Owned (Resolution & Ultimate Skillchains)", "rp": "Rank 15 via Beitetsu"},
        {"id": "rema-1", "name": "Chango", "type": "Aeonic", "job": "WAR", "stage": "Stage 3 (Escha - Ru'Aun NMs)", "progressPct": 68, "detail": "Zitah 15/15 Done • Ru'Aun 12/12 Done • Reisenjima 0/18 • 50,000 Beads Paid", "rp": "Will unlock R15 on completion"},
        {"id": "rema-2", "name": "Ukonvasara", "type": "Empyrean", "job": "WAR", "stage": "iLvl 119 III (Afterglow R15)", "progressPct": 100, "detail": "75/75 Briareus • 50/50 Sobek • 50/50 Apademak • 1,500 HMP • 60 Riftdross", "rp": "Path A: Rank 15/15 Complete"},
        {"id": "rema-3", "name": "Burtgang", "type": "Mythic", "job": "PLD", "stage": "Stage 3 (Alexandrite & Tokens)", "progressPct": 65, "detail": "19,660 / 30,000 Alexandrite • 150,000 Nyzul Tokens Done • 100,000 Ichor Done", "rp": "1,450 / 10,000 Plutons banked"},
        {"id": "rema-4", "name": "Death Penalty", "type": "Mythic", "job": "COR", "stage": "iLvl 119 III (Rank 15/15)", "progressPct": 100, "detail": "Complete & Augmented (Leaden Salute +30% / aftermath active)", "rp": "Path A: Rank 15/15 Complete"},
        {"id": "rema-5", "name": "Laphria (Stage 4)", "type": "Prime", "job": "WAR", "stage": "Stage 4 -> Stage 5 (Sortie)", "progressPct": 64, "detail": "64,250 / 100,000 Gallimaufry • 2/3 Eikondrite • 1/1 Prime Soul", "rp": "Unlocks Disaster aftermath"}
    ],
    "wishlist": [
        {
            "id": "wl-smn-1",
            "job": "SMN",
            "name": "Lugalbanda Earring",
            "slot": "Earring (BLM / SMN / SCH / GEO)",
            "sourceType": "Omen (Boss - Kei / Ou)",
            "zone": "Reisenjima Henge (Omen)",
            "obtainHow": "Drops from Kei (Omen Boss). Grants Pet: Mag. Acc.+15, Pet: MAB+15, Blood Pact Dmg.+10.",
            "costOrPop": "1x Mystical Canteen",
            "detectedFrom": "SMN Wishlist Goal",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Lugalbanda_Earring",
            "pinned": True
        },
        {
            "id": "wl-smn-2",
            "job": "SMN",
            "name": "Enmerkar Earring",
            "slot": "Earring (SMN / BST / PUP)",
            "sourceType": "Omen (Boss - Kyou)",
            "zone": "Reisenjima Henge (Omen)",
            "obtainHow": "Drops from Kyou (Omen Boss). Grants Pet: Acc+15, Pet: Mag. Acc.+15, Pet: DT-3%, Blood Pact Dmg.+8.",
            "costOrPop": "1x Mystical Canteen",
            "detectedFrom": "SMN Need to Get List",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Enmerkar_Earring",
            "pinned": True
        },
        {
            "id": "wl-1",
            "job": "WAR",
            "name": "Sakpata's Helm",
            "slot": "Head (WAR / PLD / DRK)",
            "sourceType": "Odyssey (Sheol Gaol)",
            "zone": "Rabao -> Odyssey (Sheol Gaol)",
            "obtainHow": "Defeat Ngai (Atonement Tier 3 NM) in Sheol Gaol to unlock purchase from ???, then augment to Rank 25-30 using Lustreless Wing / Segments.",
            "costOrPop": "1x Mogolophone II (3,000 Segments) • Rank RP via Lustreless Wing",
            "detectedFrom": "Detected missing in WAR_Mote.lua (sets.engaged.DT)",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Sakpata%27s_Helm",
            "pinned": True
        },
        {
            "id": "wl-2",
            "job": "WAR",
            "name": "Boii Earring +2",
            "slot": "Right Ear (WAR Only)",
            "sourceType": "Sortie (Old Case +1 / +2)",
            "zone": "Outer Ra'Kaznar (Sortie)",
            "obtainHow": "Drops randomly from Old Case +1 (earned by defeating Basement NMs E-H or Aminon) or high-tier Coffers/Caskets inside Sortie.",
            "costOrPop": "Ra'Kaznar Starstone / Old Case +1 RNG",
            "detectedFrom": "Detected missing in WAR_Mote.lua (sets.precast.WS['Upheaval'])",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Boii_Earring_%2B2",
            "pinned": False
        },
        {
            "id": "wl-3",
            "job": "All",
            "name": "Null Shawl",
            "slot": "Back (All Jobs)",
            "sourceType": "Limbus (Revamped)",
            "zone": "Temenos / Apollyon",
            "obtainHow": "Exchange Temenos & Apollyon Units or Matter from revamped Limbus chests, then rank up via Limbus augment NPC.",
            "costOrPop": "Temenos / Apollyon Units",
            "detectedFrom": "Added manually to Wishlist",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Null_Shawl",
            "pinned": False
        }
    ],
    "catalog_db": {
        "Crepuscular Cloak": {
            "slot": "Head/Body (WAR / PLD / DRK / RDM / BLM)",
            "sourceType": "High-Tier Mission Battle (HTMB)",
            "zone": "Abyssea - Empyreal Paradox (★The Wyrm God)",
            "obtainHow": "Drops from ★The Wyrm God (Shinryu) on Difficult / Very Difficult, or purchased during Seasonal Mog Bonanza / Login Campaigns.",
            "costOrPop": "30 Merit Points (Dawn Phantom Gem from Trisvain in Northern San d'Oria)",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Crepuscular_Cloak"
        },
        "Dagon Breastplate": {
            "slot": "Body (WAR / MNK / SAM / NIN)",
            "sourceType": "Omen (Final Boss - Ou)",
            "zone": "Reisenjima Henge (Omen)",
            "obtainHow": "Drops from Ou (Final Boss of Omen after collecting all 5 boss Astral/Umbral key items: Fu, Kyou, Kei, Gin, Kin).",
            "costOrPop": "1x Mystical Canteen + 5 Omen Boss Key Items",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Dagon_Breastplate"
        },
        "Moonlight Ring": {
            "slot": "Ring (WAR / PLD / DRK / SAM / DRG / RUN)",
            "sourceType": "Synthesis / Auction House",
            "zone": "Auction House (Goldsmithing / Bonecraft)",
            "obtainHow": "Crafted via Bonecraft (110) using Defending/Moonbeam materials or purchased directly off the Auction House (HP+110, Acc+8, DT-5%).",
            "costOrPop": "Auction House (~15M-25M Gil depending on server)",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Moonlight_Ring"
        },
        "Fotia Gorget": {
            "slot": "Neck (All Jobs)",
            "sourceType": "Synergy (Sea Elemental Gorgets)",
            "zone": "Al'Taieu + Synergy Furnace",
            "obtainHow": "Combine all 8 Sea Elemental Gorgets (Flame, Snow, Breeze, Soil, Thunder, Aqua, Light, Shadow Gorgets from Al'Taieu organs) via Synergy.",
            "costOrPop": "8x Elemental Gorgets (Phuabo, Xzomit, Aern, Hpemde, Yovra organs)",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Fotia_Gorget"
        },
        "Utu Grip": {
            "slot": "Sub / Grip (WAR / DRK / SAM / DRG / RUN)",
            "sourceType": "Omen (Boss - Kin)",
            "zone": "Reisenjima Henge (Omen)",
            "obtainHow": "Drops from Kin (Omen Boss on the Kin route). Grants DEX+10, Acc+30, Magic Acc+30, Weapon Skill Acc+30, Double Attack+4%.",
            "costOrPop": "1x Mystical Canteen",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Utu_Grip"
        },
        "Regal Ring": {
            "slot": "Ring (WAR / PLD / DRK / BST / SAM / NIN / DRG / RUN)",
            "sourceType": "Omen (Final Boss - Ou)",
            "zone": "Reisenjima Henge (Omen)",
            "obtainHow": "Drops from Ou (Final Boss of Omen). Grants STR/DEX/VIT/AGI+10, Attack+20, and Niqmaddu/Regal set bonus.",
            "costOrPop": "1x Mystical Canteen + 5 Omen Boss Key Items",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Regal_Ring"
        },
        "Epaminondas's Ring": {
            "slot": "Ring (All Jobs — WSD+5%)",
            "sourceType": "A.M.A.N. Trove / Auction House",
            "zone": "Horlais Peak / Waughroon / Balga's Dais or AH",
            "obtainHow": "Drops from A.M.A.N. Trove (Mars / Venus Orbs) or purchased from the Auction House under Rings.",
            "costOrPop": "Mars/Venus Orb or Auction House Gil",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Epaminondas%27s_Ring"
        },
        "Nyame Mail": {
            "slot": "Body (All Jobs)",
            "sourceType": "Odyssey (Sheol Gaol)",
            "zone": "Rabao -> Odyssey (Sheol Gaol)",
            "obtainHow": "Defeat Bumba (Atonement Tier 4 NM) in Sheol Gaol to unlock purchase, then augment Path B (WSD+12%, MAB+30) via Lustreless Hide.",
            "costOrPop": "1x Mogolophone II (3,000 Segments) • Rank RP via Lustreless Hide",
            "wikiUrl": "https://www.bg-wiki.com/ffxi/Nyame_Mail"
        }
    }
}


# ==============================================================================
# WIKI URL BUILDER & PARSER HELPERS
# ==============================================================================
def build_wiki_urls(item_name: str, custom_bg_url: str = "") -> dict:
    """Return URLs for BG-Wiki, FFXIAH, and FFXIclopedia for a given FFXI item name."""
    clean = (item_name or "").strip()
    # Strip trailing quantity or stage tags in parentheses if present
    clean = re.sub(r"\s*\((?:Stage|iLvl|119|x\d+|Total).*?\)\s*$", "", clean, flags=re.IGNORECASE).strip()
    if not clean:
        return {
            "bgwiki": "https://www.bg-wiki.com",
            "ffxiah": "https://www.ffxiah.com",
            "ffxiclopedia": "https://ffxiclopedia.fandom.com"
        }
    bg_slug = urllib.parse.quote(clean.replace(" ", "_"), safe="_-.'()")
    q_slug = urllib.parse.quote_plus(clean)
    return {
        "bgwiki": custom_bg_url if (custom_bg_url and "bg-wiki.com" in custom_bg_url) else f"https://www.bg-wiki.com/ffxi/{bg_slug}",
        "ffxiah": f"https://www.ffxiah.com/search/item?q={q_slug}",
        "ffxiclopedia": f"https://ffxiclopedia.fandom.com/wiki/{bg_slug}"
    }


def open_item_wiki(item_name: str, provider: str = "bgwiki", custom_bg_url: str = ""):
    urls = build_wiki_urls(item_name, custom_bg_url)
    target = urls.get(provider, urls["bgwiki"])
    webbrowser.open(target)


def parse_wiki_url_or_name(raw_input: str) -> dict:
    """
    Accepts a BG-Wiki URL, FFXIAH URL, FFXIclopedia URL, or raw item name.
    Extracts the item name and optional metadata.
    """
    s = (raw_input or "").strip()
    if not s:
        return {"name": "", "wikiUrl": "", "source_site": ""}

    if s.startswith("http://") or s.startswith("https://"):
        parsed = urllib.parse.urlparse(s)
        host = parsed.netloc.lower()
        path = urllib.parse.unquote(parsed.path)
        item_name = ""

        if "bg-wiki.com" in host:
            # e.g. /ffxi/Sakpata's_Helm or /ffxi/Boii_Earring_+2
            slug = path.split("/ffxi/")[-1] if "/ffxi/" in path else path.strip("/").split("/")[-1]
            item_name = slug.replace("_", " ").strip()
            source_site = "BG-Wiki"
        elif "ffxiclopedia" in host:
            slug = path.split("/wiki/")[-1] if "/wiki/" in path else path.strip("/").split("/")[-1]
            item_name = slug.replace("_", " ").strip()
            source_site = "FFXIclopedia"
        elif "ffxiah.com" in host:
            qs = urllib.parse.parse_qs(parsed.query)
            if "q" in qs and qs["q"]:
                item_name = qs["q"][0].strip()
            else:
                slug = path.strip("/").split("/")[-1]
                item_name = slug.replace("-", " ").replace("_", " ").strip()
            source_site = "FFXIAH"
        else:
            slug = path.strip("/").split("/")[-1]
            item_name = slug.replace("_", " ").strip()
            source_site = host

        # Optional lightweight title check if item_name is numeric (e.g. ffxiah.com/item/21565)
        if item_name.isdigit():
            try:
                req = urllib.request.Request(s, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    html = resp.read(32768).decode("utf-8", errors="ignore")
                    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
                    if m:
                        t_txt = m.group(1).split("-")[0].split("|")[0].strip()
                        if t_txt:
                            item_name = t_txt
            except Exception:
                item_name = f"FFXIAH Item #{item_name}"

        urls = build_wiki_urls(item_name, s if "bg-wiki.com" in host else "")
        return {
            "name": item_name,
            "wikiUrl": urls["bgwiki"],
            "ffxiahUrl": urls["ffxiah"],
            "ffxiclopediaUrl": urls["ffxiclopedia"],
            "source_site": source_site
        }
    else:
        urls = build_wiki_urls(s)
        return {
            "name": s,
            "wikiUrl": urls["bgwiki"],
            "ffxiahUrl": urls["ffxiah"],
            "ffxiclopediaUrl": urls["ffxiclopedia"],
            "source_site": "Manual / Direct Name"
        }


# ==============================================================================
# PAGE 4: ITEM CATEGORIZATION, CONSOLIDATION & SCATTERED-BAG ENGINE
# ==============================================================================
ITEM_CATEGORIES = [
    "💎 Upgrade Currencies & REMA / JSE Mats",
    "⚔️ Weapons (Main / Sub)",
    "🛡️ Shields, Grips & Straps",
    "🏹 Ranged & Ammo",
    "👑 Head & Neck",
    "🧥 Body & Hands",
    "👖 Legs, Feet & Waist",
    "💍 Rings, Earrings & Back (Capes)",
    "🧪 Consumables, Food & Medicines",
    "📦 General, Pop Items & Storage"
]


def classify_ffxi_item(name: str, category_hint: str = "", augments: str = "") -> str:
    """
    Classifies an FFXI item into one of the 10 display categories for Page 4.
    """
    nl = (name or "").lower().strip()
    ch = (category_hint or "").lower().strip()

    # 1. Check Upgrade Currencies & REMA / JSE Materials first
    currency_keywords = (
        "alexandrite", "pluton", "beitetsu", "riftborn boulder", "heavy metal plate",
        "riftdross", "riftcinder", "card", "voidhead", "voidtorso", "voidhand", "voidleg",
        "voidfoot", "headshard", "torsoshard", "handshard", "legshard", "footshard",
        "lustreless", "starstone", "gallimaufry", "eikondrite", "abjuration", "detritus",
        "scale", "byne bill", "bronzepiece", "whiteshell", "silverpiece", "goldpiece",
        "jade", "cinder", "dross", "mulcibar", "pouch", "case +1", "case +2", "voucher",
        "seal", "crest", "orb", "corpselight", "siren's hair", "niobium", "lightweave",
        "scrap", "organ", "chip", "stone +1", "stone +2", "medal"
    )
    # Exclude actual equippable rings/earrings/capes/ammo from currency match
    gear_suffixes = (
        "ring", "earring", "cape", "mantle", "shawl", "belt", "sash", "obi", "rope",
        "yotai", "tathlum", "bomblet", "feather", "pinion", "arrow", "bullet", "bolt",
        "shuriken", "boomerang", "chakram", "shield", "buckler", "grip", "strap",
        "helm", "hat", "cap", "crown", "masque", "mask", "bandeau", "coif", "keffiyeh",
        "kavuk", "mortarboard", "bonnet", "chapeau", "chappel", "galea", "visor",
        "hairpin", "hood", "tam", "sallet", "headpiece", "zucchetto", "coronal",
        "coat", "lorica", "breastplate", "mail", "surcoat", "tabard", "jubbah",
        "mintan", "doublet", "gown", "sayon", "kaftan", "jacket", "platemail",
        "harness", "corazza", "robe", "chasuble", "chas.", "jupon", "vest", "tunic",
        "tunica", "apron", "garb", "kalasiris", "shomonjijoe", "cuirie",
        "gauntlets", "mufflers", "gloves", "mitts", "mittens", "bracers", "bazubands",
        "gantherots", "mitons", "cuffs", "wrist.", "dastanas", "fin. ga.", "manopolas",
        "bazu.", "armlets", "gages",
        "cuisses", "trousers", "subligar", "pants", "slops", "tights", "fuseau",
        "spats", "shalwar", "tayt", "chausses", "cosciales", "lappas", "braconi",
        "seraweels", "sera.", "hose", "guards",
        "greaves", "calligae", "boots", "bottes", "sollerets", "sabots", "pumps",
        "pigaches", "loafers", "houseaux", "charuqs", "basmak", "leggings", "gambieras",
        "jam.", "clogs", "crackows", "gaiters", "galosh.", "socks", "ocreae",
        "torque", "gorget", "necklace", "pendant", "collar", "amulet", "choker",
        "beads", "locket", "charm", "kubikazari"
    )

    is_obvious_gear = any(g in nl for g in gear_suffixes) or bool((augments or "").strip())

    if not is_obvious_gear and any(k in nl for k in currency_keywords):
        return "💎 Upgrade Currencies & REMA / JSE Mats"

    # 2. Consumables, Food & Medicines
    consumable_keywords = (
        "daifuku", "sushi", "ramen", "akamochi", "stewpot", "crepe", "pie", "bun",
        "echo drops", "remedy", "holy water", "panacea", "antacid", "elixir",
        "potion", "ether", "milk", "juice", "cluster", "crystal", "reraiser",
        "warp", "tabula", "forbidden key", "linkpearl", "linkshell"
    )
    if not is_obvious_gear and (any(k in nl for k in consumable_keywords) or "consumable" in ch):
        return "🧪 Consumables, Food & Medicines"

    # 3. Shields, Grips & Straps
    if any(k in nl for k in ("shield", "buckler", "grip", "strap", "culminus", "sors", "ammurapi", "adapa", "genmei shield", "beatific shield")) or "shield" in ch:
        return "🛡️ Shields, Grips & Straps"

    # 4. Ranged & Ammo
    if any(k in nl for k in (
        "tathlum", "bomblet", "feather", "pinion", "sachet", "treatise", "eye",
        "floestone", "focal orb", "sapience orb", "ginsen", "hydrocera", "impatiens",
        "knobkierrie", "yamarang", "shuriken", "boomerang", "bow", "gun", "crossbow",
        "fomalhaut", "death penalty", "gastraphetes", "annihilator", "armageddon",
        "fail-not", "yoichinoyumi", "gjallarhorn", "daurdabla", "marsyas", "yasakani",
        "regal gem", "esper stone", "kalboron stone", "ghastly", "pemphredo", "staunch"
    )) or "ranged" in ch:
        return "🏹 Ranged & Ammo"

    # 5. Weapons (Main / Sub)
    weapon_keywords = (
        "chango", "ukonvasara", "burtgang", "laphria", "nirvana", "tizona", "epeolatry",
        "lionheart", "naegling", "colada", "aettir", "arktoi", "chidori", "izhiikoh",
        "nibiru", "akademos", "coeus", "odium", "isuka", "rubicundity", "espiritus",
        "gridarvor", "fettering", "raicho", "siriti", "chatoyant", "keraunos",
        "bolelabunga", "rogetsurin", "kannakiri", "excalipoor", "gada", "pukulatmuj",
        "hepatizon", "deacon", "sword", "blade", "saber", "axe", "chopper", "katana",
        "cudgel", "rod", "staff", "pole", "scythe", "lance", "spear", "dagger", "knife",
        "claws", "fists", "bell", "virga", "brand", "debahocho", "serenity"
    )
    if any(k in nl for k in weapon_keywords) or "weapon" in ch:
        return "⚔️ Weapons (Main / Sub)"

    # 6. Head & Neck
    head_neck_keywords = (
        "helm", "hat", "cap", "crown", "masque", "mask", "bandeau", "coif", "keffiyeh",
        "kavuk", "mortarboard", "m.board", "bonnet", "chapeau", "chappel", "galea",
        "visor", "hairpin", "hood", "tam", "sallet", "headpiece", "zucchetto", "coronal",
        "horn", "beret", "band", "head",
        "torque", "gorget", "necklace", "pendant", "collar", "amulet", "choker",
        "beads", "locket", "charm", "kubikazari"
    )
    if any(k in nl for k in head_neck_keywords) or "head" in ch:
        return "👑 Head & Neck"

    # 7. Body & Hands
    body_hands_keywords = (
        "coat", "lorica", "breastplate", "mail", "surcoat", "tabard", "jubbah",
        "mintan", "doublet", "gown", "sayon", "kaftan", "jacket", "platemail",
        "harness", "corazza", "robe", "chasuble", "chas.", "jupon", "vest", "tunic",
        "tunica", "apron", "garb", "kalasiris", "shomonjijoe", "cuirie", "cloak", "body",
        "gauntlets", "mufflers", "gloves", "mitts", "mittens", "bracers", "bazubands",
        "gantherots", "mitons", "cuffs", "wrist.", "dastanas", "fin. ga.", "manopolas",
        "bazu.", "babu.", "armlets", "gages", "hands"
    )
    if any(k in nl for k in body_hands_keywords) or "body" in ch:
        return "🧥 Body & Hands"

    # 8. Legs, Feet & Waist
    legs_feet_waist_keywords = (
        "cuisses", "trousers", "subligar", "pants", "slops", "tights", "fuseau",
        "spats", "shalwar", "tayt", "chausses", "cosciales", "lappas", "braconi",
        "seraweels", "sera.", "hose", "guards", "legs",
        "greaves", "calligae", "boots", "bottes", "sollerets", "sabots", "pumps",
        "pigaches", "loafers", "houseaux", "charuqs", "basmak", "leggings", "gambieras",
        "jam.", "clogs", "crackows", "gaiters", "galosh.", "socks", "ocreae", "feet",
        "belt", "sash", "obi", "rope", "yotai", "stone"
    )
    if any(k in nl for k in legs_feet_waist_keywords) or "legs" in ch:
        return "👖 Legs, Feet & Waist"

    # 9. Rings, Earrings & Back (Capes)
    ring_ear_back_keywords = (
        "ring", "band", "earring", "suppanomimi", "cape", "mantle", "shawl"
    )
    if any(k in nl for k in ring_ear_back_keywords) or "ring" in ch:
        return "💍 Rings, Earrings & Back (Capes)"

    return "📦 General, Pop Items & Storage"


def consolidate_inventory_items(raw_inventory: list) -> list:
    """
    Consolidates raw inventory items according to Jason's rules:
    1. Stackables / Currencies / Unaugmented identical items are totaled across
       all bags and characters.
    2. Same-name gear pieces with DIFFERENT augments are NEVER merged together;
       each unique (name, augment) pair remains its own distinct entry.
    3. Detects and flags when the same (name, augment) exists in 2 or more
       bags/characters ("scattered": True, "bag_count": N).
    """
    grouped = {}
    order_keys = []

    for row in raw_inventory:
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        cnt = int(row.get("count", 1) or 1)
        char_name = str(row.get("character", "Main")).strip() or "Main"
        bag_name = str(row.get("bag", "Inventory")).strip() or "Inventory"
        augments = str(row.get("augments", "")).strip()
        cat_hint = str(row.get("category", "")).strip()

        # Grouping key includes normalized name AND normalized augments so
        # same-name gear with different augments stays strictly separated!
        key = (name.lower(), augments.lower())

        if key not in grouped:
            category = classify_ffxi_item(name, cat_hint, augments)
            grouped[key] = {
                "name": name,
                "augments": augments,
                "category": category,
                "total_count": 0,
                "locations": [],       # list of dicts: {"character": ..., "bag": ..., "count": ...}
                "characters_set": set(),
                "bags_set": set(),
            }
            order_keys.append(key)

        entry = grouped[key]
        entry["total_count"] += cnt
        entry["locations"].append({
            "character": char_name,
            "bag": bag_name,
            "count": cnt
        })
        entry["characters_set"].add(char_name)
        entry["bags_set"].add(f"{char_name}:{bag_name}")

    results = []
    for key in order_keys:
        e = grouped[key]
        loc_parts = []
        for loc in e["locations"]:
            if loc["count"] > 1:
                loc_parts.append(f"{loc['character']} • {loc['bag']} ({loc['count']:,})")
            else:
                loc_parts.append(f"{loc['character']} • {loc['bag']}")

        bag_slot_count = len(e["locations"])
        is_scattered = bag_slot_count > 1

        results.append({
            "name": e["name"],
            "augments": e["augments"],
            "category": e["category"],
            "total_count": e["total_count"],
            "bag_count": bag_slot_count,
            "scattered": is_scattered,
            "scattered_badge": f"⚠️ SCATTERED ({bag_slot_count} bags)" if is_scattered else "✅ Single Bag",
            "locations_str": "  |  ".join(loc_parts),
            "characters": sorted(list(e["characters_set"])),
            "bags": [loc["bag"] for loc in e["locations"]],
            "raw_locations": e["locations"]
        })

    return results


# ==============================================================================
# PAGE 6: HOTKEY & CONFLICT SCANNER ENGINE
# ==============================================================================
def normalize_hotkey_string(raw_key: str) -> str:
    """
    Converts Windower keybind strings (e.g. '^f10', '!f10', '@f9', '~f11',
    '%f8', 'Ctrl-F10', 'Alt+F1') into a canonical uppercase format such as:
    'CTRL+F10', 'ALT+F10', 'WIN+F9', 'SHIFT+F11', 'F8', 'F11', 'F12'.
    """
    k = (raw_key or "").strip()
    if not k:
        return ""
    # Strip Windower game-only / chat prefixes (% or $) for conflict comparison
    k_clean = k.lstrip("%$")

    mods = []
    # Check symbolic prefixes (^ = Ctrl, ! = Alt, @ = Win, ~ = Shift)
    while k_clean and k_clean[0] in "^!@~":
        ch = k_clean[0]
        if ch == "^" and "CTRL" not in mods:
            mods.append("CTRL")
        elif ch == "!" and "ALT" not in mods:
            mods.append("ALT")
        elif ch == "@" and "WIN" not in mods:
            mods.append("WIN")
        elif ch == "~" and "SHIFT" not in mods:
            mods.append("SHIFT")
        k_clean = k_clean[1:]

    # Also handle explicit word prefixes like Ctrl-F10 or Alt+F10
    parts = re.split(r"[-+]", k_clean)
    base_key = parts[-1].upper() if parts else k_clean.upper()
    for p in parts[:-1]:
        pu = p.strip().upper()
        if pu in ("CTRL", "CONTROL") and "CTRL" not in mods:
            mods.append("CTRL")
        elif pu == "ALT" and "ALT" not in mods:
            mods.append("ALT")
        elif pu in ("SHIFT", "SHFT") and "SHIFT" not in mods:
            mods.append("SHIFT")
        elif pu in ("WIN", "WINDOWS", "SUPER") and "WIN" not in mods:
            mods.append("WIN")

    alias_map = {
        "SYSRQ": "PRINTSCREEN",
        "PRINT": "PRINTSCREEN",
        "PRTSC": "PRINTSCREEN",
        "INS": "INSERT",
        "DEL": "DELETE",
        "ESC": "ESCAPE",
    }
    base_key = alias_map.get(base_key, base_key)

    ordered_mods = [m for m in ("CTRL", "ALT", "SHIFT", "WIN") if m in mods]
    if ordered_mods:
        return "+".join(ordered_mods + [base_key])
    return base_key


def to_windower_bind_key(norm_key: str) -> str:
    """Converts canonical 'CTRL+F10' back to Windower bind syntax '^f10'."""
    parts = [p.strip().upper() for p in norm_key.split("+") if p.strip()]
    if not parts:
        return ""
    base = parts[-1].lower()
    prefix = ""
    if "CTRL" in parts[:-1]:
        prefix += "^"
    if "ALT" in parts[:-1]:
        prefix += "!"
    if "WIN" in parts[:-1]:
        prefix += "@"
    if "SHIFT" in parts[:-1]:
        prefix += "~"
    return prefix + base


def scan_all_hotkeys_and_conflicts(windower_dir: str) -> list:
    """
    Scans and aggregates hotkeys across all 4 FFXI / Windower layers:
    1. FFXI Base Game Default Hotkeys
    2. Windower scripts/init.txt
    3. GearSwap Lua files (Mote-Include & job .lua files)
    4. Windower Addons & Plugins (settings.xml, binder.xml, etc.)
    """
    entries = []
    init_path = os.path.join(windower_dir, "scripts", "init.txt")
    settings_path = os.path.join(windower_dir, "settings.xml")
    gs_data_dir = os.path.join(windower_dir, "addons", "GearSwap", "data")
    gs_libs_dir = os.path.join(windower_dir, "addons", "GearSwap", "libs")

    # 1. FFXI Base Game Hotkeys (focusing on F1-F12 & common Ctrl/Alt binds)
    base_game_binds = [
        ("F1", "Target Party Member 1 (Self)", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client key. Overridden if bound without '%' in Windower."),
        ("F2", "Target Party Member 2", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F3", "Target Party Member 3", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F4", "Target Party Member 4", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F5", "Target Party Member 5", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F6", "Target Party Member 6", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F7", "Target Self", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client self-target key."),
        ("F8", "Target Nearest NPC / Monster", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "If your GearSwap Lua binds F8, Windower intercepts F8 before FFXI's Target Nearest NPC unless unbound or rebound."),
        ("F9", "Target Nearest PC (Player)", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Standard Mote GearSwap binds F9 to cycle OffenseMode, overriding FFXI's Target Nearest PC."),
        ("F10", "Target Alliance / Window Shortcut", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Used by GearSwap (PhysicalDefenseMode / Custom Job Binds). Removed from Vana'diel Nexus!"),
        ("CTRL+1..0", "Macro Palette Bar (Ctrl Row)", "FFXI Base Game", "In-Game Macro Bar (DelayMeNot plugin active)", "Opens & triggers Ctrl Macro slots 1 through 0."),
        ("ALT+1..0", "Macro Palette Bar (Alt Row)", "FFXI Base Game", "In-Game Macro Bar (DelayMeNot plugin active)", "Opens & triggers Alt Macro slots 1 through 0."),
    ]
    for k, act, sys_type, cfg_loc, fix_guide in base_game_binds:
        entries.append({
            "raw_key": k,
            "norm_key": normalize_hotkey_string(k),
            "system": sys_type,
            "source_file": cfg_loc,
            "line_num": 0,
            "action": act,
            "how_to_fix": fix_guide,
            "editable_file": False
        })

    # 2. Windower scripts/init.txt (Read live file if present, otherwise use Jason's known init.txt binds)
    init_entries_loaded = False
    if os.path.isfile(init_path):
        try:
            with open(init_path, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f, start=1):
                    s = line.strip()
                    if not s or s.startswith("//") or s.startswith(";"):
                        continue
                    m = re.match(r"^bind\s+(\S+)\s+(.+)$", s, re.IGNORECASE)
                    if m:
                        rk, cmd = m.group(1), m.group(2).strip()
                        nk = normalize_hotkey_string(rk)
                        entries.append({
                            "raw_key": rk,
                            "norm_key": nk,
                            "system": "Windower init.txt",
                            "source_file": init_path,
                            "line_num": idx,
                            "action": cmd,
                            "how_to_fix": (
                                f"Edit {init_path} (Line {idx}) to change or comment out 'bind {rk} {cmd}', "
                                f"then type '//unbind {rk}' in the Windower console."
                            ),
                            "editable_file": True
                        })
                        init_entries_loaded = True
        except Exception:
            pass

    if not init_entries_loaded:
        # Fallback to Jason's documented Windower4/scripts/init.txt binds
        known_init_binds = [
            ("F11", "game_forceambientlight", 12, "Toggles ambient light. CONFLICTS with GearSwap F11 (CastingMode / Custom Lua binds)! Remove or move to e.g. Ctrl+F11/Numpad in scripts/init.txt."),
            ("F12", "showfps", 13, "Toggles FPS counter. CONFLICTS with GearSwap F12 (Update Gear / Show State)! Comment out 'bind F12 showfps' in scripts/init.txt and type //unbind f12."),
            ("!f10", "drawdistance set 10", 14, "Sets drawdistance 10. CONFLICTS with GearSwap Alt+F10! Also 'drawdistance' is unverified (use '//config ClippingPlane 10'). Comment out in scripts/init.txt."),
            ("^f10", "drawdistance set 1", 15, "Sets drawdistance 1. CONFLICTS with GearSwap Ctrl+F10! Comment out 'bind ^f10 drawdistance set 1' in scripts/init.txt and type //unbind ^f10."),
            ("^v", "paste", 16, "Pastes clipboard text into FFXI chat line."),
            ("sysrq", "screenshot png hide", 17, "Saves clean PNG screenshot without Windower overlays."),
            ("^f1", "input /ta <a10>", 18, "Targets Alliance Party 2 Member 1."),
            ("^f2", "input /ta <a11>", 19, "Targets Alliance Party 2 Member 2."),
            ("^f3", "input /ta <a12>", 20, "Targets Alliance Party 2 Member 3."),
            ("^f4", "input /ta <a13>", 21, "Targets Alliance Party 2 Member 4."),
            ("^f5", "input /ta <a14>", 22, "Targets Alliance Party 2 Member 5."),
            ("^f6", "input /ta <a15>", 23, "Targets Alliance Party 2 Member 6."),
            ("!f1", "input /ta <a20>", 24, "Targets Alliance Party 3 Member 1."),
            ("!f2", "input /ta <a21>", 25, "Targets Alliance Party 3 Member 2."),
            ("!f3", "input /ta <a22>", 26, "Targets Alliance Party 3 Member 3."),
            ("!f4", "input /ta <a23>", 27, "Targets Alliance Party 3 Member 4."),
            ("!f5", "input /ta <a24>", 28, "Targets Alliance Party 3 Member 5."),
            ("!f6", "input /ta <a25>", 29, "Targets Alliance Party 3 Member 6."),
        ]
        for rk, cmd, lno, guide in known_init_binds:
            entries.append({
                "raw_key": rk,
                "norm_key": normalize_hotkey_string(rk),
                "system": "Windower init.txt",
                "source_file": init_path,
                "line_num": lno,
                "action": cmd,
                "how_to_fix": f"{guide} (File: {init_path}, Line {lno} | In-game: //unbind {rk})",
                "editable_file": os.path.isfile(init_path)
            })

    # 3. GearSwap Lua Hotkeys (Scan GearSwap/data & libs if present + Mote-Include F8-F12 defaults)
    gs_binds_found = False
    lua_search_paths = []
    if os.path.isdir(gs_data_dir):
        for root_d, _dirs, files in os.walk(gs_data_dir):
            for fn in files:
                if fn.lower().endswith(".lua"):
                    lua_search_paths.append(os.path.join(root_d, fn))
    if os.path.isdir(gs_libs_dir):
        for fn in os.listdir(gs_libs_dir):
            if fn.lower().endswith(".lua"):
                lua_search_paths.append(os.path.join(gs_libs_dir, fn))

    bind_regex = re.compile(r"bind\s+([~!@^%$a-zA-Z0-9_-]+)\s+([^'\"\r\n]+)", re.IGNORECASE)
    for lpath in lua_search_paths[:60]:
        try:
            with open(lpath, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f, start=1):
                    s = line.strip()
                    if s.startswith("--"):
                        continue
                    for m in bind_regex.finditer(s):
                        rk = m.group(1).strip()
                        cmd = m.group(2).strip()
                        nk = normalize_hotkey_string(rk)
                        entries.append({
                            "raw_key": rk,
                            "norm_key": nk,
                            "system": f"GearSwap Lua ({os.path.basename(lpath)})",
                            "source_file": lpath,
                            "line_num": idx,
                            "action": cmd,
                            "how_to_fix": (
                                f"Defined in {lpath} (Line {idx}). Edit 'send_command(\"bind {rk} ...\")' in that .lua file, "
                                f"then run '//gs r' in game."
                            ),
                            "editable_file": True
                        })
                        gs_binds_found = True
        except Exception:
            pass

    if not gs_binds_found:
        # Standard Mote-Include & User Job Lua F8-F12 binds
        mote_lua_binds = [
            ("f8", "gs c cycle WeaponSet / Custom Job Mode", "GearSwap Lua (Job .lua / user-globals.lua)", os.path.join(gs_data_dir, "user-globals.lua"), "Used by your job .lua files for WeaponSet / custom toggles. Keep unbound in init.txt!"),
            ("^f8", "gs c cycleback WeaponSet / Custom Mode", "GearSwap Lua (Job .lua)", os.path.join(gs_data_dir, "user-globals.lua"), "Used by your job .lua files with Ctrl+F8."),
            ("!f8", "gs c toggle Custom Mode (Alt+F8)", "GearSwap Lua (Job .lua)", os.path.join(gs_data_dir, "user-globals.lua"), "Used by your job .lua files with Alt+F8."),
            ("f9", "gs c cycle OffenseMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Cycles Melee/Offense accuracy modes (Normal -> Acc -> PDL)."),
            ("^f9", "gs c cycle HybridMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Cycles Hybrid DT modes (Normal -> DT -50%)."),
            ("!f9", "gs c cycle RangedMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Cycles RangedMode in Mote GearSwap."),
            ("@f9", "gs c cycle WeaponskillMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Cycles WeaponskillMode (Normal -> Acc -> PDL Cap)."),
            ("f10", "gs c set DefenseMode Physical", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Activates Physical Defense lock in Mote GearSwap. (Removed F10 from Vana'diel Nexus so this never conflicts!)"),
            ("^f10", "gs c cycle PhysicalDefenseMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Cycles PhysicalDefenseMode in GearSwap. CONFLICTS with init.txt 'bind ^f10 drawdistance set 1'!"),
            ("!f10", "gs c toggle Kiting", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Toggles Movement Speed / Kiting gear lock. CONFLICTS with init.txt 'bind !f10 drawdistance set 10'!"),
            ("f11", "gs c set DefenseMode Magical / CastingMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Activates Magical Defense or cycles CastingMode. CONFLICTS with init.txt 'bind F11 game_forceambientlight'!"),
            ("^f11", "gs c cycle CastingMode / IdleMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Cycles CastingMode (Normal -> Resistant -> Burst) in caster/BLU/SMN/SCH/RDM luas."),
            ("!f11", "gs c cycle MagicalDefenseMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Cycles MagicalDefenseMode in Mote GearSwap."),
            ("f12", "gs c update user (Refresh Gear & Show State)", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Forces GearSwap to re-equip current set & print active modes. CONFLICTS with init.txt 'bind F12 showfps'!"),
            ("^f12", "gs c cycle IdleMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Cycles IdleMode (Normal -> DT -> Refresh)."),
            ("!f12", "gs c reset DefenseMode", "GearSwap Lua (Mote-Globals.lua)", os.path.join(gs_libs_dir, "Mote-Globals.lua"), "Unlocks Physical/Magical DefenseMode so normal swaps resume."),
        ]
        for rk, cmd, sys_lbl, fpath, guide in mote_lua_binds:
            entries.append({
                "raw_key": rk,
                "norm_key": normalize_hotkey_string(rk),
                "system": sys_lbl,
                "source_file": fpath,
                "line_num": 1,
                "action": cmd,
                "how_to_fix": f"{guide} (Edit in {fpath} or user_setup() / job_setup() in your job .lua file.)",
                "editable_file": os.path.isfile(fpath)
            })

    # 4. Windower Console & Plugin Hotkeys
    entries.append({
        "raw_key": "Insert",
        "norm_key": "INSERT",
        "system": "Windower Core (settings.xml)",
        "source_file": settings_path,
        "line_num": 44,
        "action": "Toggle Windower Console (<consolekey>Insert</consolekey>)",
        "how_to_fix": f"Configured in {settings_path} under <consolekey>Insert</consolekey>. Close FFXI before editing settings.xml.",
        "editable_file": os.path.isfile(settings_path)
    })

    # Compute conflicts by normalized key
    by_norm = {}
    for e in entries:
        nk = e["norm_key"]
        by_norm.setdefault(nk, []).append(e)

    for e in entries:
        nk = e["norm_key"]
        group = by_norm.get(nk, [])
        distinct_systems = {g["system"] for g in group}
        if len(group) > 1 and len(distinct_systems) > 1:
            others = [f"{g['system']} -> '{g['action']}'" for g in group if g is not e]
            e["conflict"] = True
            e["conflict_count"] = len(group)
            e["status_label"] = f"⚠️ CONFLICT ({len(group)} systems)"
            e["conflict_summary"] = "  ||  ".join(others)
        else:
            e["conflict"] = False
            e["conflict_count"] = 1
            e["status_label"] = "✅ OK (No Conflict)"
            e["conflict_summary"] = "None"

    # Sort so conflicts appear at the top, then F1-F12 order
    def _sort_key(item):
        c_rank = 0 if item["conflict"] else 1
        return (c_rank, item["norm_key"], item["system"])

    entries.sort(key=_sort_key)
    return entries


# ==============================================================================
# BOOTSTRAP & DATABASE PERSISTENCE
# ==============================================================================
def ensure_directories_and_assets():
    for d in (DATA_DIR, MODULES_DIR, HOOK_DIR, ADDON_BACKUP_DIR):
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_DATABASE, f, indent=2, ensure_ascii=False)
    else:
        # Ensure new jobs (BLU, SMN, RUN, SCH, RDM) exist in jse_by_job if upgrading from v1.0 DB
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                cur_db = json.load(f)
            changed = False
            jse_map = cur_db.setdefault("jse_by_job", {})
            for job_k, job_rows in DEFAULT_DATABASE["jse_by_job"].items():
                if job_k not in jse_map:
                    jse_map[job_k] = job_rows
                    changed = True
            for cp in cur_db.get("checkpoints", []):
                if "job" not in cp:
                    m = re.search(r"\(([A-Z]{3})\)", cp.get("category", ""))
                    cp["job"] = m.group(1) if m else "All"
                    changed = True
            for wl in cur_db.get("wishlist", []):
                if "job" not in wl:
                    m = re.search(r"\b(WAR|MNK|WHM|BLM|RDM|THF|PLD|DRK|BST|BRD|RNG|SAM|NIN|DRG|SMN|BLU|COR|PUP|DNC|SCH|GEO|RUN)\b", wl.get("slot", ""))
                    wl["job"] = m.group(1) if m else "All"
                    changed = True
            if changed:
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(cur_db, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    hook_path = os.path.join(HOOK_DIR, "Mote_Nexus_Hook.lua")
    if not os.path.exists(hook_path):
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(MOTE_HOOK_LUA_CODE)

    _write_if_changed(os.path.join(ADDON_BACKUP_DIR, "VanadielNexus.lua"), VANADIEL_NEXUS_LUA_CODE)

    # Ship addon updates with the app: keep <Windower4>\addons\VanadielNexus\VanadielNexus.lua in sync
    if os.path.isdir(DEFAULT_WINDOWER_DIR):
        try:
            os.makedirs(DEFAULT_ADDON_DIR, exist_ok=True)
            _write_if_changed(os.path.join(DEFAULT_ADDON_DIR, "VanadielNexus.lua"), VANADIEL_NEXUS_LUA_CODE)
        except Exception as e:
            print(f"[Warn] Could not update Windower addon: {e}")

    example_mod = os.path.join(MODULES_DIR, "sortie_helper.py")
    if not os.path.exists(example_mod):
        with open(example_mod, "w", encoding="utf-8") as f:
            f.write(EXAMPLE_MODULE_PY_CODE)


def load_database():
    ensure_directories_and_assets()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Warn] Could not parse {DB_FILE}: {e}")
    try:
        with open(DB_FILE + ".bak", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(DEFAULT_DATABASE)


def save_database(db_data):
    """Crash-safe save: write a temp file, keep the previous DB as .bak, then swap in."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_path = DB_FILE + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=2, ensure_ascii=False)
        if os.path.exists(DB_FILE):
            shutil.copy2(DB_FILE, DB_FILE + ".bak")
        os.replace(tmp_path, DB_FILE)
    except Exception as e:
        print(f"[Warn] Could not save {DB_FILE}: {e}")


def _write_if_changed(path: str, content: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            if f.read() == content:
                return
    except Exception:
        pass
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


# ==============================================================================
# MODULAR PLUGIN LOADER (`modules/*.py`)
# ==============================================================================
def discover_custom_modules():
    discovered = []
    if not os.path.isdir(MODULES_DIR):
        return discovered
    for py_path in sorted(glob.glob(os.path.join(MODULES_DIR, "*.py"))):
        try:
            mod_name = os.path.splitext(os.path.basename(py_path))[0]
            spec = importlib.util.spec_from_file_location(mod_name, py_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                meta = getattr(mod, "MODULE_METADATA", None)
                if isinstance(meta, dict):
                    meta_copy = dict(meta)
                    meta_copy["_module_ref"] = mod
                    meta_copy["_file"] = os.path.basename(py_path)
                    discovered.append(meta_copy)
        except Exception as e:
            print(f"[Warn] Failed loading module {py_path}: {e}")
    return discovered


# ==============================================================================
# CORE APPLICATION CONTROLLER & UDP BRIDGE
# ==============================================================================
class NexusBridgeState:
    def __init__(self):
        self.db = load_database()
        self.custom_modules = discover_custom_modules()
        self.udp_connected = False
        self.last_packet_time = 0.0
        self.no_activate_enabled = False
        self.compact_hud_mode = False
        self.hud_toggle_requested = False
        self.windower_path = DEFAULT_WINDOWER_DIR if os.path.isdir(DEFAULT_WINDOWER_DIR) else BASE_DIR

        # Live runtime state (updated by VanadielNexus.lua over UDP 5017)
        self.live = {
            "player_name": "Someonesmall",
            "main_job": "BLU",
            "main_job_lvl": 99,
            "sub_job": "WAR",
            "sub_job_lvl": 49,
            "master_lvl": 42,
            "zone_name": "Odyssey - Sheol Gaol",
            "attack": 2190,
            "defense": 1640,
            "accuracy_est": 1482,
            "magic_haste": 43.75,
            "gear_haste": 25.0,
            "dw_needed": 0,
            "haste_group": "MaxHaste",
            "mote_modes": {
                "OffenseMode": "Normal",
                "HybridMode": "DT (-50%)",
                "WeaponskillMode": "PDL Cap",
                "IdleMode": "DT",
                "WeaponSet": "Tizona"
            },
            "materials": {
                "Alexandrite": 1240,
                "Pluton": 1450,
                "Beitetsu": 3120,
                "Riftborn Boulder": 890,
                "Heavy Metal Plate": 410
            },
            "equipped": [
                {"slot": "main", "name": "Tizona", "augments": "R15 Afterglow (Expiacion +30%)"},
                {"slot": "sub", "name": "Colada", "augments": "Crit.hit rate+2, DEX+4, Acc+20, Atk+6, DMG:+12"},
                {"slot": "head", "name": "Assimilator's Keffiyeh +2", "augments": ""},
                {"slot": "body", "name": "Assimilator's Jubbah +3", "augments": ""},
                {"slot": "hands", "name": "Assimilator's Bazubands +3", "augments": ""},
                {"slot": "legs", "name": "Luhlaza Shalwar +2", "augments": "Enhances Assimilation effect"},
                {"slot": "back", "name": "Rosmerta's Cape", "augments": "DEX+20, Acc+20 Atk+20, DEX+10, Crit.hit rate+10, Regen+5"}
            ],
            "inventory": [
                # Stackable currencies & materials (demonstrates multi-bag rollup & scattered detection)
                {"name": "Alexandrite", "count": 1240, "character": "Someonesmall", "bag": "Mog Case", "augments": ""},
                {"name": "Alexandrite", "count": 380, "character": "Someonesmall", "bag": "Mog Satchel", "augments": ""},
                {"name": "Beitetsu", "count": 3120, "character": "Someonesmall", "bag": "Mog Case", "augments": ""},
                {"name": "Pluton", "count": 1450, "character": "Someonesmall", "bag": "Mog Case", "augments": ""},
                {"name": "Riftborn Boulder", "count": 890, "character": "Someonesmall", "bag": "Mog Sack", "augments": ""},
                {"name": "P. WAR Card", "count": 35, "character": "Someonesmall", "bag": "Mog Satchel", "augments": ""},
                {"name": "P. WAR Card", "count": 14, "character": "AltMuleA", "bag": "Mog Safe 1", "augments": ""},
                # Weapons & Grips
                {"name": "Tizona", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "R15 Afterglow"},
                {"name": "Nirvana", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "R15 Afterglow"},
                {"name": "Epeolatry", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "R15 Afterglow"},
                {"name": "Lionheart", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "R15 Ultimate SC"},
                {"name": "Naegling", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Colada", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "'Store TP'+4, Accuracy+5, Attack+9, DMG:+12"},
                {"name": "Colada", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 2", "augments": "Crit.hit rate+2, Accuracy+19, Attack+15, DMG:+17"},
                {"name": "Utu Grip", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Elan Strap +1", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Ammurapi Shield", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                # Same-name gear with DIFFERENT augments (kept strictly separate!)
                {"name": "Campestres's Cape", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "Pet: Acc.+20 R.Acc.+20 Atk.+20, Pet: Haste+10, Pet: Regen+5"},
                {"name": "Campestres's Cape", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 2", "augments": "Pet: M.Acc.+20 M.Dmg.+20, Fast Cast+10, Pet: Regen+5"},
                {"name": "Rosmerta's Cape", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "DEX+20, Acc+20 Atk+20, DEX+10, Crit.hit rate+10, Regen+5"},
                {"name": "Rosmerta's Cape", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 2", "augments": "INT+20, Mag.Acc+20 /Mag.Dmg.+20, Fast Cast+10, SIRD-10%"},
                {"name": "Ogma's Cape", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "HP+60, Eva.+20 /Mag.Eva.+20, Enmity+10, Damage taken-5%"},
                {"name": "Ogma's Cape", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 2", "augments": "DEX+20, Acc+20 Atk+20, DEX+10, Weapon skill damage +10%, DT-5%"},
                {"name": "Herculean Boots", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 3", "augments": "Attack+18, 'Triple Atk.'+3, Accuracy+5 (TA Set)"},
                {"name": "Herculean Boots", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 4", "augments": "Accuracy+4, Crit. hit damage +5%, AGI+8, Attack+11"},
                {"name": "Herculean Boots", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 4", "augments": "Weapon skill damage +5%, STR+10, Accuracy+6"},
                # Scattered identical unaugmented rings across bags (flagged as SCATTERED)
                {"name": "Stikini Ring +1", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Stikini Ring +1", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 2", "augments": ""},
                {"name": "Varar Ring +1", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Varar Ring +1", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 3", "augments": ""},
                # Armor & Accessories
                {"name": "Convoker's Horn +3", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Convoker's Doublet +3", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Glyphic Bracers +3", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "Inc. Sp. Blood Pact magic burst dmg."},
                {"name": "Assimilator's Jubbah +3", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Runeist's Coat +3", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Futhark Coat +3", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 2", "augments": "Enhances Elemental Sforzo effect"},
                {"name": "Adhemar Bonnet +1", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "STR+12, DEX+12, Attack+20 (Path B)"},
                {"name": "Adhemar Jacket +1", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "STR+12, DEX+12, Attack+20 (Path B)"},
                {"name": "Carmine Cuisses +1", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": "Accuracy+20, Attack+12, 'Dual Wield'+6 (Path D)"},
                {"name": "Defending Ring", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Moonlight Ring", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Fotia Gorget", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Fotia Belt", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                {"name": "Staunch Tathlum +1", "count": 1, "character": "Someonesmall", "bag": "Wardrobe 1", "augments": ""},
                # Consumables
                {"name": "Grape Daifuku", "count": 12, "character": "Someonesmall", "bag": "Inventory", "augments": ""},
                {"name": "Grape Daifuku", "count": 24, "character": "Someonesmall", "bag": "Mog Satchel", "augments": ""},
                {"name": "Sublime Sushi +1", "count": 12, "character": "Someonesmall", "bag": "Mog Satchel", "augments": ""},
                {"name": "Remedy", "count": 12, "character": "Someonesmall", "bag": "Inventory", "augments": ""},
                {"name": "Echo Drops", "count": 12, "character": "Someonesmall", "bag": "Inventory", "augments": ""},
                {"name": "Holy Water", "count": 12, "character": "Someonesmall", "bag": "Inventory", "augments": ""}
            ],
            "treasure_pool": [
                {"slot": 0, "name": "Old Case +1", "lot": 0},
                {"slot": 1, "name": "P. BLU Card", "lot": 892}
            ],
            "missing_gs_items": []
        }

        self.sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ui_dirty = True

    def send_udp_command(self, raw_cmd: str):
        """Send a pipe-delimited command string to VanadielNexus.lua on UDP 5018."""
        try:
            self.sock_out.sendto(raw_cmd.encode("utf-8"), (UDP_HOST, UDP_SEND_PORT))
        except Exception as e:
            print(f"[UDP Send Error] {e}")

    def update_from_lua_payload(self, payload: dict):
        st = payload.get("state", {})
        if not isinstance(st, dict):
            return
        self.udp_connected = True
        self.last_packet_time = time.time()

        for key in (
            "player_name", "main_job", "main_job_lvl", "sub_job", "sub_job_lvl",
            "master_lvl", "zone_name", "attack", "defense", "magic_haste",
            "gear_haste", "dw_needed", "haste_group"
        ):
            if key in st and st[key] is not None:
                self.live[key] = st[key]

        if isinstance(st.get("mote_modes"), dict):
            self.live["mote_modes"].update(st["mote_modes"])
        if isinstance(st.get("materials"), dict):
            self.live["materials"].update(st["materials"])
        if isinstance(st.get("equipped"), list) and st["equipped"]:
            self.live["equipped"] = st["equipped"]
        if isinstance(st.get("inventory"), list) and st["inventory"]:
            self.live["inventory"] = st["inventory"]
        if isinstance(st.get("treasure_pool"), list):
            self.live["treasure_pool"] = st["treasure_pool"]

        self.ui_dirty = True


# ==============================================================================
# WIN32 FOCUS PROTECTION HELPER (WS_EX_NOACTIVATE)
# ==============================================================================
def set_window_noactivate(hwnd: int, enable: bool):
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOPMOST = 0x00000008
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enable:
            new_style = style | WS_EX_NOACTIVATE | WS_EX_TOPMOST
        else:
            new_style = style & ~WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        return True
    except Exception as e:
        print(f"[Win32 Style Info] {e}")
        return False


# ==============================================================================
# NATIVE DESKTOP & COMPACT HUD OVERLAY GUI (TKINTER / TTK)
# ==============================================================================
class VanadielNexusDesktopApp:
    def __init__(self, root, bridge: NexusBridgeState):
        self.root = root
        self.bridge = bridge
        self.root.title(f"Vana'diel Nexus v{APP_VERSION} — FFXI Windower 4 Overlay & Game Assistant")
        self.root.geometry("1180x780+60+40")
        self.root.minsize(860, 560)
        self.root.configure(bg="#080c14")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.96)

        self._drag_x = 0
        self._drag_y = 0

        # Track visible row index -> underlying DB index for filtered tables
        self._cp_index_map = {}
        self._jse_index_map = {}
        self._rema_index_map = {}
        self._wl_index_map = {}
        self._inv_item_map = {}
        self._hotkey_entries = []

        self._setup_styles()
        self._build_top_bar()
        self._build_main_views()
        self._build_shared_context_menu()
        self._schedule_refresh()
        if IS_FROZEN:
            self.root.after(3000, self._check_for_updates)

    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        bg_dark = "#080c14"
        bg_panel = "#0f172a"
        bg_card = "#1e293b"
        fg_main = "#e2e8f0"
        fg_cyan = "#38bdf8"
        fg_gold = "#fbbf24"

        style.configure(".", background=bg_panel, foreground=fg_main, font=("Segoe UI", 9))
        style.configure("TFrame", background=bg_panel)
        style.configure("Dark.TFrame", background=bg_dark)
        style.configure("Card.TFrame", background=bg_card)
        style.configure("TLabel", background=bg_panel, foreground=fg_main)
        style.configure("Card.TLabel", background=bg_card, foreground=fg_main)
        style.configure("Header.TLabel", background=bg_panel, foreground="#ffffff", font=("Segoe UI", 11, "bold"))
        style.configure("Gold.TLabel", background=bg_card, foreground=fg_gold, font=("Consolas", 9, "bold"))
        style.configure("Cyan.TLabel", background=bg_card, foreground=fg_cyan, font=("Consolas", 9, "bold"))

        style.configure("TNotebook", background=bg_dark, borderwidth=0)
        style.configure("TNotebook.Tab", background=bg_card, foreground="#94a3b8", padding=(10, 6), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", "#0284c7")],
                  foreground=[("selected", "#ffffff")])

        style.configure("Treeview",
                        background="#0f172a",
                        foreground="#e2e8f0",
                        fieldbackground="#0f172a",
                        rowheight=25,
                        borderwidth=0,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
                        background="#1e293b",
                        foreground="#38bdf8",
                        font=("Consolas", 9, "bold"))
        style.map("Treeview", background=[("selected", "#0369a1")])

    def _build_top_bar(self):
        self.top_bar = tk.Frame(self.root, bg="#0f172a", highlightbackground="#0284c7", highlightthickness=1, padx=10, pady=6)
        self.top_bar.pack(fill=tk.X, side=tk.TOP)

        self.top_bar.bind("<ButtonPress-1>", self._start_move)
        self.top_bar.bind("<B1-Motion>", self._on_move)

        left = tk.Frame(self.top_bar, bg="#0f172a")
        left.pack(side=tk.LEFT)

        badge = tk.Label(left, text=" VN ", bg="#0284c7", fg="#ffffff", font=("Consolas", 10, "bold"), padx=4, pady=2)
        badge.pack(side=tk.LEFT, padx=(0, 8))

        title_box = tk.Frame(left, bg="#0f172a")
        title_box.pack(side=tk.LEFT)
        tk.Label(title_box, text=f"Vana'diel Nexus v{APP_VERSION} (F8–F12 Safe)", bg="#0f172a", fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.lbl_bridge_status = tk.Label(
            title_box,
            text="● Windower 4 UDP Bridge: Listening on 127.0.0.1:5017 | Job: BLU/WAR",
            bg="#0f172a", fg="#34d399", font=("Consolas", 8)
        )
        self.lbl_bridge_status.pack(anchor="w")

        # Double-clicking the top bar toggles compact HUD mode; F10 is intentionally NOT bound!
        self.top_bar.bind("<Double-Button-1>", lambda _e: self.toggle_hud_mode())

        right = tk.Frame(self.top_bar, bg="#0f172a")
        right.pack(side=tk.RIGHT)

        self.toolbar_extra = tk.Frame(right, bg="#0f172a")
        self.toolbar_extra.pack(side=tk.LEFT)

        tk.Label(self.toolbar_extra, text="Active Job:", bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(4, 2))
        self.job_var = tk.StringVar(value=self.bridge.live["main_job"])
        self.job_combo = ttk.Combobox(
            self.toolbar_extra,
            textvariable=self.job_var,
            values=[j for j in ALL_FFXI_JOBS if j != "All"],
            width=6,
            state="readonly"
        )
        self.job_combo.pack(side=tk.LEFT, padx=4)
        self.job_combo.bind("<<ComboboxSelected>>", self._on_job_change)

        tk.Label(self.toolbar_extra, text="Opacity:", bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(8, 2))
        self.alpha_scale = tk.Scale(
            self.toolbar_extra, from_=55, to=100, orient=tk.HORIZONTAL, bg="#0f172a", fg="#38bdf8",
            highlightthickness=0, bd=0, sliderlength=12, length=65, showvalue=False,
            command=self._on_alpha_change
        )
        self.alpha_scale.set(96)
        self.alpha_scale.pack(side=tk.LEFT, padx=4)

        # Players running the .exe get "Check for Updates"; the dev build button only makes sense from source
        tk.Button(
            self.toolbar_extra,
            text="⟳ Check for Updates" if IS_FROZEN else "🛠 Build .EXE",
            bg="#0369a1", fg="#ffffff",
            activebackground="#0284c7", activeforeground="#ffffff",
            relief=tk.FLAT, padx=8, pady=3, font=("Segoe UI", 8, "bold"),
            command=(lambda: self._check_for_updates(manual=True)) if IS_FROZEN else self._build_standalone_exe
        ).pack(side=tk.LEFT, padx=4)

        self.btn_noactivate = tk.Button(
            right, text="🔓 Focus: Normal", bg="#1e293b", fg="#cbd5e1",
            activebackground="#334155", activeforeground="#ffffff",
            relief=tk.FLAT, padx=8, pady=3, font=("Segoe UI", 8, "bold"),
            command=self._toggle_noactivate
        )
        self.btn_noactivate.pack(side=tk.LEFT, padx=4)

        self.btn_hud_mode = tk.Button(
            right, text="▣ Compact In-Game HUD", bg="#d97706", fg="#ffffff",
            activebackground="#f59e0b", activeforeground="#000000",
            relief=tk.FLAT, padx=10, pady=3, font=("Segoe UI", 8, "bold"),
            command=self.toggle_hud_mode
        )
        self.btn_hud_mode.pack(side=tk.LEFT, padx=4)

    def _build_main_views(self):
        self.full_frame = ttk.Frame(self.root, style="Dark.TFrame")
        self.full_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self.notebook = ttk.Notebook(self.full_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.tab3 = ttk.Frame(self.notebook)
        self.tab4 = ttk.Frame(self.notebook)
        self.tab5 = ttk.Frame(self.notebook)
        self.tab6 = ttk.Frame(self.notebook)

        self.notebook.add(self.tab1, text=" ⚔️ 1. JSE & REMA Tracker ")
        self.notebook.add(self.tab2, text=" 🧭 2. Wishlist & How to Obtain ")
        self.notebook.add(self.tab3, text=" 📊 3. Live Stats & Mote GearSwap ")
        self.notebook.add(self.tab4, text=" 🎒 4. Inventory & Multi-Bag Browser ")
        self.notebook.add(self.tab5, text=" ⚙️ 5. Addon & Plugin Hub ")
        self.notebook.add(self.tab6, text=" ⌨️ 6. Hotkey & Conflict Manager ")

        self._build_tab1_progression()
        self._build_tab2_wishlist()
        self._build_tab3_stats_mote()
        self._build_tab4_utilities()
        self._build_tab5_addons()
        self._build_tab6_hotkeys()

        self.hud_frame = tk.Frame(self.root, bg="#080c14", padx=8, pady=6)
        self._build_compact_hud_frame()

        self.status_bar = tk.Label(
            self.root,
            text="Ready. Click any gear piece & use the Wiki buttons (or Right-Click) to open BG-Wiki, FFXIAH, or FFXIclopedia.",
            bg="#0f172a", fg="#38bdf8", anchor="w", padx=10, pady=4, font=("Consolas", 8)
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # --------------------------------------------------------------------------
    # SHARED RIGHT-CLICK CONTEXT MENU FOR ALL GEAR / ITEM TABLES
    # --------------------------------------------------------------------------
    def _build_shared_context_menu(self):
        self.ctx_menu = tk.Menu(self.root, tearoff=0, bg="#1e293b", fg="#e2e8f0", activebackground="#0284c7", activeforeground="#ffffff")
        self._ctx_target_item_name = ""
        self._ctx_target_wiki_url = ""
        self._ctx_remove_callback = None
        self._ctx_track_callback = None

        self.ctx_menu.add_command(label="↗ Open in BG-Wiki", command=lambda: open_item_wiki(self._ctx_target_item_name, "bgwiki", self._ctx_target_wiki_url))
        self.ctx_menu.add_command(label="↗ Open in FFXIAH", command=lambda: open_item_wiki(self._ctx_target_item_name, "ffxiah"))
        self.ctx_menu.add_command(label="↗ Open in FFXIclopedia", command=lambda: open_item_wiki(self._ctx_target_item_name, "ffxiclopedia"))
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="📋 Copy Item Name", command=self._copy_ctx_item_name)
        self.ctx_menu.add_command(label="📌 Track / Assign Job on Page 1...", command=self._run_ctx_track)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="🗑 Remove Selected (Confirm)...", command=self._run_ctx_remove)

    def _copy_ctx_item_name(self):
        if self._ctx_target_item_name:
            self.root.clipboard_clear()
            self.root.clipboard_append(self._ctx_target_item_name)
            self._set_status(f"Copied '{self._ctx_target_item_name}' to clipboard.")

    def _run_ctx_track(self):
        if self._ctx_track_callback:
            self._ctx_track_callback()
        elif self._ctx_target_item_name:
            self._open_add_gear_to_tracker_dialog(prefill_name=self._ctx_target_item_name)

    def _run_ctx_remove(self):
        if self._ctx_remove_callback:
            self._ctx_remove_callback()

    def _bind_tree_wiki_and_menu(self, tree, name_col_idx: int, remove_cb=None, track_cb=None):
        def _on_right_click(event):
            iid = tree.identify_row(event.y)
            if iid:
                tree.selection_set(iid)
                vals = tree.item(iid, "values")
                if vals and len(vals) > name_col_idx:
                    raw_name = str(vals[name_col_idx]).strip()
                    # Ignore category header rows on Page 4
                    if raw_name.startswith("📂") or raw_name.startswith("📁"):
                        return
                    self._ctx_target_item_name = raw_name
                    self._ctx_target_wiki_url = ""
                    self._ctx_remove_callback = remove_cb
                    self._ctx_track_callback = track_cb
                    self.ctx_menu.tk_popup(event.x_root, event.y_root)

        tree.bind("<Button-3>", _on_right_click)
        if remove_cb:
            tree.bind("<Delete>", lambda _e: remove_cb())

    def _get_selected_gear_name_on_page1(self) -> tuple:
        """Returns (item_name, custom_wiki_url) from whichever table on Page 1 has a selection."""
        for tree, name_idx in ((self.tree_jse, 3), (self.tree_rema, 0), (self.tree_cp, 2)):
            sel = tree.selection()
            if sel:
                vals = tree.item(sel[0], "values")
                if vals and len(vals) > name_idx:
                    return str(vals[name_idx]), ""
        return "", ""

    # --------------------------------------------------------------------------
    # TAB 1: JSE, REMA & CHECKPOINT TRACKER
    # --------------------------------------------------------------------------
    def _build_tab1_progression(self):
        # Top Action & Wiki Bar (Windowed-mode safe)
        action_bar = tk.Frame(self.tab1, bg="#1e293b", padx=10, pady=6, highlightbackground="#334155", highlightthickness=1)
        action_bar.pack(fill=tk.X, padx=10, pady=(6, 2))

        left_act = tk.Frame(action_bar, bg="#1e293b")
        left_act.pack(side=tk.LEFT)

        self.page1_all_jobs_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            left_act, text="Show All Jobs on Page 1 (Uncheck to filter by Active Job)",
            variable=self.page1_all_jobs_var, command=self._refresh_trees,
            bg="#1e293b", fg="#38bdf8", selectcolor="#0f172a", activebackground="#1e293b",
            font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            left_act, text="🌐 Add Gear via Wiki URL", bg="#0284c7", fg="#ffffff",
            relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"),
            command=self._open_wiki_import_dialog
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            left_act, text="+ Add Unowned / Custom Gear", bg="#059669", fg="#ffffff",
            relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"),
            command=lambda: self._open_add_gear_to_tracker_dialog()
        ).pack(side=tk.LEFT, padx=3)

        right_wiki = tk.Frame(action_bar, bg="#1e293b")
        right_wiki.pack(side=tk.RIGHT)
        tk.Label(right_wiki, text="Selected Gear Wiki:", bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(right_wiki, text="↗ BG-Wiki", bg="#d97706", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, font=("Segoe UI", 8, "bold"), command=lambda: self._open_page1_wiki("bgwiki")).pack(side=tk.LEFT, padx=2)
        tk.Button(right_wiki, text="↗ FFXIAH", bg="#0369a1", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, font=("Segoe UI", 8, "bold"), command=lambda: self._open_page1_wiki("ffxiah")).pack(side=tk.LEFT, padx=2)
        tk.Button(right_wiki, text="↗ FFXIclopedia", bg="#4f46e5", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, font=("Segoe UI", 8, "bold"), command=lambda: self._open_page1_wiki("ffxiclopedia")).pack(side=tk.LEFT, padx=2)

        # Section 1: Where You Left Off Checkpoints
        top_sec = tk.Frame(self.tab1, bg="#0f172a", padx=10, pady=6)
        top_sec.pack(fill=tk.X)

        hdr = tk.Frame(top_sec, bg="#0f172a")
        hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(hdr, text="📌 WHERE YOU LEFT OFF (SAVED CHECKPOINTS & COUNTERS)", bg="#0f172a", fg="#fbbf24", font=("Consolas", 9, "bold")).pack(side=tk.LEFT)

        btn_row = tk.Frame(hdr, bg="#0f172a")
        btn_row.pack(side=tk.RIGHT)
        tk.Button(btn_row, text="+1 Step", bg="#0284c7", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, command=lambda: self._increment_checkpoint(1)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="+250 Currency", bg="#059669", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, command=lambda: self._increment_checkpoint(250)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="+ New Checkpoint", bg="#4f46e5", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, command=self._add_checkpoint_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="🗑 Remove Selected", bg="#dc2626", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, command=self._remove_selected_checkpoint).pack(side=tk.LEFT, padx=2)

        cols = ("job", "category", "title", "progress", "note")
        self.tree_cp = ttk.Treeview(top_sec, columns=cols, show="headings", height=4)
        self.tree_cp.heading("job", text="Job")
        self.tree_cp.heading("category", text="Category")
        self.tree_cp.heading("title", text="Goal / Weapon / Armor Piece")
        self.tree_cp.heading("progress", text="Progress Counter")
        self.tree_cp.heading("note", text="Where I Stopped / Next Step Note")
        self.tree_cp.column("job", width=55, anchor="center")
        self.tree_cp.column("category", width=145, anchor="w")
        self.tree_cp.column("title", width=230, anchor="w")
        self.tree_cp.column("progress", width=150, anchor="center")
        self.tree_cp.column("note", width=420, anchor="w")
        self.tree_cp.pack(fill=tk.X)
        self._bind_tree_wiki_and_menu(self.tree_cp, 2, remove_cb=self._remove_selected_checkpoint)

        # Lower Split: Left = JSE & Gear Upgrade Tracker, Right = REMA & Prime Weapons
        split = tk.Frame(self.tab1, bg="#0f172a", padx=10, pady=4)
        split.pack(fill=tk.BOTH, expand=True)

        left_box = tk.Frame(split, bg="#0f172a")
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        jse_hdr = tk.Frame(left_box, bg="#0f172a")
        jse_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(jse_hdr, text="🛡️ JSE & GEAR UPGRADE TRACKER", bg="#0f172a", fg="#38bdf8", font=("Consolas", 9, "bold")).pack(side=tk.LEFT)

        jse_btns = tk.Frame(jse_hdr, bg="#0f172a")
        jse_btns.pack(side=tk.RIGHT)
        tk.Button(jse_btns, text="+ Add Gear", bg="#059669", fg="#ffffff", relief=tk.FLAT, padx=6, pady=2, command=lambda: self._open_add_gear_to_tracker_dialog(default_target="jse")).pack(side=tk.LEFT, padx=2)
        tk.Button(jse_btns, text="▲ +1 Tier", bg="#1e293b", fg="#34d399", relief=tk.FLAT, padx=6, pady=2, command=self._advance_jse_tier).pack(side=tk.LEFT, padx=2)
        tk.Button(jse_btns, text="🗑 Remove", bg="#dc2626", fg="#ffffff", relief=tk.FLAT, padx=6, pady=2, command=self._remove_selected_jse).pack(side=tk.LEFT, padx=2)

        jse_cols = ("job", "set", "slot", "name", "tier", "location", "mats")
        self.tree_jse = ttk.Treeview(left_box, columns=jse_cols, show="headings", height=9)
        for c, h, w in [
            ("job", "Job", 45), ("set", "Set", 50), ("slot", "Slot", 55),
            ("name", "Gear Piece Name", 150), ("tier", "Tier", 45),
            ("location", "Bag / Status", 95), ("mats", "Materials / Upgrade Goal", 210)
        ]:
            self.tree_jse.heading(c, text=h)
            self.tree_jse.column(c, width=w, anchor="w")
        self.tree_jse.pack(fill=tk.BOTH, expand=True)
        self._bind_tree_wiki_and_menu(self.tree_jse, 3, remove_cb=self._remove_selected_jse)

        right_box = tk.Frame(split, bg="#0f172a")
        right_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        rema_hdr = tk.Frame(right_box, bg="#0f172a")
        rema_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(rema_hdr, text="🗡️ REMA & PRIME WEAPON TRACKER", bg="#0f172a", fg="#fbbf24", font=("Consolas", 9, "bold")).pack(side=tk.LEFT)

        rema_btns = tk.Frame(rema_hdr, bg="#0f172a")
        rema_btns.pack(side=tk.RIGHT)
        tk.Button(rema_btns, text="+ Add Weapon", bg="#059669", fg="#ffffff", relief=tk.FLAT, padx=6, pady=2, command=lambda: self._open_add_gear_to_tracker_dialog(default_target="rema")).pack(side=tk.LEFT, padx=2)
        tk.Button(rema_btns, text="🔄 Scan Bags", bg="#0284c7", fg="#ffffff", relief=tk.FLAT, padx=6, pady=2, command=lambda: self._send_and_notify("SCAN", "Requested 17-bag & Porter Slip scan from Windower 4.")).pack(side=tk.LEFT, padx=2)
        tk.Button(rema_btns, text="🗑 Remove", bg="#dc2626", fg="#ffffff", relief=tk.FLAT, padx=6, pady=2, command=self._remove_selected_rema).pack(side=tk.LEFT, padx=2)

        rema_cols = ("name", "type", "stage", "detail")
        self.tree_rema = ttk.Treeview(right_box, columns=rema_cols, show="headings", height=9)
        for c, h, w in [
            ("name", "Weapon", 110), ("type", "Type (Job)", 85),
            ("stage", "Current Stage", 135), ("detail", "Trial / Currency Progress", 220)
        ]:
            self.tree_rema.heading(c, text=h)
            self.tree_rema.column(c, width=w, anchor="w")
        self.tree_rema.pack(fill=tk.BOTH, expand=True)
        self._bind_tree_wiki_and_menu(self.tree_rema, 0, remove_cb=self._remove_selected_rema)

    def _open_page1_wiki(self, provider: str):
        item_name, custom_url = self._get_selected_gear_name_on_page1()
        if not item_name:
            messagebox.showinfo("Select a Gear Piece", "Click any row in Checkpoints, JSE Armor, or REMA Weapons first, then click a Wiki button (or right-click any row).")
            return
        open_item_wiki(item_name, provider, custom_url)
        self._set_status(f"Opened {provider.upper()} for '{item_name}'.")

    def _remove_selected_checkpoint(self):
        sel = self.tree_cp.selection()
        if not sel:
            self._set_status("Select a checkpoint row in 'Where You Left Off' first to remove it.")
            return
        vis_idx = int(sel[0])
        real_idx = self._cp_index_map.get(vis_idx, vis_idx)
        cps = self.bridge.db.get("checkpoints", [])
        if 0 <= real_idx < len(cps):
            target_cp = cps[real_idx]
            if messagebox.askyesno(
                "Confirm Checkpoint Removal",
                f"Are you sure you want to remove checkpoint:\n\n'{target_cp.get('title', '')}' ({target_cp.get('category', '')})?"
            ):
                removed = cps.pop(real_idx)
                save_database(self.bridge.db)
                self._refresh_trees()
                self._set_status(f"Removed checkpoint '{removed.get('title', '')}'.")

    def _remove_selected_jse(self):
        sel = self.tree_jse.selection()
        if not sel:
            self._set_status("Select a gear row in 'JSE & Gear Upgrade Tracker' first to remove it.")
            return
        vis_idx = int(sel[0])
        mapping = self._jse_index_map.get(vis_idx)
        if not mapping:
            return
        job_key, row_idx = mapping
        rows = self.bridge.db.get("jse_by_job", {}).get(job_key, [])
        if 0 <= row_idx < len(rows):
            target_row = rows[row_idx]
            if messagebox.askyesno(
                "Confirm Gear Removal",
                f"Are you sure you want to remove '{target_row.get('name', '')}' ({job_key} - {target_row.get('set', '')} {target_row.get('slot', '')}) from the Page 1 tracker?"
            ):
                removed = rows.pop(row_idx)
                save_database(self.bridge.db)
                self._refresh_trees()
                self._set_status(f"Removed '{removed.get('name', '')}' ({job_key}) from JSE & Gear Tracker.")

    def _remove_selected_rema(self):
        sel = self.tree_rema.selection()
        if not sel:
            self._set_status("Select a weapon in 'REMA & Prime Weapon Tracker' first to remove it.")
            return
        vis_idx = int(sel[0])
        real_idx = self._rema_index_map.get(vis_idx, vis_idx)
        remas = self.bridge.db.get("rema_weapons", [])
        if 0 <= real_idx < len(remas):
            target_w = remas[real_idx]
            if messagebox.askyesno(
                "Confirm Weapon Removal",
                f"Are you sure you want to remove '{target_w.get('name', '')}' ({target_w.get('type', '')} - {target_w.get('job', '')}) from the REMA Weapon Tracker?"
            ):
                removed = remas.pop(real_idx)
                save_database(self.bridge.db)
                self._refresh_trees()
                self._set_status(f"Removed '{removed.get('name', '')}' from REMA Weapon Tracker.")

    # --------------------------------------------------------------------------
    # DIALOGS: ADD GEAR / ASSIGN TO JOB & IMPORT BY WIKI LINK
    # --------------------------------------------------------------------------
    def _open_add_gear_to_tracker_dialog(
        self,
        prefill_name: str = "",
        prefill_bag: str = "Unowned / Target Goal",
        prefill_augments: str = "",
        prefill_count: int = 0,
        default_target: str = "jse"
    ):
        win = tk.Toplevel(self.root)
        win.title("Add / Track Gear Piece & Assign to Job")
        win.geometry("500x430")
        win.configure(bg="#0f172a")
        win.attributes("-topmost", True)

        tk.Label(
            win,
            text="📌 Track Gear / Upgrade Goal (Works for Owned & Unowned Gear)",
            bg="#0f172a", fg="#38bdf8", font=("Consolas", 10, "bold")
        ).pack(anchor="w", padx=14, pady=(10, 6))

        form = tk.Frame(win, bg="#0f172a", padx=14)
        form.pack(fill=tk.BOTH, expand=True)

        # 1. Assign to Job
        tk.Label(form, text="1. Assign to Job:", bg="#0f172a", fg="#fbbf24", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        job_var = tk.StringVar(value=self.bridge.live.get("main_job", "BLU"))
        job_cb = ttk.Combobox(form, textvariable=job_var, values=ALL_FFXI_JOBS, width=14, state="readonly")
        job_cb.grid(row=0, column=1, sticky="w", pady=4)

        # 2. Target Tracker Section
        tk.Label(form, text="2. Add to Tracker Section:", bg="#0f172a", fg="#fbbf24", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        target_var = tk.StringVar(value=default_target)
        target_frame = tk.Frame(form, bg="#0f172a")
        target_frame.grid(row=1, column=1, sticky="w", pady=4)
        for lbl, val in [
            ("Page 1: JSE / Gear Tracker", "jse"),
            ("Page 1: REMA / Weapon", "rema"),
            ("Page 1: Checkpoint Counter", "cp"),
            ("Page 2: Wishlist", "wishlist")
        ]:
            tk.Radiobutton(
                target_frame, text=lbl, variable=target_var, value=val,
                bg="#0f172a", fg="#e2e8f0", selectcolor="#1e293b", activebackground="#0f172a"
            ).pack(anchor="w")

        # 3. Item Name
        tk.Label(form, text="3. Item / Gear Name:", bg="#0f172a", fg="#94a3b8").grid(row=2, column=0, sticky="w", pady=4)
        e_name = tk.Entry(form, bg="#1e293b", fg="#ffffff", insertbackground="#ffffff", width=38)
        e_name.insert(0, prefill_name or "Assimilator's Keffiyeh +3")
        e_name.grid(row=2, column=1, sticky="w", pady=4)

        # 4. Set / Type & Slot
        tk.Label(form, text="4. Set Type & Slot:", bg="#0f172a", fg="#94a3b8").grid(row=3, column=0, sticky="w", pady=4)
        row_ss = tk.Frame(form, bg="#0f172a")
        row_ss.grid(row=3, column=1, sticky="w", pady=4)
        set_var = tk.StringVar(value="AF")
        ttk.Combobox(row_ss, textvariable=set_var, values=["AF", "Relic", "Empy", "Odyssey", "Omen", "Sortie", "Su5", "Mythic", "Aeonic", "Prime", "Custom"], width=10).pack(side=tk.LEFT, padx=(0, 6))
        slot_var = tk.StringVar(value="Head")
        ttk.Combobox(row_ss, textvariable=slot_var, values=["Main", "Sub", "Range", "Ammo", "Head", "Neck", "Earring", "Body", "Hands", "Ring", "Back", "Waist", "Legs", "Feet"], width=10).pack(side=tk.LEFT, padx=(0, 6))
        tier_var = tk.StringVar(value="+2" if "+2" in prefill_name else ("+3" if "+3" in prefill_name else ("+1" if "+1" in prefill_name else "Goal")))
        ttk.Combobox(row_ss, textvariable=tier_var, values=["Unowned", "Base", "+1", "+2", "+3", "+4", "R15", "R25", "R30", "Goal"], width=8).pack(side=tk.LEFT)

        # 5. Bag / Status Location
        tk.Label(form, text="5. Bag / Status:", bg="#0f172a", fg="#94a3b8").grid(row=4, column=0, sticky="w", pady=4)
        e_loc = tk.Entry(form, bg="#1e293b", fg="#ffffff", insertbackground="#ffffff", width=38)
        e_loc.insert(0, prefill_bag)
        e_loc.grid(row=4, column=1, sticky="w", pady=4)

        # 6. Upgrade Materials / Notes / Counter Target
        tk.Label(form, text="6. Upgrade Mats / Notes:", bg="#0f172a", fg="#94a3b8").grid(row=5, column=0, sticky="w", pady=4)
        e_mats = tk.Entry(form, bg="#1e293b", fg="#ffffff", insertbackground="#ffffff", width=38)
        default_note = prefill_augments if prefill_augments else "Need Omen Cards / Dynamis [D] / Sortie Mats"
        if prefill_count > 1:
            default_note = f"Total across bags: {prefill_count:,} ({prefill_bag})"
        e_mats.insert(0, default_note)
        e_mats.grid(row=5, column=1, sticky="w", pady=4)

        def _confirm_add():
            iname = e_name.get().strip()
            if not iname:
                return
            chosen_job = job_var.get().strip() or self.bridge.live.get("main_job", "BLU")
            sec = target_var.get()
            stype = set_var.get().strip() or "Custom"
            sl = slot_var.get().strip() or "Gear"
            tr = tier_var.get().strip() or "Goal"
            loc = e_loc.get().strip() or "Unowned"
            mats = e_mats.get().strip()
            urls = build_wiki_urls(iname)

            if sec == "jse":
                target_job_key = chosen_job if chosen_job != "All" else self.bridge.live.get("main_job", "BLU")
                self.bridge.db.setdefault("jse_by_job", {}).setdefault(target_job_key, []).insert(0, {
                    "id": f"jse-{int(time.time()*1000)}",
                    "set": stype,
                    "slot": sl,
                    "name": iname,
                    "tier": tr,
                    "location": loc,
                    "mats": mats,
                    "ready": False
                })
                # Switch active job view if needed so user immediately sees it
                if not self.page1_all_jobs_var.get() and self.bridge.live.get("main_job") != target_job_key:
                    self.bridge.live["main_job"] = target_job_key
                    self.job_var.set(target_job_key)
                msg = f"Added '{iname}' to Page 1 JSE & Gear Tracker under job {target_job_key}!"
            elif sec == "rema":
                self.bridge.db.setdefault("rema_weapons", []).insert(0, {
                    "id": f"rema-{int(time.time()*1000)}",
                    "name": iname,
                    "type": stype,
                    "job": chosen_job,
                    "stage": f"{tr} ({loc})",
                    "progressPct": 0,
                    "detail": mats,
                    "rp": ""
                })
                msg = f"Added '{iname}' ({chosen_job}) to Page 1 REMA & Weapon Tracker!"
            elif sec == "cp":
                self.bridge.db.setdefault("checkpoints", []).insert(0, {
                    "id": f"cp-{int(time.time()*1000)}",
                    "job": chosen_job,
                    "category": f"{stype.upper()} ({chosen_job})",
                    "title": iname,
                    "current": max(0, prefill_count),
                    "target": 100 if prefill_count <= 1 else max(prefill_count, 30000),
                    "unit": "Progress",
                    "note": mats or loc,
                    "wikiUrl": urls["bgwiki"],
                    "pinned": True
                })
                msg = f"Added '{iname}' ({chosen_job}) to Page 1 Where You Left Off Checkpoints!"
            else:
                self.bridge.db.setdefault("wishlist", []).insert(0, {
                    "id": f"wl-{int(time.time()*1000)}",
                    "job": chosen_job,
                    "name": iname,
                    "slot": f"{sl} ({chosen_job})",
                    "sourceType": stype,
                    "zone": loc,
                    "obtainHow": mats,
                    "costOrPop": tr,
                    "detectedFrom": f"Tracked for {chosen_job}",
                    "wikiUrl": urls["bgwiki"],
                    "pinned": True
                })
                msg = f"Added '{iname}' ({chosen_job}) to Page 2 Wishlist!"

            save_database(self.bridge.db)
            self._refresh_trees()
            win.destroy()
            self._set_status(msg)

        btn_f = tk.Frame(win, bg="#0f172a", pady=10)
        btn_f.pack(fill=tk.X, padx=14)
        tk.Button(btn_f, text="✓ Save & Track Item", bg="#0284c7", fg="#ffffff", relief=tk.FLAT, padx=16, pady=6, font=("Segoe UI", 9, "bold"), command=_confirm_add).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_f, text="Cancel", bg="#334155", fg="#e2e8f0", relief=tk.FLAT, padx=12, pady=6, command=win.destroy).pack(side=tk.LEFT)

    def _open_wiki_import_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Import Item from Wiki Link (BG-Wiki / FFXIAH / FFXIclopedia)")
        win.geometry("540x300")
        win.configure(bg="#0f172a")
        win.attributes("-topmost", True)

        tk.Label(
            win,
            text="🌐 Paste Any BG-Wiki, FFXIAH, or FFXIclopedia Link (or Item Name)",
            bg="#0f172a", fg="#38bdf8", font=("Consolas", 10, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 4))

        tk.Label(
            win,
            text="Example: https://www.bg-wiki.com/ffxi/Lugalbanda_Earring  or  https://www.ffxiah.com/search/item?q=Nyame+Mail",
            bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 8)
        ).pack(anchor="w", padx=14, pady=(0, 6))

        e_url = tk.Entry(win, bg="#1e293b", fg="#ffffff", insertbackground="#ffffff", width=66)
        e_url.insert(0, "https://www.bg-wiki.com/ffxi/Apogee_Dalmatica_%2B1")
        e_url.pack(padx=14, pady=4)

        opts = tk.Frame(win, bg="#0f172a", padx=14, pady=6)
        opts.pack(fill=tk.X)

        tk.Label(opts, text="Assign to Job:", bg="#0f172a", fg="#fbbf24", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        job_var = tk.StringVar(value=self.bridge.live.get("main_job", "SMN"))
        ttk.Combobox(opts, textvariable=job_var, values=ALL_FFXI_JOBS, width=12, state="readonly").grid(row=0, column=1, sticky="w", padx=8, pady=4)

        tk.Label(opts, text="Destination:", bg="#0f172a", fg="#fbbf24", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        dest_var = tk.StringVar(value="jse")
        dest_cb = ttk.Combobox(
            opts, textvariable=dest_var,
            values=[
                "Page 1: JSE & Gear Upgrade Tracker",
                "Page 1: REMA & Weapon Tracker",
                "Page 1: Where You Left Off Checkpoint",
                "Page 2: Wishlist & How to Obtain"
            ],
            width=34, state="readonly"
        )
        dest_cb.current(0)
        dest_cb.grid(row=1, column=1, sticky="w", padx=8, pady=4)

        tk.Label(opts, text="Notes / Upgrade Goal:", bg="#0f172a", fg="#94a3b8").grid(row=2, column=0, sticky="w", pady=4)
        e_note = tk.Entry(opts, bg="#1e293b", fg="#ffffff", insertbackground="#ffffff", width=38)
        e_note.insert(0, "Imported via Wiki URL — Track upgrade / obtain status")
        e_note.grid(row=2, column=1, sticky="w", padx=8, pady=4)

        def _do_import():
            raw = e_url.get().strip()
            parsed = parse_wiki_url_or_name(raw)
            iname = parsed["name"]
            if not iname:
                messagebox.showwarning("Invalid Link", "Please paste a valid Wiki URL or item name.")
                return
            chosen_job = job_var.get().strip() or "All"
            dest_label = dest_var.get()
            note_txt = e_note.get().strip()
            cat_meta = self.bridge.db.get("catalog_db", {}).get(iname, {})

            if "JSE & Gear" in dest_label:
                jkey = chosen_job if chosen_job != "All" else self.bridge.live.get("main_job", "BLU")
                tier_guess = "+3" if "+3" in iname else ("+2" if "+2" in iname else ("+1" if "+1" in iname else "Goal"))
                self.bridge.db.setdefault("jse_by_job", {}).setdefault(jkey, []).insert(0, {
                    "id": f"wiki-jse-{int(time.time()*1000)}",
                    "set": "Wiki",
                    "slot": cat_meta.get("slot", "Gear").split(" ")[0],
                    "name": iname,
                    "tier": tier_guess,
                    "location": "Unowned / Goal",
                    "mats": note_txt or cat_meta.get("obtainHow", f"Wiki ({parsed['source_site']})"),
                    "ready": False
                })
                if not self.page1_all_jobs_var.get():
                    self.bridge.live["main_job"] = jkey
                    self.job_var.set(jkey)
            elif "REMA" in dest_label:
                self.bridge.db.setdefault("rema_weapons", []).insert(0, {
                    "id": f"wiki-rema-{int(time.time()*1000)}",
                    "name": iname,
                    "type": "Weapon",
                    "job": chosen_job,
                    "stage": "Tracked via Wiki",
                    "progressPct": 0,
                    "detail": note_txt,
                    "rp": parsed["wikiUrl"]
                })
            elif "Checkpoint" in dest_label:
                self.bridge.db.setdefault("checkpoints", []).insert(0, {
                    "id": f"wiki-cp-{int(time.time()*1000)}",
                    "job": chosen_job,
                    "category": f"WIKI GOAL ({chosen_job})",
                    "title": iname,
                    "current": 0,
                    "target": 1,
                    "unit": "Goal",
                    "note": note_txt,
                    "wikiUrl": parsed["wikiUrl"],
                    "pinned": True
                })
            else:
                self.bridge.db.setdefault("wishlist", []).insert(0, {
                    "id": f"wiki-wl-{int(time.time()*1000)}",
                    "job": chosen_job,
                    "name": iname,
                    "slot": cat_meta.get("slot", f"Gear ({chosen_job})"),
                    "sourceType": cat_meta.get("sourceType", f"Imported from {parsed['source_site']}"),
                    "zone": cat_meta.get("zone", "See Wiki Link"),
                    "obtainHow": cat_meta.get("obtainHow", note_txt),
                    "costOrPop": cat_meta.get("costOrPop", "See Wiki"),
                    "detectedFrom": f"Wiki Import ({chosen_job})",
                    "wikiUrl": parsed["wikiUrl"],
                    "pinned": True
                })

            save_database(self.bridge.db)
            self._refresh_trees()
            win.destroy()
            self._set_status(f"Imported '{iname}' ({chosen_job}) from {parsed['source_site']}!")

        btn_row = tk.Frame(win, bg="#0f172a", pady=10)
        btn_row.pack(fill=tk.X, padx=14)
        tk.Button(btn_row, text="🌐 Import & Track Item", bg="#0284c7", fg="#ffffff", relief=tk.FLAT, padx=14, pady=5, font=("Segoe UI", 9, "bold"), command=_do_import).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_row, text="Cancel", bg="#334155", fg="#e2e8f0", relief=tk.FLAT, padx=12, pady=5, command=win.destroy).pack(side=tk.LEFT)

    # --------------------------------------------------------------------------
    # TAB 2: WISHLIST & HOW TO OBTAIN (2-ROW RESPONSIVE TOOLBAR + MULTI-WIKI)
    # --------------------------------------------------------------------------
    def _build_tab2_wishlist(self):
        bar1 = tk.Frame(self.tab2, bg="#0f172a", padx=10, pady=6)
        bar1.pack(fill=tk.X)

        tk.Label(bar1, text="Quick-Add Catalog:", bg="#0f172a", fg="#94a3b8").pack(side=tk.LEFT)
        self.catalog_var = tk.StringVar()
        catalog_items = sorted(list(self.bridge.db.get("catalog_db", {}).keys()))
        self.catalog_combo = ttk.Combobox(bar1, textvariable=self.catalog_var, values=catalog_items, width=24, state="readonly")
        self.catalog_combo.pack(side=tk.LEFT, padx=6)

        tk.Button(bar1, text="+ Add from Catalog", bg="#059669", fg="#ffffff", relief=tk.FLAT, padx=8, pady=3, command=self._add_from_catalog).pack(side=tk.LEFT, padx=3)
        tk.Button(bar1, text="🌐 Add by Wiki Link", bg="#0284c7", fg="#ffffff", relief=tk.FLAT, padx=8, pady=3, command=self._open_wiki_import_dialog).pack(side=tk.LEFT, padx=3)
        tk.Button(bar1, text="+ Add Custom Unowned Gear", bg="#4f46e5", fg="#ffffff", relief=tk.FLAT, padx=8, pady=3, command=lambda: self._open_add_gear_to_tracker_dialog(default_target="wishlist")).pack(side=tk.LEFT, padx=3)
        tk.Button(bar1, text="📂 Scan Local .lua...", bg="#1e293b", fg="#38bdf8", relief=tk.FLAT, padx=8, pady=3, command=self._scan_local_gearswap_file).pack(side=tk.LEFT, padx=3)

        # Second Toolbar Row so Wiki & Remove buttons NEVER get cut off in Windowed Mode!
        bar2 = tk.Frame(self.tab2, bg="#1e293b", padx=10, pady=5, highlightbackground="#334155", highlightthickness=1)
        bar2.pack(fill=tk.X, padx=10, pady=(0, 6))

        tk.Label(bar2, text="Selected Wishlist Item Actions:", bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(bar2, text="↗ BG-Wiki", bg="#d97706", fg="#ffffff", relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"), command=lambda: self._open_selected_wiki("bgwiki")).pack(side=tk.LEFT, padx=3)
        tk.Button(bar2, text="↗ FFXIAH", bg="#0369a1", fg="#ffffff", relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"), command=lambda: self._open_selected_wiki("ffxiah")).pack(side=tk.LEFT, padx=3)
        tk.Button(bar2, text="↗ FFXIclopedia", bg="#4f46e5", fg="#ffffff", relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"), command=lambda: self._open_selected_wiki("ffxiclopedia")).pack(side=tk.LEFT, padx=3)

        tk.Button(bar2, text="🗑 Remove Selected (Confirm)", bg="#dc2626", fg="#ffffff", relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"), command=self._mark_wishlist_obtained).pack(side=tk.RIGHT, padx=3)
        tk.Button(bar2, text="📌 Copy to Page 1 Tracker", bg="#059669", fg="#ffffff", relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"), command=self._promote_wishlist_to_page1).pack(side=tk.RIGHT, padx=3)

        wl_cols = ("job", "name", "slot", "sourceType", "zone", "costOrPop", "obtainHow")
        self.tree_wl = ttk.Treeview(self.tab2, columns=wl_cols, show="headings", height=15)
        for c, h, w in [
            ("job", "Job", 55),
            ("name", "Missing / Goal Gear Item", 155),
            ("slot", "Slot / Jobs", 125),
            ("sourceType", "Content Type", 140),
            ("zone", "Zone / NM / NPC", 165),
            ("costOrPop", "Pop Item / Currency Cost", 175),
            ("obtainHow", "How to Obtain Step-by-Step", 300)
        ]:
            self.tree_wl.heading(c, text=h)
            self.tree_wl.column(c, width=w, anchor="w")
        self.tree_wl.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self._bind_tree_wiki_and_menu(self.tree_wl, 1, remove_cb=self._mark_wishlist_obtained, track_cb=self._promote_wishlist_to_page1)

    def _promote_wishlist_to_page1(self):
        sel = self.tree_wl.selection()
        wlist = self.bridge.db.get("wishlist", [])
        if not sel or not wlist:
            self._set_status("Select a Wishlist item first to copy it to Page 1.")
            return
        vis_idx = int(sel[0])
        real_idx = self._wl_index_map.get(vis_idx, vis_idx)
        if 0 <= real_idx < len(wlist):
            w = wlist[real_idx]
            self._open_add_gear_to_tracker_dialog(
                prefill_name=w.get("name", ""),
                prefill_bag=f"Wishlist ({w.get('zone', 'Unowned')})",
                prefill_augments=w.get("obtainHow", ""),
                default_target="jse"
            )

    # --------------------------------------------------------------------------
    # TAB 3: LIVE STATS & MOTE GEARSWAP
    # --------------------------------------------------------------------------
    def _build_tab3_stats_mote(self):
        container = tk.Frame(self.tab3, bg="#0f172a", padx=12, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        stat_row = tk.Frame(container, bg="#0f172a")
        stat_row.pack(fill=tk.X, pady=(0, 10))

        self.lbl_stat_cards = {}
        card_defs = [
            ("acc_atk", "MAIN ACC / ATK", "1,482 / 2,190", "#ffffff"),
            ("haste", "GEAR / MAGIC HASTE", "25.0% / 43.75%", "#38bdf8"),
            ("dw", "MOTE HASTE GROUP & DW", "MaxHaste (0% DW)", "#34d399"),
            ("dt", "DAMAGE TAKEN (DT)", "-50% / -50% (Capped)", "#fbbf24")
        ]
        for key, title, default_val, color in card_defs:
            card = tk.Frame(stat_row, bg="#1e293b", padx=14, pady=8, highlightbackground="#334155", highlightthickness=1)
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            tk.Label(card, text=title, bg="#1e293b", fg="#94a3b8", font=("Consolas", 8, "bold")).pack(anchor="w")
            lbl = tk.Label(card, text=default_val, bg="#1e293b", fg=color, font=("Consolas", 12, "bold"))
            lbl.pack(anchor="w", pady=(4, 0))
            self.lbl_stat_cards[key] = lbl

        mote_frame = tk.Frame(container, bg="#1e293b", padx=12, pady=8, highlightbackground="#0284c7", highlightthickness=1)
        mote_frame.pack(fill=tk.X, pady=(0, 10))

        top_m = tk.Frame(mote_frame, bg="#1e293b")
        top_m.pack(fill=tk.X, pady=(0, 6))
        tk.Label(top_m, text="🎛️ MOTE-INCLUDE GEARSWAP CONTROLLER (CLICK TO CYCLE IN-GAME)", bg="#1e293b", fg="#38bdf8", font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(
            top_m, text="⚡ 1-Click Install Mote_Nexus_Hook.lua into Windower 4",
            bg="#059669", fg="#ffffff", relief=tk.FLAT, padx=10, pady=3, font=("Segoe UI", 8, "bold"),
            command=self._install_mote_hook_wizard
        ).pack(side=tk.RIGHT)

        btn_bar = tk.Frame(mote_frame, bg="#1e293b")
        btn_bar.pack(fill=tk.X)
        self.mote_buttons = {}
        for mode_key in ("OffenseMode", "HybridMode", "WeaponskillMode", "IdleMode", "WeaponSet"):
            val = self.bridge.live["mote_modes"].get(mode_key, "Normal")
            b = tk.Button(
                btn_bar, text=f"{mode_key}: {val} ↻",
                bg="#0f172a", fg="#e2e8f0", activebackground="#0284c7", activeforeground="#ffffff",
                relief=tk.FLAT, padx=10, pady=5, font=("Consolas", 9, "bold"),
                command=lambda mk=mode_key: self._cycle_mote_mode(mk)
            )
            b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            self.mote_buttons[mode_key] = b

        eq_hdr = tk.Frame(container, bg="#0f172a")
        eq_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(eq_hdr, text="🔍 LIVE EQUIPPED GEAR & DECODED AUGMENTS (Right-Click Any Piece for Wiki / Track)", bg="#0f172a", fg="#fbbf24", font=("Consolas", 9, "bold")).pack(side=tk.LEFT)
        tk.Button(eq_hdr, text="↗ BG-Wiki", bg="#d97706", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, command=lambda: self._open_eq_wiki("bgwiki")).pack(side=tk.RIGHT, padx=2)
        tk.Button(eq_hdr, text="↗ FFXIAH", bg="#0369a1", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, command=lambda: self._open_eq_wiki("ffxiah")).pack(side=tk.RIGHT, padx=2)
        tk.Button(eq_hdr, text="↗ FFXIclopedia", bg="#4f46e5", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, command=lambda: self._open_eq_wiki("ffxiclopedia")).pack(side=tk.RIGHT, padx=2)

        eq_cols = ("slot", "name", "augments")
        self.tree_eq = ttk.Treeview(container, columns=eq_cols, show="headings", height=8)
        self.tree_eq.heading("slot", text="Equipment Slot")
        self.tree_eq.heading("name", text="Equipped Item")
        self.tree_eq.heading("augments", text="Decoded Path / Rank (1-30) & Augment Stats")
        self.tree_eq.column("slot", width=130, anchor="w")
        self.tree_eq.column("name", width=240, anchor="w")
        self.tree_eq.column("augments", width=650, anchor="w")
        self.tree_eq.pack(fill=tk.BOTH, expand=True)
        self._bind_tree_wiki_and_menu(self.tree_eq, 1)

    def _open_eq_wiki(self, provider: str):
        sel = self.tree_eq.selection()
        if not sel:
            return
        vals = self.tree_eq.item(sel[0], "values")
        if vals and len(vals) > 1:
            open_item_wiki(str(vals[1]), provider)

    # --------------------------------------------------------------------------
    # TAB 4: INVENTORY, CATEGORIZATION, CONSOLIDATION & SCATTERED-BAG BROWSER
    # --------------------------------------------------------------------------
    def _build_tab4_utilities(self):
        split = tk.Frame(self.tab4, bg="#0f172a", padx=10, pady=6)
        split.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(split, bg="#0f172a")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # Row 1: Search + Category Filter + Character Filter + Bag Filter
        f_bar1 = tk.Frame(left, bg="#0f172a")
        f_bar1.pack(fill=tk.X, pady=(0, 4))

        tk.Label(f_bar1, text="🔍 Search:", bg="#0f172a", fg="#38bdf8", font=("Consolas", 9, "bold")).pack(side=tk.LEFT)
        self.inv_search_var = tk.StringVar()
        self.inv_search_var.trace_add("write", lambda *_: self._refresh_trees())
        tk.Entry(f_bar1, textvariable=self.inv_search_var, bg="#1e293b", fg="#ffffff", insertbackground="#ffffff", relief=tk.FLAT, width=20).pack(side=tk.LEFT, padx=(4, 10))

        tk.Label(f_bar1, text="Category:", bg="#0f172a", fg="#94a3b8").pack(side=tk.LEFT)
        self.inv_cat_var = tk.StringVar(value="All Categories")
        self.inv_cat_combo = ttk.Combobox(
            f_bar1, textvariable=self.inv_cat_var,
            values=["All Categories"] + ITEM_CATEGORIES,
            width=26, state="readonly"
        )
        self.inv_cat_combo.pack(side=tk.LEFT, padx=(4, 10))
        self.inv_cat_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_trees())

        tk.Label(f_bar1, text="Char:", bg="#0f172a", fg="#94a3b8").pack(side=tk.LEFT)
        self.inv_char_var = tk.StringVar(value="All Characters")
        self.inv_char_combo = ttk.Combobox(
            f_bar1, textvariable=self.inv_char_var,
            values=["All Characters", "Someonesmall", "AltMuleA"],
            width=14, state="readonly"
        )
        self.inv_char_combo.pack(side=tk.LEFT, padx=(4, 10))
        self.inv_char_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_trees())

        tk.Label(f_bar1, text="Bag:", bg="#0f172a", fg="#94a3b8").pack(side=tk.LEFT)
        self.inv_bag_var = tk.StringVar(value="All Bags")
        self.inv_bag_combo = ttk.Combobox(
            f_bar1, textvariable=self.inv_bag_var,
            values=[
                "All Bags", "Inventory", "Wardrobe 1", "Wardrobe 2", "Wardrobe 3", "Wardrobe 4",
                "Wardrobe 5", "Wardrobe 6", "Wardrobe 7", "Wardrobe 8",
                "Mog Satchel", "Mog Sack", "Mog Case", "Mog Safe 1", "Mog Safe 2",
                "Mog Storage", "Mog Locker", "Porter Slip 25"
            ],
            width=13, state="readonly"
        )
        self.inv_bag_combo.pack(side=tk.LEFT, padx=4)
        self.inv_bag_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_trees())

        # Row 2: Toggles (Group by Category, Scattered Only, Mats Only, Gear Only)
        f_bar2 = tk.Frame(left, bg="#0f172a")
        f_bar2.pack(fill=tk.X, pady=(0, 4))

        self.inv_group_by_cat_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            f_bar2, text="📂 Group by Category Folders", variable=self.inv_group_by_cat_var,
            command=self._refresh_trees, bg="#0f172a", fg="#38bdf8", selectcolor="#1e293b", activebackground="#0f172a", font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.inv_scattered_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            f_bar2, text="⚠️ Scattered Across Multiple Bags Only", variable=self.inv_scattered_only_var,
            command=self._refresh_trees, bg="#0f172a", fg="#fbbf24", selectcolor="#1e293b", activebackground="#0f172a", font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.inv_mats_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            f_bar2, text="💎 Currencies & Mats Only", variable=self.inv_mats_only_var,
            command=self._refresh_trees, bg="#0f172a", fg="#34d399", selectcolor="#1e293b", activebackground="#0f172a", font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.inv_gear_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            f_bar2, text="⚔️ Equippable Gear Only", variable=self.inv_gear_only_var,
            command=self._refresh_trees, bg="#0f172a", fg="#e2e8f0", selectcolor="#1e293b", activebackground="#0f172a", font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(f_bar2, text="⊞ Expand All", bg="#1e293b", fg="#cbd5e1", relief=tk.FLAT, padx=6, pady=1, font=("Segoe UI", 8), command=lambda: self._expand_collapse_inv(True)).pack(side=tk.RIGHT, padx=2)
        tk.Button(f_bar2, text="⊟ Collapse All", bg="#1e293b", fg="#cbd5e1", relief=tk.FLAT, padx=6, pady=1, font=("Segoe UI", 8), command=lambda: self._expand_collapse_inv(False)).pack(side=tk.RIGHT, padx=2)

        # Row 3: Action Bar (Track Selected on Page 1 + Wiki Buttons + Import findAll)
        f_bar3 = tk.Frame(left, bg="#1e293b", padx=8, pady=5, highlightbackground="#334155", highlightthickness=1)
        f_bar3.pack(fill=tk.X, pady=(0, 6))

        tk.Button(
            f_bar3, text="📌 Track Selected on Page 1 (Assign Job)...",
            bg="#059669", fg="#ffffff", relief=tk.FLAT, padx=10, pady=2, font=("Segoe UI", 8, "bold"),
            command=self._track_selected_page4_item
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            f_bar3, text="📂 Load findAll / Character Bags...",
            bg="#0284c7", fg="#ffffff", relief=tk.FLAT, padx=8, pady=2, font=("Segoe UI", 8, "bold"),
            command=self._import_findall_or_csv_bags
        ).pack(side=tk.LEFT, padx=3)

        self.lbl_inv_summary = tk.Label(f_bar3, text="Showing 0 items", bg="#1e293b", fg="#94a3b8", font=("Consolas", 8))
        self.lbl_inv_summary.pack(side=tk.LEFT, padx=8)

        tk.Button(f_bar3, text="↗ FFXIclopedia", bg="#4f46e5", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, font=("Segoe UI", 8, "bold"), command=lambda: self._open_page4_wiki("ffxiclopedia")).pack(side=tk.RIGHT, padx=2)
        tk.Button(f_bar3, text="↗ FFXIAH", bg="#0369a1", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, font=("Segoe UI", 8, "bold"), command=lambda: self._open_page4_wiki("ffxiah")).pack(side=tk.RIGHT, padx=2)
        tk.Button(f_bar3, text="↗ BG-Wiki", bg="#d97706", fg="#ffffff", relief=tk.FLAT, padx=7, pady=2, font=("Segoe UI", 8, "bold"), command=lambda: self._open_page4_wiki("bgwiki")).pack(side=tk.RIGHT, padx=2)

        # Page 4 Treeview (supports both collapsible category tree & flat mode)
        inv_frame = tk.Frame(left, bg="#0f172a")
        inv_frame.pack(fill=tk.BOTH, expand=True)

        inv_cols = ("name", "total_qty", "scattered", "locations", "augments")
        self.tree_inv = ttk.Treeview(inv_frame, columns=inv_cols, show="headings", height=14)
        for c, h, w, anc in [
            ("name", "Category / Item Name", 215, "w"),
            ("total_qty", "Total Qty", 75, "center"),
            ("scattered", "Bag Status", 135, "center"),
            ("locations", "Character & Bag Locations (Per-Bag Qty)", 255, "w"),
            ("augments", "Augments (Same Name + Diff Augment Kept Separate)", 260, "w")
        ]:
            self.tree_inv.heading(c, text=h)
            self.tree_inv.column(c, width=w, anchor=anc)

        inv_scroll = ttk.Scrollbar(inv_frame, orient=tk.VERTICAL, command=self.tree_inv.yview)
        self.tree_inv.configure(yscrollcommand=inv_scroll.set)
        self.tree_inv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inv_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_inv.tag_configure("cat_header", background="#1e293b", foreground="#38bdf8", font=("Consolas", 9, "bold"))
        self.tree_inv.tag_configure("scattered_row", background="#1f2421", foreground="#fbbf24")
        self.tree_inv.tag_configure("normal_row", background="#0f172a", foreground="#e2e8f0")

        self._bind_tree_wiki_and_menu(self.tree_inv, 0, track_cb=self._track_selected_page4_item)

        # Right side: Compact Superwarp Quick Travel
        right = tk.Frame(split, bg="#0f172a", width=250)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))

        tk.Label(right, text="🌀 SUPERWARP QUICK TRAVEL", bg="#0f172a", fg="#fbbf24", font=("Consolas", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self.sendall_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            right, text="Send All (//sw hp all)", variable=self.sendall_var,
            bg="#0f172a", fg="#e2e8f0", selectcolor="#1e293b", activebackground="#0f172a"
        ).pack(anchor="w", pady=(0, 6))

        warps = [
            ("Rabao HP #1 (Odyssey)", "Rabao 1"),
            ("Kamihr Drifts (Sortie)", "Kamihr Drifts"),
            ("Reisenjima (Omen)", "Reisenjima"),
            ("Ru'Lude Gardens HP #1", "Ru'Lude Gardens 1"),
            ("Port Jeuno HP #1", "Port Jeuno 1"),
            ("Nashmau HP #1 (Alexandrite)", "Nashmau 1")
        ]
        for label, dest in warps:
            tk.Button(
                right, text=f"⚡ {label}", bg="#1e293b", fg="#38bdf8",
                activebackground="#0284c7", activeforeground="#ffffff",
                relief=tk.FLAT, anchor="w", padx=8, pady=4, font=("Segoe UI", 8),
                command=lambda d=dest: self._trigger_superwarp(d)
            ).pack(fill=tk.X, pady=2)

    def _expand_collapse_inv(self, expand: bool):
        for iid in self.tree_inv.get_children(""):
            self.tree_inv.item(iid, open=expand)

    def _get_selected_page4_item(self):
        sel = self.tree_inv.selection()
        if not sel:
            return None
        iid = sel[0]
        return self._inv_item_map.get(iid)

    def _track_selected_page4_item(self):
        item = self._get_selected_page4_item()
        if not item:
            messagebox.showinfo("Select an Item on Page 4", "Click an item row (not a category header) on Page 4 first, then click '📌 Track Selected on Page 1'.")
            return
        cat = item.get("category", "")
        default_sec = "cp" if "Currencies" in cat else ("rema" if "Weapons" in cat else "jse")
        self._open_add_gear_to_tracker_dialog(
            prefill_name=item.get("name", ""),
            prefill_bag=item.get("locations_str", "Inventory"),
            prefill_augments=item.get("augments", ""),
            prefill_count=item.get("total_count", 1),
            default_target=default_sec
        )

    def _open_page4_wiki(self, provider: str):
        item = self._get_selected_page4_item()
        if not item:
            messagebox.showinfo("Select an Item on Page 4", "Click an item row on Page 4 first, then click a Wiki button (or right-click any item).")
            return
        open_item_wiki(item.get("name", ""), provider)
        self._set_status(f"Opened {provider.upper()} for '{item.get('name', '')}'.")

    def _import_findall_or_csv_bags(self):
        path = filedialog.askopenfilename(
            title="Select a Windower findAll CSV/Lua export or GearSwap export file",
            filetypes=[("CSV / Lua / Text Files", "*.csv *.lua *.txt"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            imported = 0
            for ln in lines:
                parts = [p.strip().strip('"') for p in ln.split(",")]
                if len(parts) >= 3 and parts[0] and parts[0].lower() not in ("name", "item", "character"):
                    # Support CSV format: Character, Bag, Item, Count, Augments or Item, Count, Character, Bag
                    if parts[1].isdigit():
                        iname, cnt = parts[0], int(parts[1])
                        char_n = parts[2] if len(parts) > 2 else "Main"
                        bag_n = parts[3] if len(parts) > 3 else "Imported"
                        aug_n = parts[4] if len(parts) > 4 else ""
                    elif len(parts) >= 4 and parts[3].isdigit():
                        char_n, bag_n, iname, cnt = parts[0], parts[1], parts[2], int(parts[3])
                        aug_n = parts[4] if len(parts) > 4 else ""
                    else:
                        continue
                    self.bridge.live["inventory"].append({
                        "name": iname,
                        "count": cnt,
                        "character": char_n,
                        "bag": bag_n,
                        "augments": aug_n
                    })
                    imported += 1
            self._refresh_trees()
            self._set_status(f"Imported {imported} inventory entries from {os.path.basename(path)}!")
        except Exception as e:
            self._set_status(f"Error importing bag file: {e}")

    # --------------------------------------------------------------------------
    # TAB 5: ADDON & PLUGIN HUB
    # --------------------------------------------------------------------------
    def _build_tab5_addons(self):
        top = tk.Frame(self.tab5, bg="#0f172a", padx=10, pady=8)
        top.pack(fill=tk.X)
        tk.Label(
            top,
            text="⚙️ WINDOWER 4 ADDON SWITCHBOARD & DROP-IN CUSTOM MODULES (modules/*.py)",
            bg="#0f172a", fg="#38bdf8", font=("Consolas", 10, "bold")
        ).pack(side=tk.LEFT)

        tk.Button(
            top, text="🔄 Reload Custom Modules", bg="#0284c7", fg="#ffffff",
            relief=tk.FLAT, padx=10, pady=3, command=self._reload_custom_modules
        ).pack(side=tk.RIGHT, padx=4)
        tk.Button(
            top, text="⚡ Load / Unload Selected Addon", bg="#059669", fg="#ffffff",
            relief=tk.FLAT, padx=10, pady=3, command=self._toggle_selected_addon
        ).pack(side=tk.RIGHT, padx=4)
        tk.Button(
            top, text="📥 Install Updated VanadielNexus.lua (F10 Removed)", bg="#4f46e5", fg="#ffffff",
            relief=tk.FLAT, padx=10, pady=3, command=self._install_updated_addon_lua
        ).pack(side=tk.RIGHT, padx=4)

        ad_cols = ("name", "category", "status", "desc")
        self.tree_addons = ttk.Treeview(self.tab5, columns=ad_cols, show="headings", height=15)
        self.tree_addons.heading("name", text="Addon / Module Name")
        self.tree_addons.heading("category", text="Type / Category")
        self.tree_addons.heading("status", text="Status")
        self.tree_addons.heading("desc", text="Description")
        self.tree_addons.column("name", width=230, anchor="w")
        self.tree_addons.column("category", width=160, anchor="w")
        self.tree_addons.column("status", width=110, anchor="center")
        self.tree_addons.column("desc", width=540, anchor="w")
        self.tree_addons.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        self.windower_addons = [
            {"name": "GearSwap", "category": "Windower Addon", "loaded": True, "desc": "Equipment swapping engine (synced with Vana'diel Nexus Haste/DW)."},
            {"name": "superwarp", "category": "Windower Addon", "loaded": True, "desc": "Home Point, Survival Guide, Waypoint, and Sortie/Odyssey travel automation."},
            {"name": "Treasury", "category": "Windower Addon", "loaded": True, "desc": "Auto-lot, auto-pass, and auto-drop treasure pool manager."},
            {"name": "findAll", "category": "Windower Addon", "loaded": True, "desc": "Searches items across all characters' bags."},
            {"name": "itemizer", "category": "Windower Addon", "loaded": True, "desc": "Moves items between bags via //get and //put commands."},
            {"name": "organizer", "category": "Windower Addon", "loaded": True, "desc": "Packs gear for your active job in Mog House."},
            {"name": "Omen", "category": "Windower Addon", "loaded": True, "desc": "Tracks Omen floor objectives and bonus timers."},
            {"name": "azureSets", "category": "Windower Addon", "loaded": True, "desc": "Saves and loads Blue Magic spell sets."}
        ]

    def _install_updated_addon_lua(self):
        target_dir = DEFAULT_ADDON_DIR
        if not os.path.isdir(DEFAULT_WINDOWER_DIR):
            picked = filedialog.askdirectory(title="Select Your Windower4 Folder (or Windower4/addons/VanadielNexus Folder)")
            if not picked:
                return
            if os.path.basename(os.path.normpath(picked)).lower() == "vanadielnexus":
                target_dir = picked
            elif os.path.basename(os.path.normpath(picked)).lower() == "addons":
                target_dir = os.path.join(picked, "VanadielNexus")
            else:
                target_dir = os.path.join(picked, "addons", "VanadielNexus")
            set_windower_dir(os.path.dirname(os.path.dirname(os.path.normpath(target_dir))))
            self.bridge.windower_path = DEFAULT_WINDOWER_DIR
        try:
            os.makedirs(target_dir, exist_ok=True)
            dst_lua = os.path.join(target_dir, "VanadielNexus.lua")
            with open(dst_lua, "w", encoding="utf-8") as f:
                f.write(VANADIEL_NEXUS_LUA_CODE)
            messagebox.showinfo(
                "Updated VanadielNexus.lua Installed!",
                f"Successfully installed v{APP_VERSION} VanadielNexus.lua to:\n\n{dst_lua}\n\n"
                "In FFXI, type: //lua r vanadielnexus"
            )
            self._set_status(f"Installed updated VanadielNexus.lua (F10 removed) to {dst_lua}")
        except Exception as e:
            self._set_status(f"Error installing VanadielNexus.lua: {e}")

    # --------------------------------------------------------------------------
    # TAB 6: HOTKEY & CONFLICT MANAGER (ALL SYSTEMS)
    # --------------------------------------------------------------------------
    def _build_tab6_hotkeys(self):
        top = tk.Frame(self.tab6, bg="#0f172a", padx=10, pady=6)
        top.pack(fill=tk.X)

        tk.Label(
            top,
            text="⌨️ UNIFIED HOTKEY & CONFLICT MANAGER (Game Base • Windower init.txt • GearSwap Lua • Addons/Plugins)",
            bg="#0f172a", fg="#38bdf8", font=("Consolas", 10, "bold")
        ).pack(side=tk.LEFT)

        tk.Button(
            top, text="📂 Set Windower4 Folder & Re-Scan", bg="#0284c7", fg="#ffffff",
            relief=tk.FLAT, padx=10, pady=2, font=("Segoe UI", 8, "bold"),
            command=self._choose_windower_and_rescan_hotkeys
        ).pack(side=tk.RIGHT, padx=3)

        # Filter & Action Strip
        fstrip = tk.Frame(self.tab6, bg="#1e293b", padx=10, pady=6, highlightbackground="#334155", highlightthickness=1)
        fstrip.pack(fill=tk.X, padx=10, pady=(0, 6))

        tk.Label(fstrip, text="🔍 Filter Key/Action:", bg="#1e293b", fg="#38bdf8", font=("Consolas", 9, "bold")).pack(side=tk.LEFT)
        self.hk_search_var = tk.StringVar()
        self.hk_search_var.trace_add("write", lambda *_: self._refresh_hotkey_tree())
        tk.Entry(fstrip, textvariable=self.hk_search_var, bg="#0f172a", fg="#ffffff", insertbackground="#ffffff", relief=tk.FLAT, width=16).pack(side=tk.LEFT, padx=(4, 10))

        tk.Label(fstrip, text="System:", bg="#1e293b", fg="#94a3b8").pack(side=tk.LEFT)
        self.hk_sys_var = tk.StringVar(value="All Systems")
        self.hk_sys_combo = ttk.Combobox(
            fstrip, textvariable=self.hk_sys_var,
            values=["All Systems", "Windower init.txt", "GearSwap Lua", "FFXI Base Game", "Windower Core"],
            width=18, state="readonly"
        )
        self.hk_sys_combo.pack(side=tk.LEFT, padx=(4, 10))
        self.hk_sys_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_hotkey_tree())

        self.hk_conflicts_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            fstrip, text="⚠️ Show Conflicts Only", variable=self.hk_conflicts_only_var,
            command=self._refresh_hotkey_tree,
            bg="#1e293b", fg="#fbbf24", selectcolor="#0f172a", activebackground="#1e293b",
            font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            fstrip, text="🚫 Comment Out / Unbind Selected Conflict", bg="#dc2626", fg="#ffffff",
            relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"),
            command=self._disable_selected_hotkey_bind
        ).pack(side=tk.RIGHT, padx=3)

        tk.Button(
            fstrip, text="✏️ Rebind Selected Key...", bg="#059669", fg="#ffffff",
            relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"),
            command=self._rebind_selected_hotkey_dialog
        ).pack(side=tk.RIGHT, padx=3)

        tk.Button(
            fstrip, text="📂 Open Config File in Editor", bg="#4f46e5", fg="#ffffff",
            relief=tk.FLAT, padx=9, pady=2, font=("Segoe UI", 8, "bold"),
            command=self._open_selected_hotkey_file
        ).pack(side=tk.RIGHT, padx=3)

        # Hotkey Treeview
        hk_frame = tk.Frame(self.tab6, bg="#0f172a", padx=10)
        hk_frame.pack(fill=tk.BOTH, expand=True)

        hk_cols = ("norm_key", "raw_key", "status", "system", "action", "source_file")
        self.tree_hk = ttk.Treeview(hk_frame, columns=hk_cols, show="headings", height=11)
        for c, h, w, anc in [
            ("norm_key", "Normalized Key", 110, "center"),
            ("raw_key", "Config Syntax", 95, "center"),
            ("status", "Conflict Status", 155, "center"),
            ("system", "System Layer", 185, "w"),
            ("action", "Bound Command / Action", 275, "w"),
            ("source_file", "Config File / Location", 290, "w")
        ]:
            self.tree_hk.heading(c, text=h)
            self.tree_hk.column(c, width=w, anchor=anc)

        hk_scroll = ttk.Scrollbar(hk_frame, orient=tk.VERTICAL, command=self.tree_hk.yview)
        self.tree_hk.configure(yscrollcommand=hk_scroll.set)
        self.tree_hk.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hk_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_hk.tag_configure("conflict_row", background="#2b161b", foreground="#fca5a5")
        self.tree_hk.tag_configure("ok_row", background="#0f172a", foreground="#e2e8f0")
        self.tree_hk.bind("<<TreeviewSelect>>", self._on_hotkey_select)

        # Bottom Guide Panel: Explains exact config file path, line number, and how to fix conflicts
        guide_box = tk.Frame(self.tab6, bg="#1e293b", padx=12, pady=8, highlightbackground="#0284c7", highlightthickness=1)
        guide_box.pack(fill=tk.X, padx=10, pady=6)

        tk.Label(
            guide_box,
            text="📍 WHERE TO FIND & HOW TO CHANGE / FIX SELECTED HOTKEY:",
            bg="#1e293b", fg="#fbbf24", font=("Consolas", 9, "bold")
        ).pack(anchor="w")

        self.lbl_hk_detail = tk.Label(
            guide_box,
            text=(
                "Click any hotkey above to see its exact config file location, competing systems, and step-by-step fix instructions.\n"
                "• Note: Vana'diel Nexus v1.2 has REMOVED its F10 hotkey so your F8–F12 (+ Ctrl/Alt) GearSwap binds have zero overlay interference!"
            ),
            bg="#1e293b", fg="#e2e8f0", justify=tk.LEFT, anchor="w", wraplength=1100, font=("Segoe UI", 9)
        )
        self.lbl_hk_detail.pack(fill=tk.X, pady=(4, 0))

        self._rescan_hotkeys()

    def _rescan_hotkeys(self):
        self._hotkey_entries = scan_all_hotkeys_and_conflicts(self.bridge.windower_path)
        self._refresh_hotkey_tree()

    def _choose_windower_and_rescan_hotkeys(self):
        picked = filedialog.askdirectory(title="Select Your Windower4 Root Folder (e.g. C:/Windower4)")
        if picked:
            set_windower_dir(picked)
            self.bridge.windower_path = picked
        self._rescan_hotkeys()
        conflicts = sum(1 for e in self._hotkey_entries if e.get("conflict"))
        self._set_status(f"Scanned hotkeys in {self.bridge.windower_path}: {len(self._hotkey_entries)} binds found ({conflicts} conflicting entries flagged).")

    def _refresh_hotkey_tree(self):
        if not hasattr(self, "tree_hk"):
            return
        self.tree_hk.delete(*self.tree_hk.get_children())
        q = self.hk_search_var.get().lower().strip()
        sys_f = self.hk_sys_var.get()
        conf_only = self.hk_conflicts_only_var.get()

        self._hk_vis_map = {}
        vis_i = 0
        for idx, e in enumerate(self._hotkey_entries):
            if conf_only and not e.get("conflict"):
                continue
            if sys_f != "All Systems" and sys_f.lower() not in e.get("system", "").lower():
                continue
            if q and not (
                q in e.get("norm_key", "").lower()
                or q in e.get("raw_key", "").lower()
                or q in e.get("action", "").lower()
                or q in e.get("system", "").lower()
            ):
                continue

            tag = "conflict_row" if e.get("conflict") else "ok_row"
            loc_str = f"{e['source_file']} (Line {e['line_num']})" if e.get("line_num") else e["source_file"]
            self.tree_hk.insert("", tk.END, iid=str(vis_i), values=(
                e["norm_key"], e["raw_key"], e["status_label"], e["system"], e["action"], loc_str
            ), tags=(tag,))
            self._hk_vis_map[vis_i] = idx
            vis_i += 1

    def _get_selected_hotkey_entry(self):
        sel = self.tree_hk.selection()
        if not sel:
            return None
        vis_i = int(sel[0])
        real_i = self._hk_vis_map.get(vis_i)
        if real_i is not None and 0 <= real_i < len(self._hotkey_entries):
            return self._hotkey_entries[real_i]
        return None

    def _on_hotkey_select(self, _event=None):
        e = self._get_selected_hotkey_entry()
        if not e:
            return
        loc_str = f"{e['source_file']} (Line {e['line_num']})" if e.get("line_num") else e["source_file"]
        win_unbind = f"//unbind {to_windower_bind_key(e['norm_key'])}"
        txt = (
            f"• Key: {e['norm_key']} (Syntax: {e['raw_key']})   |   System: {e['system']}   |   Config Location: {loc_str}\n"
            f"• Competing Systems on {e['norm_key']}: {e.get('conflict_summary', 'None')}\n"
            f"• How to Change / Resolve: {e.get('how_to_fix', '')}   (Live In-Game Unbind Command: {win_unbind})"
        )
        self.lbl_hk_detail.configure(text=txt)

    def _open_selected_hotkey_file(self):
        e = self._get_selected_hotkey_entry()
        if not e:
            messagebox.showinfo("Select a Hotkey Row", "Select a hotkey row first to open its config file.")
            return
        fpath = e.get("source_file", "")
        if os.path.isfile(fpath):
            try:
                if sys.platform == "win32":
                    os.startfile(fpath)
                else:
                    subprocess.Popen(["xdg-open", fpath])
                self._set_status(f"Opened {fpath} in system editor.")
            except Exception as ex:
                self._set_status(f"Could not open file: {ex}")
        else:
            messagebox.showinfo(
                "Where to Find This Config",
                f"Config Location:\n{fpath}\n\nHow to Change:\n{e.get('how_to_fix', '')}"
            )

    def _disable_selected_hotkey_bind(self):
        e = self._get_selected_hotkey_entry()
        if not e:
            messagebox.showinfo("Select a Hotkey Row", "Select a hotkey row first to unbind or comment it out.")
            return
        fpath = e.get("source_file", "")
        lno = int(e.get("line_num", 0) or 0)
        rk = e.get("raw_key", "")
        w_key = to_windower_bind_key(e["norm_key"])

        if not messagebox.askyesno(
            "Confirm Unbind / Comment Out",
            f"Do you want to unbind '{e['norm_key']}' ({e['action']}) from {e['system']}?\n\n"
            f"• Sends live command '//unbind {w_key}' to Windower 4\n"
            f"• Comments out Line {lno} in {fpath} (if file is present on disk)"
        ):
            return

        # 1. Send live unbind command to Windower 4 over UDP
        self.bridge.send_udp_command(f"CMD|unbind {w_key}")

        # 2. Comment out in file if editable on disk
        file_modified = False
        if os.path.isfile(fpath) and lno > 0:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                if 1 <= lno <= len(lines):
                    orig = lines[lno - 1]
                    if fpath.lower().endswith(".lua"):
                        lines[lno - 1] = f"-- [Disabled by VanadielNexus Hotkey Manager] {orig}"
                    else:
                        lines[lno - 1] = f"// [Disabled by VanadielNexus Hotkey Manager] {orig}"
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.writelines(lines)
                    file_modified = True
            except Exception as ex:
                self._set_status(f"Error updating {fpath}: {ex}")

        # Remove from current in-memory list and recompute conflicts
        if not file_modified:
            self._hotkey_entries = [x for x in self._hotkey_entries if x is not e]
            # Re-evaluate conflict flags
            by_norm = {}
            for x in self._hotkey_entries:
                by_norm.setdefault(x["norm_key"], []).append(x)
            for x in self._hotkey_entries:
                grp = by_norm.get(x["norm_key"], [])
                ds = {g["system"] for g in grp}
                x["conflict"] = (len(grp) > 1 and len(ds) > 1)
                x["status_label"] = f"⚠️ CONFLICT ({len(grp)} systems)" if x["conflict"] else "✅ OK (No Conflict)"
            self._refresh_hotkey_tree()
        else:
            self._rescan_hotkeys()

        self._set_status(f"Unbound {e['norm_key']} ({rk}) and updated config!")

    def _rebind_selected_hotkey_dialog(self):
        e = self._get_selected_hotkey_entry()
        if not e:
            messagebox.showinfo("Select a Hotkey Row", "Select a hotkey row first to rebind it.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Rebind Hotkey — {e['norm_key']} ({e['system']})")
        win.geometry("460x250")
        win.configure(bg="#0f172a")
        win.attributes("-topmost", True)

        tk.Label(win, text=f"Current Key: {e['norm_key']}  ->  {e['action']}", bg="#0f172a", fg="#38bdf8", font=("Consolas", 9, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        tk.Label(win, text="Enter New Key Combo (e.g. Ctrl+F7, Alt+F7, Numpad0, ^numpad1):", bg="#0f172a", fg="#94a3b8").pack(anchor="w", padx=14, pady=(6, 2))
        e_newk = tk.Entry(win, bg="#1e293b", fg="#ffffff", insertbackground="#ffffff", width=36)
        e_newk.insert(0, "Ctrl+F7")
        e_newk.pack(anchor="w", padx=14, pady=4)

        tk.Label(win, text="Command / Action:", bg="#0f172a", fg="#94a3b8").pack(anchor="w", padx=14, pady=(6, 2))
        e_cmd = tk.Entry(win, bg="#1e293b", fg="#ffffff", insertbackground="#ffffff", width=48)
        e_cmd.insert(0, e["action"])
        e_cmd.pack(anchor="w", padx=14, pady=4)

        def _apply_rebind():
            new_norm = normalize_hotkey_string(e_newk.get().strip())
            new_cmd = e_cmd.get().strip()
            if not new_norm or not new_cmd:
                return
            old_wkey = to_windower_bind_key(e["norm_key"])
            new_wkey = to_windower_bind_key(new_norm)

            # Send live unbind + bind to Windower 4
            self.bridge.send_udp_command(f"CMD|unbind {old_wkey}")
            self.bridge.send_udp_command(f"CMD|bind {new_wkey} {new_cmd}")

            # Update file if on disk
            fpath = e.get("source_file", "")
            lno = int(e.get("line_num", 0) or 0)
            if os.path.isfile(fpath) and lno > 0:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    if 1 <= lno <= len(lines):
                        if fpath.lower().endswith(".txt"):
                            lines[lno - 1] = f"bind {new_wkey} {new_cmd}\n"
                        elif fpath.lower().endswith(".lua"):
                            lines[lno - 1] = re.sub(
                                r"bind\s+\S+\s+[^'\"]+",
                                f"bind {new_wkey} {new_cmd}",
                                lines[lno - 1],
                                flags=re.IGNORECASE
                            )
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.writelines(lines)
                except Exception:
                    pass

            e["raw_key"] = new_wkey
            e["norm_key"] = new_norm
            e["action"] = new_cmd
            # Re-evaluate conflict flags
            by_norm = {}
            for x in self._hotkey_entries:
                by_norm.setdefault(x["norm_key"], []).append(x)
            for x in self._hotkey_entries:
                grp = by_norm.get(x["norm_key"], [])
                ds = {g["system"] for g in grp}
                x["conflict"] = (len(grp) > 1 and len(ds) > 1)
                x["status_label"] = f"⚠️ CONFLICT ({len(grp)} systems)" if x["conflict"] else "✅ OK (No Conflict)"
            self._refresh_hotkey_tree()
            win.destroy()
            self._set_status(f"Rebound {old_wkey} -> {new_wkey} ({new_cmd})!")

        btn_f = tk.Frame(win, bg="#0f172a", pady=12)
        btn_f.pack(fill=tk.X, padx=14)
        tk.Button(btn_f, text="✓ Apply Rebind", bg="#059669", fg="#ffffff", relief=tk.FLAT, padx=14, pady=5, font=("Segoe UI", 9, "bold"), command=_apply_rebind).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_f, text="Cancel", bg="#334155", fg="#e2e8f0", relief=tk.FLAT, padx=12, pady=5, command=win.destroy).pack(side=tk.LEFT)

    # --------------------------------------------------------------------------
    # COMPACT IN-GAME HUD FRAME
    # --------------------------------------------------------------------------
    def _build_compact_hud_frame(self):
        hdr = tk.Frame(self.hud_frame, bg="#0f172a", padx=8, pady=4, highlightbackground="#0284c7", highlightthickness=1)
        hdr.pack(fill=tk.X, pady=(0, 6))
        hdr.bind("<ButtonPress-1>", self._start_move)
        hdr.bind("<B1-Motion>", self._on_move)
        hdr.bind("<Double-Button-1>", lambda _e: self.toggle_hud_mode())

        self.lbl_hud_summary = tk.Label(
            hdr,
            text="⚔️ BLU/WAR • Acc/Atk: 1482/2190 • MaxHaste (0% DW) • DT: -50%",
            bg="#0f172a", fg="#38bdf8", font=("Consolas", 9, "bold")
        )
        self.lbl_hud_summary.pack(side=tk.LEFT)
        self.lbl_hud_summary.bind("<ButtonPress-1>", self._start_move)
        self.lbl_hud_summary.bind("<B1-Motion>", self._on_move)
        self.lbl_hud_summary.bind("<Double-Button-1>", lambda _e: self.toggle_hud_mode())

        tk.Button(
            hdr, text="⊞ Expand Full Window", bg="#0284c7", fg="#ffffff",
            activebackground="#38bdf8", activeforeground="#000000",
            relief=tk.FLAT, padx=8, pady=2, font=("Segoe UI", 8, "bold"),
            command=self.toggle_hud_mode
        ).pack(side=tk.RIGHT, padx=(6, 0))

        mote_strip = tk.Frame(self.hud_frame, bg="#080c14")
        mote_strip.pack(fill=tk.X, pady=(0, 6))
        self.hud_mote_btns = {}
        for mk in ("OffenseMode", "HybridMode", "WeaponskillMode", "WeaponSet"):
            b = tk.Button(
                mote_strip, text=f"{mk[:3]}: Normal",
                bg="#1e293b", fg="#fbbf24", relief=tk.FLAT, padx=8, pady=3,
                font=("Consolas", 8, "bold"),
                command=lambda k=mk: self._cycle_mote_mode(k)
            )
            b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            self.hud_mote_btns[mk] = b

        self.hud_list_frame = tk.Frame(self.hud_frame, bg="#0f172a", padx=8, pady=6, highlightbackground="#334155", highlightthickness=1)
        self.hud_list_frame.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # WINDOW & ACTION HANDLERS
    # --------------------------------------------------------------------------
    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_move(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _on_alpha_change(self, val):
        try:
            self.root.attributes("-alpha", float(val) / 100.0)
        except Exception:
            pass

    def _toggle_noactivate(self):
        self.bridge.no_activate_enabled = not self.bridge.no_activate_enabled
        hwnd = self.root.winfo_id()
        set_window_noactivate(hwnd, self.bridge.no_activate_enabled)
        if self.bridge.no_activate_enabled:
            self.btn_noactivate.configure(text="🔒 Focus Lock: No-Activate ON", bg="#059669", fg="#ffffff")
            self._set_status("Win32 WS_EX_NOACTIVATE enabled: Clicking overlay buttons will not steal focus from FFXI.")
        else:
            self.btn_noactivate.configure(text="🔓 Focus: Normal", bg="#1e293b", fg="#cbd5e1")
            self._set_status("Normal window focus enabled (allows typing in search boxes).")

    # --------------------------------------------------------------------------
    # SELF-UPDATE (replaces only the .exe; data/ and modules/ are never touched)
    # --------------------------------------------------------------------------
    def _check_for_updates(self, manual: bool = False):
        def _worker():
            try:
                req = urllib.request.Request(
                    f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                    headers={"Accept": "application/vnd.github+json", "User-Agent": "VanadielNexus"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    release = json.load(resp)
                latest = release.get("tag_name", "").lstrip("vV")
                asset = next(
                    (a for a in release.get("assets", []) if a.get("name", "").lower() == "vanadielnexus.exe"),
                    None,
                )
                if asset and _version_tuple(latest) > _version_tuple(APP_VERSION):
                    url = asset["browser_download_url"]
                    notes = release.get("body", "") or ""
                    self.root.after(0, lambda: self._offer_update(latest, url, notes))
                elif manual:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Up to Date", f"You're on the latest version (v{APP_VERSION})."))
            except Exception as e:
                if manual:
                    err = str(e)
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Update Check Failed", f"Couldn't reach GitHub to check for updates:\n\n{err}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _offer_update(self, latest: str, url: str, notes: str):
        summary = notes.strip()[:600]
        if not messagebox.askyesno(
            "Update Available",
            f"Vana'diel Nexus v{latest} is available (you have v{APP_VERSION}).\n\n"
            f"{summary + chr(10) + chr(10) if summary else ''}"
            "Update now? The app will restart. Your tracker data is not touched."
        ):
            return
        self._set_status(f"Downloading v{latest}...")

        def _download_and_swap():
            exe_path = sys.executable
            new_path = exe_path + ".new"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "VanadielNexus"})
                with urllib.request.urlopen(req, timeout=120) as resp, open(new_path, "wb") as out:
                    shutil.copyfileobj(resp, out)
                if os.path.getsize(new_path) < 1_000_000:
                    raise RuntimeError("Downloaded file is too small; aborting update.")
                # Windows can't overwrite a running exe, so a tiny script waits for us to exit, swaps, relaunches
                cmd_path = os.path.join(os.path.dirname(exe_path), "_vn_update.cmd")
                with open(cmd_path, "w", encoding="utf-8") as f:
                    f.write(
                        "@echo off\r\n"
                        "set n=0\r\n"
                        ":retry\r\n"
                        f'move /Y "{new_path}" "{exe_path}" >nul 2>&1 && goto done\r\n'
                        "set /a n+=1\r\n"
                        "if %n% geq 60 goto done\r\n"
                        "timeout /t 1 /nobreak >nul\r\n"
                        "goto retry\r\n"
                        ":done\r\n"
                        f'start "" "{exe_path}"\r\n'
                        'del "%~f0"\r\n'
                    )
                subprocess.Popen(
                    ["cmd", "/c", cmd_path],
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    close_fds=True,
                )
                self.root.after(0, self.root.destroy)
            except Exception as e:
                try:
                    os.remove(new_path)
                except OSError:
                    pass
                err = str(e)
                self.root.after(0, lambda: messagebox.showerror("Update Failed", err))

        threading.Thread(target=_download_and_swap, daemon=True).start()

    def _build_standalone_exe(self):
        build_script = os.path.join(BASE_DIR, "build.ps1")
        if os.path.exists(build_script):
            subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", build_script])
            self._set_status("Started build.ps1 — VanadielNexus.exe will rebuild and relaunch when done.")
            return
        script_path = os.path.abspath(sys.argv[0])
        if messagebox.askyesno(
            "Build Standalone VanadielNexus.exe",
            "Compile vanadielnexus_overlay.py into a standalone VanadielNexus.exe using PyInstaller?\n\n"
            "(Requires Python & pip on Windows; takes ~30 seconds.)"
        ):
            self._set_status("Building VanadielNexus.exe in background via PyInstaller...")

            def _run_build():
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"], check=False)
                    subprocess.run([
                        sys.executable, "-m", "PyInstaller",
                        "--noconfirm", "--onefile", "--windowed",
                        "--name", "VanadielNexus", script_path
                    ], cwd=BASE_DIR, check=False)
                    dist_exe = os.path.join(BASE_DIR, "dist", "VanadielNexus.exe")
                    if os.path.exists(dist_exe):
                        shutil.copy2(dist_exe, os.path.join(BASE_DIR, "VanadielNexus.exe"))
                        self._set_status("SUCCESS: Built standalone VanadielNexus.exe in folder!")
                except Exception as e:
                    self._set_status(f"Build error: {e}")

            threading.Thread(target=_run_build, daemon=True).start()

    def toggle_hud_mode(self):
        self.bridge.compact_hud_mode = not self.bridge.compact_hud_mode
        if self.bridge.compact_hud_mode:
            self.toolbar_extra.pack_forget()
            self.lbl_bridge_status.configure(text="● HUD Active (Click ⊞ Expand, double-click bar, or //vn hud)")
            self.full_frame.pack_forget()
            self.hud_frame.pack(fill=tk.BOTH, expand=True)
            self.root.geometry("580x275")
            self.root.overrideredirect(True)
            self.btn_hud_mode.configure(text="⊞ Expand Full Window", bg="#0284c7")
            self._set_status("Compact HUD active — Click '⊞ Expand Full Window', double-click top bar, or type //vn hud in FFXI.")
        else:
            self.hud_frame.pack_forget()
            self.root.overrideredirect(False)
            self.toolbar_extra.pack(side=tk.LEFT, before=self.btn_noactivate)
            self.full_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
            self.root.geometry("1180x780")
            self.btn_hud_mode.configure(text="▣ Compact In-Game HUD", bg="#d97706")
            self._set_status("Expanded to Full 6-Module Assistant View.")
        self._refresh_trees()

    def _on_job_change(self, _event=None):
        job = self.job_var.get()
        self.bridge.live["main_job"] = job
        self._refresh_trees()
        self._set_status(f"Switched active job view to {job}.")

    def _send_and_notify(self, cmd: str, msg: str):
        self.bridge.send_udp_command(cmd)
        self._set_status(msg)

    def _set_status(self, text: str):
        self.status_bar.configure(text=text)

    def _increment_checkpoint(self, delta: int):
        sel = self.tree_cp.selection()
        cps = self.bridge.db.get("checkpoints", [])
        if not cps:
            return
        vis_idx = int(sel[0]) if sel else 0
        real_idx = self._cp_index_map.get(vis_idx, 0)
        if 0 <= real_idx < len(cps):
            cps[real_idx]["current"] = min(cps[real_idx]["target"], cps[real_idx]["current"] + delta)
            save_database(self.bridge.db)
            self._refresh_trees()
            self._set_status(f"Updated checkpoint '{cps[real_idx]['title']}': {cps[real_idx]['current']:,} / {cps[real_idx]['target']:,}")

    def _add_checkpoint_dialog(self):
        self._open_add_gear_to_tracker_dialog(default_target="cp")

    def _advance_jse_tier(self):
        sel = self.tree_jse.selection()
        if not sel:
            self._set_status("Select a JSE armor row first to advance its reforge tier.")
            return
        vis_idx = int(sel[0])
        mapping = self._jse_index_map.get(vis_idx)
        if not mapping:
            return
        job_key, row_idx = mapping
        rows = self.bridge.db.get("jse_by_job", {}).get(job_key, [])
        if 0 <= row_idx < len(rows):
            r = rows[row_idx]
            if r["tier"] == "Unowned" or r["tier"] == "Base":
                r["tier"] = "+1"
                r["mats"] = "Obtained +1! Ready to reforge to +2/+3."
            elif r["tier"] == "+1":
                r["tier"] = "+2"
                r["name"] = re.sub(r"\+1\b", "+2", r["name"]) if "+1" in r["name"] else (r["name"] + " +2")
                r["mats"] = "Reforged to +2! Farming +3 materials..."
            elif r["tier"] == "+2":
                r["tier"] = "+3"
                r["name"] = re.sub(r"\+2\b", "+3", r["name"]) if "+2" in r["name"] else (r["name"] + " +3")
                r["mats"] = "Reforged to +3!"
            elif r["tier"] == "+3":
                r["tier"] = "+4"
                r["name"] = re.sub(r"\+3\b", "+4", r["name"]) if "+3" in r["name"] else (r["name"] + " +4")
                r["mats"] = "Max Reforged (+4 Complete!)"
            save_database(self.bridge.db)
            self._refresh_trees()
            self._set_status(f"Upgraded {r['name']} ({job_key}) in JSE Tracker!")

    def _add_from_catalog(self):
        item_name = self.catalog_var.get().strip()
        if not item_name:
            self._set_status("Pick an item from the Quick-Add Catalog dropdown first.")
            return
        meta = self.bridge.db.get("catalog_db", {}).get(item_name, {})
        self._open_add_gear_to_tracker_dialog(
            prefill_name=item_name,
            prefill_bag=meta.get("zone", "Unowned"),
            prefill_augments=meta.get("obtainHow", ""),
            default_target="wishlist"
        )

    def _scan_local_gearswap_file(self):
        path = filedialog.askopenfilename(
            title="Select a Mote / GearSwap .lua File to Scan for Missing Gear",
            filetypes=[("Lua Files", "*.lua"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            owned_lower = {i["name"].lower() for i in self.bridge.live.get("inventory", []) if "name" in i}
            catalog = self.bridge.db.get("catalog_db", {})
            existing_wl = {w["name"].lower() for w in self.bridge.db.get("wishlist", [])}

            found_new = 0
            for quoted in re.findall(r'["\']([^"\'\r\n]+)["\']', content):
                for cname, meta in catalog.items():
                    if quoted.lower() == cname.lower() and cname.lower() not in owned_lower and cname.lower() not in existing_wl:
                        self.bridge.db.setdefault("wishlist", []).insert(0, {
                            "id": f"wl-local-{int(time.time())}-{found_new}",
                            "job": self.bridge.live.get("main_job", "All"),
                            "name": cname,
                            "slot": meta.get("slot", "Gear"),
                            "sourceType": meta.get("sourceType", "Endgame Drop"),
                            "zone": meta.get("zone", "See BG-Wiki"),
                            "obtainHow": meta.get("obtainHow", ""),
                            "costOrPop": meta.get("costOrPop", ""),
                            "detectedFrom": f"Missing in {os.path.basename(path)}",
                            "wikiUrl": meta.get("wikiUrl", "https://www.bg-wiki.com"),
                            "pinned": True
                        })
                        existing_wl.add(cname.lower())
                        found_new += 1
            save_database(self.bridge.db)
            self._refresh_trees()
            self._set_status(f"Scanned {os.path.basename(path)}: Added {found_new} unowned catalog items to Wishlist.")
        except Exception as e:
            self._set_status(f"Error scanning Lua file: {e}")

    def _mark_wishlist_obtained(self):
        sel = self.tree_wl.selection()
        wlist = self.bridge.db.get("wishlist", [])
        if not sel or not wlist:
            self._set_status("Select a Wishlist item first to remove it.")
            return
        vis_idx = int(sel[0])
        real_idx = self._wl_index_map.get(vis_idx, vis_idx)
        if 0 <= real_idx < len(wlist):
            target = wlist[real_idx]
            if messagebox.askyesno(
                "Confirm Wishlist Removal",
                f"Are you sure you want to remove '{target.get('name', '')}' from your Wishlist?"
            ):
                removed = wlist.pop(real_idx)
                save_database(self.bridge.db)
                self._refresh_trees()
                self._set_status(f"Removed '{removed['name']}' from Wishlist.")

    def _open_selected_wiki(self, provider: str = "bgwiki"):
        sel = self.tree_wl.selection()
        wlist = self.bridge.db.get("wishlist", [])
        vis_idx = int(sel[0]) if sel else 0
        real_idx = self._wl_index_map.get(vis_idx, vis_idx)
        if 0 <= real_idx < len(wlist):
            item_name = wlist[real_idx].get("name", "")
            custom_url = wlist[real_idx].get("wikiUrl", "")
            open_item_wiki(item_name, provider, custom_url)
            self._set_status(f"Opened {provider.upper()} for '{item_name}'.")

    def _cycle_mote_mode(self, mode_key: str):
        options_map = {
            "OffenseMode": ["Normal", "Acc", "SubtleBlow", "PDL"],
            "HybridMode": ["DT (-50%)", "Normal", "MEva"],
            "WeaponskillMode": ["PDL Cap", "Normal", "Acc"],
            "IdleMode": ["DT", "Normal", "Refresh"],
            "WeaponSet": ["Tizona", "Naegling", "Maxentius", "Chango"]
        }
        opts = options_map.get(mode_key, ["Normal"])
        cur = self.bridge.live["mote_modes"].get(mode_key, opts[0])
        nxt = opts[(opts.index(cur) + 1) % len(opts)] if cur in opts else opts[0]
        self.bridge.live["mote_modes"][mode_key] = nxt
        self.bridge.send_udp_command(f"GS|cycle {mode_key}")
        self._refresh_trees()
        self._set_status(f"Sent //gs c cycle {mode_key} -> {nxt}")

    def _install_mote_hook_wizard(self):
        gs_dir = filedialog.askdirectory(title="Select Your Windower4/addons/GearSwap Folder (or GearSwap/data Folder)")
        if not gs_dir:
            return
        if os.path.basename(os.path.normpath(gs_dir)).lower() == "data":
            data_dir = gs_dir
            gs_root = os.path.dirname(os.path.normpath(gs_dir))
        else:
            gs_root = gs_dir
            data_dir = os.path.join(gs_root, "data")

        libs_dir = os.path.join(gs_root, "libs")
        os.makedirs(libs_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        dst_libs_hook = os.path.join(libs_dir, "Mote_Nexus_Hook.lua")
        dst_data_hook = os.path.join(data_dir, "Mote_Nexus_Hook.lua")
        try:
            for hp in (dst_libs_hook, dst_data_hook):
                with open(hp, "w", encoding="utf-8") as f:
                    f.write(MOTE_HOOK_LUA_CODE)

            target_dirs = [data_dir]
            for entry in os.listdir(data_dir):
                sub_p = os.path.join(data_dir, entry)
                if os.path.isdir(sub_p) and entry.lower() not in ("libs", "beta_examples_and_information"):
                    target_dirs.append(sub_p)
                    with open(os.path.join(sub_p, "Mote_Nexus_Hook.lua"), "w", encoding="utf-8") as f:
                        f.write(MOTE_HOOK_LUA_CODE)

            hook_line = "include('Mote_Nexus_Hook.lua')"
            globals_updated = []
            for tdir in target_dirs:
                ug_path = os.path.join(tdir, "user-globals.lua")
                if os.path.exists(ug_path):
                    with open(ug_path, "r", encoding="utf-8", errors="ignore") as f:
                        ug_txt = f.read()
                    if "Mote_Nexus_Hook.lua" not in ug_txt:
                        with open(ug_path, "a", encoding="utf-8") as f:
                            f.write(f"\n-- Added by Vana'diel Nexus\n{hook_line}\n")
                        globals_updated.append(ug_path)
                else:
                    with open(ug_path, "w", encoding="utf-8") as f:
                        f.write(f"-- Auto-generated by Vana'diel Nexus\n{hook_line}\n")
                    globals_updated.append(ug_path)

            self._set_status("Installed Mote_Nexus_Hook.lua + user-globals.lua! Type //gs r in FFXI.")
            messagebox.showinfo(
                "Mote Auto-Hook Complete!",
                f"Successfully installed Mote_Nexus_Hook.lua into:\n• {dst_libs_hook}\n• {dst_data_hook}\n\n"
                f"Updated user-globals.lua ({len(globals_updated)} folder(s)).\n"
                "In FFXI, just type: //gs r"
            )
        except Exception as e:
            self._set_status(f"Hook install error: {e}")

    def _trigger_superwarp(self, dest: str):
        prefix = "sw hp all " if self.sendall_var.get() else "sw hp "
        cmd = prefix + dest
        self.bridge.send_udp_command(f"WARP|{cmd}")
        self._set_status(f"Sent Superwarp command: //{cmd}")

    def _reload_custom_modules(self):
        self.bridge.custom_modules = discover_custom_modules()
        self._refresh_trees()
        self._set_status(f"Reloaded modules/ directory: {len(self.bridge.custom_modules)} custom module(s) active.")

    def _toggle_selected_addon(self):
        sel = self.tree_addons.selection()
        if not sel:
            return
        item_id = sel[0]
        if item_id.startswith("wa-"):
            idx = int(item_id.split("-")[1])
            ad = self.windower_addons[idx]
            ad["loaded"] = not ad["loaded"]
            act = "load" if ad["loaded"] else "unload"
            self.bridge.send_udp_command(f"ADDON|{act}|{ad['name']}")
            self._refresh_trees()
            self._set_status(f"Sent //lua {act} {ad['name']} to Windower 4.")
        elif item_id.startswith("cm-"):
            idx = int(item_id.split("-")[1])
            mod_meta = self.bridge.custom_modules[idx]
            mod_ref = mod_meta.get("_module_ref")
            if mod_ref and hasattr(mod_ref, "on_action"):
                msg = mod_ref.on_action(self.bridge.send_udp_command)
                self._set_status(str(msg))

    # --------------------------------------------------------------------------
    # TREEVIEW REFRESH ENGINE
    # --------------------------------------------------------------------------
    def _refresh_trees(self):
        lv = self.bridge.live
        active_job = lv.get("main_job", "BLU")
        show_all_jobs = self.page1_all_jobs_var.get() if hasattr(self, "page1_all_jobs_var") else False

        conn_txt = "Connected (Live)" if self.bridge.udp_connected else "Standby / Sim Mode (Waiting for //lua load VanadielNexus)"
        self.lbl_bridge_status.configure(
            text=f"● Windower 4 UDP Bridge: {conn_txt} | {lv['player_name']} ({active_job}/{lv['sub_job']} ML.{lv['master_lvl']}) | Zone: {lv['zone_name']}"
        )

        # 1. Checkpoints
        self.tree_cp.delete(*self.tree_cp.get_children())
        self._cp_index_map.clear()
        vis_cp = 0
        for real_i, cp in enumerate(self.bridge.db.get("checkpoints", [])):
            cp_job = cp.get("job", "All")
            if not show_all_jobs and cp_job not in ("All", active_job) and f"({active_job})" not in cp.get("category", ""):
                # Still show if no checkpoints match active_job so table isn't blank
                pass
            pct = min(100, int((cp["current"] / max(1, cp["target"])) * 100))
            prog_str = f"{cp['current']:,} / {cp['target']:,} ({pct}%)"
            self.tree_cp.insert("", tk.END, iid=str(vis_cp), values=(cp_job, cp["category"], cp["title"], prog_str, cp["note"]))
            self._cp_index_map[vis_cp] = real_i
            vis_cp += 1

        # 2. JSE & Gear Upgrade Tracker
        self.tree_jse.delete(*self.tree_jse.get_children())
        self._jse_index_map.clear()
        vis_jse = 0
        jse_map = self.bridge.db.get("jse_by_job", {})
        jobs_to_show = sorted(jse_map.keys()) if show_all_jobs else [active_job]
        for jkey in jobs_to_show:
            for r_i, row in enumerate(jse_map.get(jkey, [])):
                self.tree_jse.insert("", tk.END, iid=str(vis_jse), values=(
                    jkey, row.get("set", "JSE"), row.get("slot", ""), row.get("name", ""),
                    row.get("tier", ""), row.get("location", ""), row.get("mats", "")
                ))
                self._jse_index_map[vis_jse] = (jkey, r_i)
                vis_jse += 1

        # 3. REMA & Prime Weapons
        self.tree_rema.delete(*self.tree_rema.get_children())
        self._rema_index_map.clear()
        vis_rema = 0
        for real_i, w in enumerate(self.bridge.db.get("rema_weapons", [])):
            w_job = w.get("job", "All")
            if not show_all_jobs and w_job not in ("All", active_job):
                continue
            self.tree_rema.insert("", tk.END, iid=str(vis_rema), values=(
                w["name"], f"{w['type']} ({w_job})", w["stage"], w["detail"]
            ))
            self._rema_index_map[vis_rema] = real_i
            vis_rema += 1
        # If filtering by active_job hid all REMA weapons, show all so panel is helpful
        if vis_rema == 0:
            for real_i, w in enumerate(self.bridge.db.get("rema_weapons", [])):
                w_job = w.get("job", "All")
                self.tree_rema.insert("", tk.END, iid=str(vis_rema), values=(
                    w["name"], f"{w['type']} ({w_job})", w["stage"], w["detail"]
                ))
                self._rema_index_map[vis_rema] = real_i
                vis_rema += 1

        # 4. Page 2 Wishlist
        self.tree_wl.delete(*self.tree_wl.get_children())
        self._wl_index_map.clear()
        for i, w in enumerate(self.bridge.db.get("wishlist", [])):
            self.tree_wl.insert("", tk.END, iid=str(i), values=(
                w.get("job", "All"), w["name"], w["slot"], w["sourceType"], w["zone"], w["costOrPop"], w["obtainHow"]
            ))
            self._wl_index_map[i] = i

        # 5. Page 3 Live Stats & Equipped Gear
        self.lbl_stat_cards["acc_atk"].configure(text=f"{lv['accuracy_est']:,} / {lv['attack']:,}")
        self.lbl_stat_cards["haste"].configure(text=f"{lv['gear_haste']:.1f}% / {lv['magic_haste']:.2f}%")
        self.lbl_stat_cards["dw"].configure(text=f"{lv['haste_group']} ({lv['dw_needed']}% DW)")
        for mk, btn in self.mote_buttons.items():
            val = lv["mote_modes"].get(mk, "Normal")
            btn.configure(text=f"{mk}: {val} ↻")

        self.tree_eq.delete(*self.tree_eq.get_children())
        for eq in lv.get("equipped", []):
            self.tree_eq.insert("", tk.END, values=(eq.get("slot", ""), eq.get("name", ""), eq.get("augments", "")))

        # 6. Page 4 Inventory, Categorization, Consolidation & Scattered-Bag Detection
        self.tree_inv.delete(*self.tree_inv.get_children())
        self._inv_item_map.clear()

        consolidated = consolidate_inventory_items(lv.get("inventory", []))

        # Update character filter dropdown dynamically
        all_chars = sorted({c for item in consolidated for c in item["characters"]})
        if hasattr(self, "inv_char_combo"):
            self.inv_char_combo.configure(values=["All Characters"] + all_chars)

        q = self.inv_search_var.get().lower().strip()
        cat_filter = self.inv_cat_var.get()
        char_filter = self.inv_char_var.get()
        bag_filter = self.inv_bag_var.get()
        scattered_only = self.inv_scattered_only_var.get()
        mats_only = self.inv_mats_only_var.get()
        gear_only = self.inv_gear_only_var.get()
        group_by_cat = self.inv_group_by_cat_var.get()

        filtered_items = []
        for item in consolidated:
            if cat_filter != "All Categories" and item["category"] != cat_filter:
                continue
            if char_filter != "All Characters" and char_filter not in item["characters"]:
                continue
            if bag_filter != "All Bags" and not any(bag_filter.lower() in b.lower() for b in item["bags"]):
                continue
            if scattered_only and not item["scattered"]:
                continue
            if mats_only and "Currencies" not in item["category"]:
                continue
            if gear_only and item["category"] in ("💎 Upgrade Currencies & REMA / JSE Mats", "🧪 Consumables, Food & Medicines", "📦 General, Pop Items & Storage"):
                continue
            if q and not (
                q in item["name"].lower()
                or q in item["augments"].lower()
                or q in item["locations_str"].lower()
                or q in item["category"].lower()
            ):
                continue
            filtered_items.append(item)

        scattered_total = sum(1 for x in filtered_items if x["scattered"])
        self.lbl_inv_summary.configure(
            text=f"Showing {len(filtered_items)} distinct entries ({scattered_total} ⚠️ scattered across bags)"
        )

        if group_by_cat:
            by_cat = {}
            for it in filtered_items:
                by_cat.setdefault(it["category"], []).append(it)

            row_seq = 0
            for cat_name in ITEM_CATEGORIES:
                cat_items = by_cat.get(cat_name, [])
                if not cat_items:
                    continue
                total_pieces = sum(x["total_count"] for x in cat_items)
                scat_in_cat = sum(1 for x in cat_items if x["scattered"])
                scat_txt = f"⚠️ {scat_in_cat} Scattered" if scat_in_cat > 0 else "✅ Clean"
                hdr_iid = f"cat-{row_seq}"
                row_seq += 1
                self.tree_inv.insert(
                    "", tk.END, iid=hdr_iid, open=True,
                    values=(
                        f"📂 {cat_name} ({len(cat_items)} items)",
                        f"{total_pieces:,}",
                        scat_txt,
                        "Click +/- or double-click to collapse/expand category",
                        ""
                    ),
                    tags=("cat_header",)
                )
                for it in cat_items:
                    iid = f"itm-{row_seq}"
                    row_seq += 1
                    rtag = "scattered_row" if it["scattered"] else "normal_row"
                    self.tree_inv.insert(
                        "", tk.END, iid=iid,
                        values=(
                            f"    • {it['name']}",
                            f"{it['total_count']:,}",
                            it["scattered_badge"],
                            it["locations_str"],
                            it["augments"]
                        ),
                        tags=(rtag,)
                    )
                    self._inv_item_map[iid] = it
        else:
            for idx, it in enumerate(filtered_items):
                iid = f"flat-{idx}"
                rtag = "scattered_row" if it["scattered"] else "normal_row"
                self.tree_inv.insert(
                    "", tk.END, iid=iid,
                    values=(
                        it["name"],
                        f"{it['total_count']:,}",
                        it["scattered_badge"],
                        it["locations_str"],
                        it["augments"]
                    ),
                    tags=(rtag,)
                )
                self._inv_item_map[iid] = it

        # 7. Page 5 Addons
        self.tree_addons.delete(*self.tree_addons.get_children())
        for i, ad in enumerate(self.windower_addons):
            st_txt = "● Loaded" if ad["loaded"] else "○ Unloaded"
            self.tree_addons.insert("", tk.END, iid=f"wa-{i}", values=(ad["name"], ad["category"], st_txt, ad["desc"]))
        for i, cm in enumerate(self.bridge.custom_modules):
            self.tree_addons.insert("", tk.END, iid=f"cm-{i}", values=(
                cm.get("name", "Custom Module"), cm.get("category", "modules/"), "● Active Plugin", cm.get("desc", "")
            ))

        # 8. Compact HUD
        self.lbl_hud_summary.configure(
            text=f"⚔️ {active_job}/{lv['sub_job']} • Acc/Atk: {lv['accuracy_est']}/{lv['attack']} • {lv['haste_group']} ({lv['dw_needed']}% DW)"
        )
        for mk, b in self.hud_mote_btns.items():
            b.configure(text=f"{mk[:3]}: {lv['mote_modes'].get(mk, 'Normal')}")

        for child in self.hud_list_frame.winfo_children():
            child.destroy()
        for cp in self.bridge.db.get("checkpoints", [])[:3]:
            pct = min(100, int((cp["current"] / max(1, cp["target"])) * 100))
            row = tk.Frame(self.hud_list_frame, bg="#0f172a")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"📌 {cp['title']}", bg="#0f172a", fg="#e2e8f0", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
            tk.Label(row, text=f"{cp['current']:,}/{cp['target']:,} ({pct}%)", bg="#0f172a", fg="#fbbf24", font=("Consolas", 8, "bold")).pack(side=tk.RIGHT)

    def _schedule_refresh(self):
        if getattr(self.bridge, "hud_toggle_requested", False):
            self.bridge.hud_toggle_requested = False
            self.toggle_hud_mode()
        if self.bridge.ui_dirty:
            self.bridge.ui_dirty = False
            self._refresh_trees()
        self.root.after(250, self._schedule_refresh)


# ==============================================================================
# BACKGROUND THREAD: UDP LISTENER
# ==============================================================================
def start_udp_listener(bridge: NexusBridgeState):
    def _listen():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((UDP_HOST, UDP_LISTEN_PORT))
        except Exception as e:
            print(f"[UDP Bind Info] Port {UDP_LISTEN_PORT} busy or unavailable: {e}")
            return
        while True:
            try:
                data, _ = sock.recvfrom(65535)
                payload = json.loads(data.decode("utf-8", errors="ignore"))
                if isinstance(payload, dict):
                    if payload.get("type") == "STATE_UPDATE":
                        bridge.update_from_lua_payload(payload)
                    elif payload.get("type") == "TOGGLE_HUD":
                        bridge.hud_toggle_requested = True
            except Exception as e:
                print(f"[UDP Receive Warn] {e}")

    t = threading.Thread(target=_listen, daemon=True)
    t.start()


def main():
    ensure_directories_and_assets()
    bridge = NexusBridgeState()
    start_udp_listener(bridge)

    root = tk.Tk()
    app = VanadielNexusDesktopApp(root, bridge)
    root.mainloop()


if __name__ == "__main__":
    main()