-- Narrow host boundary. Native services must be verified on the installed runtime
-- before activation; tests supply read-only filesystem/control/timer services.
local M={}
function M.new(env,services,modules)
    assert(services.read_profile,'missing checked profile reader')
    assert(services.get_control,'missing live control snapshot service')
    assert(services.now and services.schedule,'missing monotonic clock/timer service')
    local spec,data=modules.spec,modules.data
    local host={now=services.now,schedule=services.schedule,get_control=services.get_control,
        remove_unhandled=services.remove_unhandled,acquire_bridge=services.acquire_bridge,
        load_legacy=services.load_legacy,notify=services.notify}
    function host.identity()
        local player=env.windower.ffxi.get_player()
        local info=env.windower.ffxi.get_info()
        return {name=player and player.name,job=player and player.main_job,server=info and info.server}
    end
    function host.watch(tick)
        local ids={}
        local function dispose()
            for i=#ids,1,-1 do env.windower.unregister_event(ids[i]); ids[i]=nil end
        end
        local ok,err=pcall(function()
            ids[#ids+1]=env.windower.register_event('prerender',function() tick() end)
            ids[#ids+1]=env.windower.register_event('logout',function() tick('logout') end)
            ids[#ids+1]=env.windower.register_event('job change',function() tick('job change') end)
        end)
        if not ok then dispose(); error(err,0) end
        return dispose
    end
    function host.publish(ready,candidate)
        env.PlayerSystemReady=ready and {profile=candidate.profile,job='SMN'} or nil
    end
    function host.prepare(binding)
        modules.lifecycle.validate_binding(binding)
        local sources={}
        for _,name in ipairs({'Equipment.lua','Settings.lua','Hotkeys.lua','Sets/SMN.lua'}) do
            -- read_profile is a trusted native service, NOT an include/evaluator.
            -- It must reject reparse/symlink escapes and changed redirection,
            -- constrain the opened handle to PlayerProfiles/<binding.profile>,
            -- read at most limit+1 bytes and close it on every outcome.
            sources[name]=services.read_profile(binding.profile,name,2097152)
        end
        local options=spec.options()
        options.profile=binding.profile; options.empty=env.empty
        options.validate_item=services.validate_item
        if not options.validate_item then
            local res=env.gearswap.res
            options.validate_item=modules.eligibility.validator(res.items,res.bags,env.bit.band,15,env.player.main_job_level)
        end
        local candidate=data.prepare(sources,options)
        candidate.profile=binding.profile
        candidate.removed_hotkeys={}
        local document=candidate.documents['Hotkeys.lua'].root.value
        local function removals(n)
            if not n then return end
            for key,value in pairs(n.value) do
                candidate.removed_hotkeys[data.normalize_chord(key)]=value.value.remove and true or nil
            end
        end
        removals(document.shared)
        removals(document.jobs.value[binding.job])
        return candidate
    end
    return host
end
return M
