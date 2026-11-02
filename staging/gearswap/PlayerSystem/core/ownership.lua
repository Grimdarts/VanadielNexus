-- Attempt-local wrappers. Do not mutate the shared Windower/texts libraries.
-- Host control snapshots are mandatory: restore only controls still owned here.
local M={}
local function shallow(t) local out={}; for k,v in pairs(t) do out[k]=v end; return out end
function M.enter(env,host,scope,data)
    assert(host.get_control,'host must provide binding/alias collision snapshots')
    local snapshot=shallow(env)
    local controls,events,objects,unhandled={},{},{},{}
    local cleaning=false
    local final_unload
    local send=env.send_command
    local wind=env.windower
    local function control(kind,key,payload)
        if kind=='bind' then key=assert(data.normalize_chord(key),'unsupported legacy chord '..key) end
        local id=kind..':'..key
        local record=controls[id]
        if not record then
            record={kind=kind,key=key,previous=host.get_control(kind,key)}
            controls[id]=record
        elseif record.current~=host.get_control(kind,key) then
            error('control collision changed outside this load: '..key,0)
        end
        record.current=payload
        send((payload and kind or (kind=='bind' and 'unbind' or 'unalias'))..' '..key..(payload and ' '..payload or ''))
    end
    local function command(text)
        local verb,key,payload=text:match('^%s*(%a+)%s+(%S+)%s*(.*)$')
        if verb=='bind' or verb=='alias' then control(verb,key,payload); return end
        if verb=='unbind' or verb=='unalias' then
            local kind=verb=='unbind' and 'bind' or 'alias'
            key=kind=='bind' and data.normalize_chord(key) or key
            local record=key and controls[kind..':'..key]
            if record and record.current==host.get_control(kind,key) then control(kind,key,nil) end
            return -- legacy blanket unbind cannot touch an unowned control
        end
        if text=='lua load g13_smn_bridge' or text=='lua unload g13_smn_bridge' then
            if not cleaning and text:find(' load ',1,true) and host.acquire_bridge then
                local dispose=host.acquire_bridge('g13_smn_bridge'); if dispose then scope.own(dispose) end
            end
            return
        end
        local delay,tail=text:match('^wait%s+([%d.]+);%s*(.+)$')
        if delay and (tail:match('^gs c ') or tail=='gi update') then
            if not cleaning then scope.after(tonumber(delay),function() send(tail) end) end
            return
        end
        if not cleaning then send(text) end
    end
    local function register(raw,...)
        local args={...}; local callback=args[#args]
        args[#args]=scope.guard and scope.guard(callback) or function(...) if scope.active() then return callback(...) end end
        local ids={raw(unpack(args))}
        for _,id in ipairs(ids) do events[id]=true end
        return unpack(ids)
    end
    local function lib(original)
        local proxy=setmetatable(shallow(original),{__index=original})
        proxy.new=function(...)
            local object=original.new(...); objects[#objects+1]=object
            local destroy=object.destroy; local destroyed=false
            if destroy then object.destroy=function(...)
                if not destroyed then destroyed=true; return destroy(...) end
            end end
            return object
        end
        return proxy
    end
    -- Rollback is owned before the first framework include or resource allocation.
    scope.own(function()
        cleaning=true
        local errors={}
        local function safe(fn) if fn then local ok,err=pcall(fn); if not ok then errors[#errors+1]=tostring(err) end end end
        for _,name in ipairs({'user_unload','job_file_unload','binds_on_unload','global_on_unload'}) do
            local fn=env[name]; local called=false
            if fn then env[name]=function(...) if not called then called=true; return fn(...) end end end
        end
        local unload=final_unload or (env.file_unload~=snapshot.file_unload and env.file_unload)
        safe(unload)
        safe(env.user_unload or env.job_file_unload)
        safe(env.binds_on_unload or env.global_on_unload)
        if env.Nova and env.Nova.weapon_lock then
            env.Nova.weapon_lock=false; safe(function() env.enable('main','sub','range') end)
        end
        for id in pairs(events) do safe(function() wind.unregister_event(id) end) end
        for _,callback in ipairs(unhandled) do
            safe(function()
                if host.remove_unhandled then host.remove_unhandled(callback)
                else
                    local list=env.gearswap.unhandled_command_events
                    for i=#list,1,-1 do if list[i]==callback then table.remove(list,i) end end
                end
            end)
        end
        for _,object in ipairs(objects) do
            -- Some legacy unloads destroy a HUD themselves. The wrapper's own
            -- idempotent disposer below prevents a second native destruction.
            safe(function() if object.destroy then object:destroy() end end)
        end
        for _,record in pairs(controls) do
            safe(function()
                if host.get_control(record.kind,record.key)==record.current then
                    local payload=record.previous
                    send((payload and record.kind or (record.kind=='bind' and 'unbind' or 'unalias'))..' '..record.key..(payload and ' '..payload or ''))
                end
            end)
        end
        for k in pairs(env) do if snapshot[k]==nil then env[k]=nil end end
        for k,v in pairs(snapshot) do env[k]=v end
        if #errors>0 then error(table.concat(errors,'; '),0) end
    end)
    env.send_command=command
    env.windower=shallow(wind)
    env.windower.send_command=command
    env.windower.register_event=function(...) return register(wind.register_event,...) end
    env.windower.raw_register_event=function(...) return register(wind.raw_register_event,...) end
    env.windower.unregister_event=function(id) if events[id] then events[id]=nil; return wind.unregister_event(id) end end
    env.coroutine=shallow(env.coroutine)
    env.coroutine.schedule=function(fn,delay) return scope.after(delay,fn) end
    local register_unhandled=env.register_unhandled_command
    env.register_unhandled_command=function(fn)
        assert(host.remove_unhandled or env.gearswap.unhandled_command_events,'host cannot release framework command callbacks')
        local wrapped=scope.guard and scope.guard(fn) or function(...) if scope.active() then return fn(...) end end
        unhandled[#unhandled+1]=wrapped
        return register_unhandled(wrapped)
    end
    local wrapped={}
    local function wrap_library(name,original)
        if not wrapped[name] then wrapped[name]=lib(original) end
        return wrapped[name]
    end
    env.texts=wrap_library('texts',env.texts)
    local require_original=env.require
    env.require=function(name,...)
        local original=require_original(name,...)
        if name=='texts' or name=='images' then return wrap_library(name,original) end
        return original
    end
    return {control=control,controls=controls,events=events,
        set_unload=function(fn) final_unload=fn end, snapshot=snapshot}
end
return M
