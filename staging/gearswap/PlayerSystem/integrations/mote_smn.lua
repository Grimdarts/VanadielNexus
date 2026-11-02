-- Compatibility adapter for the captured SMN Mote lifecycle. The trusted host
-- loads the inventoried legacy job/dependencies in this attempt's environment.
-- This module does not discover another character, migrate files, or install.
local M={}
function M.new(env,host,modules)
    local data,spec,ownership,pacts=modules.data,modules.spec,modules.ownership,modules.pacts
    local lease,settings
    local adapter={}
    function adapter.enter(candidate,scope)
        lease=ownership.enter(env,host,scope,data)
        local original_include=env.include
        local function working_copy(value) return data.copy(value,{[env.empty]=env.empty}) end
        local function working_sets() env.sets=working_copy(candidate.resolved.sets) end
        local function flags()
            env.LagMode=nil
            for name,value in pairs(settings.legacy) do env[name]=value end
        end
        local function setup_hooks()
            local job_setup,user_setup=env.job_setup,env.user_setup
            env.job_setup=function(...)
                working_sets(); flags()
                if job_setup then return job_setup(...) end
            end
            env.user_setup=function(...)
                flags()
                if user_setup then user_setup(...) end
                spec.apply(env,settings)
            end
            env.init_gear_sets=working_sets -- wins over a discovered legacy sidecar
        end
        settings=candidate.settings
        -- Isolate Mote's early default table assignments from the bootstrap graph.
        env.sets={}
        env.include=function(name,...)
            local result=original_include(name,...)
            local lower=name:lower():gsub('%.lua$','')
            if lower=='mote-selfcommands' then working_sets() end
            if lower=='mote-utility' then
                local load_sidecar=env.load_sidecar
                env.load_sidecar=function(...)
                    local result=load_sidecar(...)
                    setup_hooks()
                    return result
                end
            end
            return result
        end
        host.load_legacy(env)
        if not scope.active() then return end
        flags()
        local initialize=assert(env.get_sets,'legacy SMN did not define get_sets')
        assert(initialize~=lease.snapshot.get_sets,'legacy SMN did not replace bootstrap get_sets')
        env.get_sets=lease.snapshot.get_sets -- repeated external get_sets uses the controller
        -- Mote conditionally defines file_unload only when it is absent. Do not
        -- let the bootstrap observer hook suppress Mote's own cleanup function.
        if env.file_unload==lease.snapshot.file_unload then env.file_unload=nil end
        initialize() -- Nova's wrapper attaches its controls once AFTER Mote initializes
        if not scope.active() then return end
        assert(env.state and env.handle_actions and env.get_pet_midcast_set,'incomplete Mote initialization')
        spec.apply(env,settings)
        local pact_context=pacts.install(env,scope,working_copy)
        lease.set_unload(env.file_unload)
        env.file_unload=lease.snapshot.file_unload -- controller owns final teardown
        local original_command=env.self_command
        env.self_command=function(command)
            local previous=env.state.lagmode.value
            local id=type(command)=='string' and command:match('^player%s+(%S+)%s*$')
            if id then
                local descriptor=spec.options().commands[id]
                assert(descriptor,'unknown managed command '..id)
                command=descriptor.command
            end
            local result=original_command(command)
            if previous~=env.state.lagmode.value then pact_context.invalidate() end
            return result
        end
        if env.updatedisplay then env.updatedisplay() end
    end
    function adapter.attach(candidate)
        -- Profile-defined keys have final precedence over globals/sidecar/legacy
        -- job/Nova. Explicit removals are supplied separately by prepare_host.
        for key in pairs(candidate.removed_hotkeys or {}) do lease.control('bind',key,nil) end
        for key,record in pairs(candidate.hotkeys) do
            local descriptor=assert(spec.options().commands[record.command],'missing command registry entry')
            assert(not next(record.args or {}),'SMN commands currently take no profile arguments')
            lease.control('bind',key,'gs c player '..record.command)
        end
    end
    return adapter
end
return M
