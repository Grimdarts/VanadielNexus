-- Repair the legacy missing helper/dispatch by reusing Mote's existing filters,
-- selection and post overlays. No archived gear rules or action initiation.
local M={}
function M.install(env,scope,copy)
    local pending,serial,siphon= nil,0,nil
    local function invalidate() serial=serial+1; if pending and pending.cancel then pending.cancel() end; pending=nil end
    scope.own(invalidate)
    local function bloodpact(spell) return spell.type=='BloodPactRage' or spell.type=='BloodPactWard' end
    local function apply(name)
        local p=pending
        if not p or p.name~=name or p.used or not scope.active() or not env.pet.isvalid
            or env.pet.name~=p.pet or not env.state.lagmode.value then return false end
        p.used=true
        -- Use the FULL existing Mote pipeline, with this adapter's no-op pet hook.
        -- That preserves filters, user hooks, set mapping, post overlays and cleanup.
        env.handle_actions(copy(p.spell),'pet_midcast')
        return true
    end
    env.equipBPGear=apply -- compatibility entry; never equips arbitrary named sets
    local midcast=env.job_midcast
    env.job_midcast=function(spell,action,map,args)
        invalidate()
        if midcast then midcast(spell,action,map,args) end
        if bloodpact(spell) and not spell.interrupted and not args.cancel
            and env.state.lagmode.value and env.pet.isvalid then
            local p={spell=copy(spell),name=spell.name,pet=env.pet.name,id=serial}
            pending=p
            p.cancel=scope.after(0.5,function() if pending==p then apply(p.name) end end)
        end
    end
    -- The original called an undefined helper then allowed Mote to equip again.
    -- Normal pet events now use Mote exactly once in both lag modes.
    env.job_pet_midcast=function() end
    local precast=env.job_precast
    env.job_precast=function(spell,...)
        invalidate()
        if precast then return precast(spell,...) end
    end
    local aftercast=env.job_aftercast
    env.job_aftercast=function(spell,...)
        if spell.interrupted then invalidate() end
        if spell.english=='Elemental Siphon' then siphon=nil end
        if aftercast then return aftercast(spell,...) end
    end
    local petafter=env.job_pet_aftercast
    env.job_pet_aftercast=function(...)
        invalidate()
        if petafter then return petafter(...) end
    end
    for _,name in ipairs({'job_pet_change'}) do
        local original=env[name]
        env[name]=function(...) invalidate(); if original then return original(...) end end
    end
    local original_command=env.job_self_command
    env.job_self_command=function(args,event)
        local command=tostring(args[1] or ''):lower()
        if command=='equipbp' then apply(table.concat(args,' ',2)); event.handled=true; return end
        if command=='lagmode' then
            env.state.lagmode:toggle()
            if not env.state.lagmode.value then invalidate() end
            event.handled=true
            if env.updatedisplay then env.updatedisplay() end
            return
        end
        if original_command then return original_command(args,event) end
    end
    local helper=env.handle_siphoning
    if helper then
        env.handle_siphoning=function(...)
            local canonical=env.sets
            local overlay=(env.world.day_element=='Light' or env.world.day_element=='Dark')
                and canonical.SiphonLightDarkDay or canonical.SiphonZodiac
            siphon=copy(overlay or {})
            -- Let the existing finite command builder run against a transient
            -- graph. Its legacy assignment cannot modify prepared definitions.
            env.sets=copy(canonical)
            local ok,result=pcall(helper,...)
            env.sets=canonical
            if not ok then siphon=nil; error(result,0) end
            return result
        end
        local get_precast=env.get_precast_set
        env.get_precast_set=function(spell,...)
            local selected=get_precast(spell,...)
            if spell.english=='Elemental Siphon' and siphon then return env.set_combine(selected,siphon) end
            return selected
        end
    end
    return {invalidate=invalidate, pending=function() return pending end}
end
return M
