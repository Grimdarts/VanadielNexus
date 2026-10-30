-- Vana'diel Nexus — 1-Click Mote-Include GearSwap Auto-Hook (Mote_Nexus_Hook.lua)
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

local _orig_display_current_state = display_current_state
function display_current_state(eventArgs)
    if _orig_display_current_state then _orig_display_current_state(eventArgs) end
    nexus_push_mote_states()
end

coroutine.schedule(nexus_push_mote_states, 2)
