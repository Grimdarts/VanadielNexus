-- Identity -> complete candidate -> framework -> final controls -> ready.
-- Any failure/unload invalidates callbacks first, clears ready, then tears down
-- only completed/partially-entered phases in reverse order. No fallback profile.
local M={}
function M.validate_binding(binding)
    assert(type(binding)=='table','missing explicit profile binding')
    assert(type(binding.profile)=='string' and binding.profile:match('^[A-Za-z0-9_-]+$'),'invalid profile folder ID')
    assert(type(binding.character)=='string' and binding.character:match('^[A-Za-z]+$'),'invalid expected character name')
    assert(type(binding.server)=='number' and binding.server>0 and binding.server==math.floor(binding.server),'expected numeric server ID')
    assert(binding.job=='SMN','this staged adapter supports SMN only')
end
function M.new(host,binding,adapter)
    M.validate_binding(binding)
    local self={state='idle',generation=0,phases={},errors={}}
    local cleanup,live={},false
    local function notify(message) if host.notify then host.notify('[PlayerSystem '..binding.profile..'/'..binding.job..'] '..message) end end
    local function own(fn)
        assert(type(fn)=='function','cleanup must be a function')
        cleanup[#cleanup+1]=fn
    end
    local function release(state)
        live=false; self.generation=self.generation+1
        self.state=state; self.candidate=nil
        -- Unpublish before invoking legacy cleanup, even if publication itself failed.
        local ok,err=pcall(host.publish,false)
        if not ok then self.errors[#self.errors+1]=tostring(err) end
        local disposing=cleanup; cleanup={}
        for i=#disposing,1,-1 do
            ok,err=pcall(disposing[i]); if not ok then self.errors[#self.errors+1]=tostring(err) end
        end
    end
    local function failure(err)
        self.error=tostring(err); release('failed'); notify(self.error..'; correct the configuration and retry/reload')
    end
    function self.stop(reason)
        if not live then return end
        release('stopped'); self.reason=reason or 'unload'
    end
    function self.start()
        if live then return false end -- repeated get_sets cannot attach twice
        if #cleanup>0 then release('stopped') end
        self.generation=self.generation+1; local generation=self.generation
        self.phases={}; self.errors={}; self.error=nil
        live=true; self.state='waiting'
        local started=host.now(); local next_poll=started
        local waiting_cleanup
        local scope={}
        local scheduled={}
        own(function() for token,cancel in pairs(scheduled) do scheduled[token]=nil; if type(cancel)=='function' then cancel() end end end)
        scope.own=own
        function scope.active() return live and self.generation==generation end
        local function pack(...) return {n=select('#',...),...} end
        function scope.guard(fn)
            return function(...)
                if not scope.active() then return end
                local during_setup=self.state~='ready'
                local result=pack(pcall(fn,...))
                if not result[1] then
                    failure(result[2])
                    if during_setup then error(result[2],0) end -- unwind the legacy initializer
                    return
                end
                return unpack(result,2,result.n)
            end
        end
        function scope.after(seconds,fn)
            local token={}; scheduled[token]=true
            local cancel=host.schedule(seconds,function()
                local pending=scheduled[token]; scheduled[token]=nil
                if scope.active() and pending then
                    local ok,err=pcall(fn)
                    if not ok then failure(err) end
                end
            end)
            if scheduled[token] then scheduled[token]=cancel or true end
            local function dispose() scheduled[token]=nil; if cancel then cancel(); cancel=nil end end
            return dispose
        end
        local tick
        local function enter()
            if waiting_cleanup then waiting_cleanup(); waiting_cleanup=nil end
            own(host.watch(tick))
            self.state='preparing'; self.phases[#self.phases+1]='prepare'
            local candidate=host.prepare(binding)
            if not scope.active() then return end
            self.state='framework'; self.phases[#self.phases+1]='framework'
            -- Adapter registers rollback BEFORE executing legacy setup.
            adapter.enter(candidate,scope,binding)
            if not scope.active() then return end
            self.state='controls'; self.phases[#self.phases+1]='controls'
            adapter.attach(candidate,scope,binding)
            if not scope.active() then return end
            self.phases[#self.phases+1]='publish'
            host.publish(true,candidate)
            if not scope.active() then return end
            self.candidate=candidate; self.state='ready'
        end
        tick=function(event)
            if not scope.active() then return end
            if event=='logout' or event=='job change' then self.stop(event); return end
            local now=host.now()
            if now<next_poll then return end
            next_poll=now+0.5
            local ok,err=pcall(function()
                local identity=host.identity() or {}
                if identity.name and identity.name~=binding.character then error('character mismatch: expected '..binding.character,0) end
                if identity.server and identity.server~=binding.server then error('server mismatch: expected '..binding.server,0) end
                if identity.job and identity.job~=binding.job then self.stop('job change'); return end
                if self.state~='waiting' then
                    if not identity.name or not identity.server then
                        self.stop('identity unavailable')
                        notify('identity became unavailable; managed profile stopped; retry/reload after identity returns')
                    end
                    return
                end
                if identity.name and identity.server then enter()
                elseif now-started>=10 then error('identity unavailable after 10 seconds',0) end
            end)
            if not ok and self.state~='failed' then failure(err) end
        end
        -- One readiness observer owns its own tick/logout/job-change routes.
        local ok,err=pcall(function()
            local cancel=host.watch(tick)
            local done=false
            waiting_cleanup=function() if not done then done=true; cancel() end end
            own(waiting_cleanup)
            tick()
            if self.state=='waiting' then notify('waiting for character/server identity (up to 10 seconds)') end
        end)
        if not ok then failure(err) end
        return self.state=='ready'
    end
    return self
end
return M
