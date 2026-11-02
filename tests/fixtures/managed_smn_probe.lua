-- Runs only inside the isolated Nexus sandbox. No commands reach Windower.
local e=user_env
local mods=managed_modules
local report={checks={},fault=probe_fault}
result.smn_integration=report
local function check(name,value) report.checks[name]=not not value; assert(value,'integration: '..name..' '..tostring(report.error)) end
local candidate={resolved={sets=mods.data.copy(e.sets)},hotkeys={['!f11']={command='mode.lag_compensation.toggle',args={}}},removed_hotkeys={['^w']=true}}
candidate.settings=mods.spec.options().defaults
candidate.settings.modes.favor='All Out'
candidate.settings.legacy.display_states=true
local canonical=candidate.resolved.sets
local original_canonical=mods.data.copy(canonical)
canonical.managed_empty_probe={head=e.empty}
original_canonical.managed_empty_probe={head=e.empty}
local controls={['bind:^w']='external warp', ['bind:!f11']='external lag', ['bind:!%numpad1']='unrelated key', ['alias:unrelated']='unrelated alias'}
local original_controls=mods.data.copy(controls)
local commands,events,timers,observers,callbacks={},{},{},{},{}
local clock,eventserial=0,0
local ready=false
local prepares=0
local function send(command)
    commands[#commands+1]=command
    local verb,key,payload=command:match('^(%a+)%s+(%S+)%s*(.*)$')
    if verb=='bind' or verb=='alias' then controls[verb..':'..key]=payload end
    if verb=='unbind' then controls['bind:'..key]=nil end
    if verb=='unalias' then controls['alias:'..key]=nil end
end
e.send_command=send
e.windower.send_command=send
e.windower.register_event=function(name,fn) eventserial=eventserial+1; events[eventserial]={name=name,fn=fn}; return eventserial end
e.windower.raw_register_event=e.windower.register_event
e.windower.unregister_event=function(id) events[id]=nil end
e.register_unhandled_command=function(fn) callbacks[fn]=true end
local disabled={}
e.disable=function(...) for _,s in ipairs({...}) do disabled[s]=true end end
e.enable=function(...) for _,s in ipairs({...}) do disabled[s]=nil end end
local equipping={}
e.equip=function(set) equipping[#equipping+1]=mods.data.copy(set) end
local host={
    now=function() return clock end,
    identity=function() return {name=player.name,server=1,job=player.main_job} end,
    notify=function(message) report.last_message=message end,
    publish=function(value) ready=value; if value and probe_fault=='publish' then error('injected publish') end end,
    get_control=function(kind,key) return controls[kind..':'..key] end,
    remove_unhandled=function(fn) callbacks[fn]=nil end,
    schedule=function(delay,fn)
        local timer={at=clock+delay,fn=fn}; timers[#timers+1]=timer
        return function() timer.cancelled=true end
    end,
    watch=function(fn) observers[fn]=true; return function() observers[fn]=nil end end,
    prepare=function()
        prepares=prepares+1
        check('prepare_before_legacy',prepares>1 or #commands==0)
        if probe_fault=='prepare' then error('injected prepare') end
        return candidate
    end,
}
host.load_legacy=function()
    if probe_fault=='entry' then error('injected before entry') end
    e.include(basename(cfg.job_path))
    local original_include=e.include
    local pathsearch=e.gearswap.pathsearch
    local gearswap_proxy={}; for k,v in pairs(e.gearswap) do gearswap_proxy[k]=v end
    e.gearswap=gearswap_proxy
    local sidecar=player.name..'_SMN_gear.lua'
    e.gearswap.pathsearch=function(names,...)
        if names[1]==sidecar then return 'mocked late sidecar' end
        return pathsearch(names,...)
    end
    e.include=function(name,...)
        if name==sidecar then
            -- Execute inside the real load_sidecar call, before the adapter
            -- restores its managed hooks. No sidecar file is written.
            local js=e.job_setup
            e.job_setup=function(...)
                check('prepared_sets_before_setup_callback',e.sets.midcast.Pet.MagicalBloodPactRage~=nil)
                if probe_fault=='setup' then error('injected setup') end
                if probe_fault=='setup_event' then
                    local id=e.windower.register_event('managed setup event',function() error('injected setup event') end)
                    events[id].fn()
                    error('failed setup event resumed initializer')
                end
                return js(...)
            end
            local us=e.user_setup
            e.user_setup=function(...)
                us(...); e.state.favor:set('MP Saver')
                e.send_command('bind !f11 gs c lagmode')
            end
            e.init_gear_sets=function() error('legacy sidecar sets should not run') end
            return
        end
        local result=original_include(name,...)
        local lower=name:lower():gsub('%.lua$','')
        if lower=='mote-globals' and probe_fault=='globals' then error('injected globals') end
        return result
    end
end
local controller
e.get_sets=function() return controller.start() end
e.file_unload=function() controller.stop('unload') end
local adapter=mods.adapter.new(e,host,mods)
local attach=adapter.attach
adapter.attach=function(...)
    attach(...)
    if probe_fault=='controls' then error('injected controls') end
end
controller=mods.lifecycle.new(host,{profile='reference',character=player.name,server=1,job='SMN'},adapter)
controller.start()
if probe_fault=='event' then
    local id=e.windower.register_event('managed test event',function() error('injected event') end)
    events[id].fn()
end
report.state=controller.state; report.error=controller.error; report.cleanup_errors=controller.errors
local function size(t) local n=0; for _ in pairs(t) do n=n+1 end; return n end
local function same(a,b,seen)
    if type(a)~='table' or type(b)~='table' then return a==b end
    seen=seen or {}; if seen[a]==b then return true end; seen[a]=b
    for k,v in pairs(a) do if not same(v,b[k],seen) then return false end end
    for k in pairs(b) do if a[k]==nil then return false end end
    return true
end
local function cleanup_checks()
    check('no_ready_after_cleanup',not ready)
    check('no_events_after_cleanup',size(events)==0 and size(observers)==0)
    check('no_unhandled_after_cleanup',size(callbacks)==0)
    check('controls_restored',same(controls,original_controls))
end
if probe_fault~='' then
    check('failed_as_injected',controller.state=='failed')
    cleanup_checks()
    probe_fault=''
    controller.start()
    check('retry_after_failed_setup',ready and controller.state=='ready')
    controller.stop()
    cleanup_checks()
else
    check('ready',ready and controller.state=='ready')
    check('profile_final_mode_precedence',e.state.favor.value=='All Out')
    check('profile_final_key_precedence',controls['bind:!f11']=='gs c player mode.lag_compensation.toggle')
    check('profile_explicit_key_removal',controls['bind:^w']==nil)
    check('lag_initial_true',e.state.lagmode.value and e.LagMode==nil)
    check('working_copy_preserves_real_empty_sentinel',e.sets.managed_empty_probe.head==e.empty)
    check('canonical_data_unchanged_by_setup',same(original_canonical,candidate.resolved.sets))
    for _,command in ipairs({'toggle lagmode','lagmode','player mode.lag_compensation.toggle'}) do e.self_command(command) end
    check('lag_commands_share_authority',not e.state.lagmode.value and e.LagMode==nil)
    e.self_command('reset lagmode')
    check('lag_reset_uses_profile_default',e.state.lagmode.value)
    e.pet.name='Garuda'; e.pet.isvalid=true; e.pet.status='Engaged'
    local sp={name='Predator Claws',english='Predator Claws',en='Predator Claws',type='BloodPactRage',action_type='Ability',skill='Summoning Magic',target={type='MONSTER',name='Example'}}
    local function run_due()
        clock=clock+0.5
        local current=timers; timers={}
        for _,t in ipairs(current) do if not t.cancelled then if t.at<=clock then t.fn() else timers[#timers+1]=t end end end
    end
    local samples={}
    for _,flag in ipairs({false,true}) do
        e.state.lagmode:set(flag); equipping={}
        e.midcast(sp); equipping={}; e.pet_midcast(sp)
        local immediate=mods.data.copy(equipping)
        equipping={}; run_due()
        samples[#samples+1]={immediate=immediate,delayed=mods.data.copy(equipping)}
    end
    check('off_path_equips_without_missing_helper',#samples[1].immediate>0)
    check('off_path_no_delayed_equip',#samples[1].delayed==0)
    check('on_path_compensates',#samples[2].delayed>0)
    check('same_immediate_gear_both_lag_modes',same(samples[1].immediate,samples[2].immediate))
    check('compensation_reuses_exact_mote_equipment',same(samples[2].immediate,samples[2].delayed))
    local cases=0
    for _,sample in ipairs({
        {'Predator Claws','BloodPactRage','Garuda','MONSTER'},
        {'Flaming Crush','BloodPactRage','Ifrit','MONSTER'},
        {'Wind Blade','BloodPactRage','Garuda','MONSTER'},
        {'Impact','BloodPactRage','Fenrir','MONSTER'},
        {'Hastega II','BloodPactWard','Garuda','SELF'},
        {'Healing Ruby II','BloodPactWard','Carbuncle','SELF'},
        {'Lunar Cry','BloodPactWard','Fenrir','MONSTER'},
        {'Level ? Holy','BloodPactRage','Cait Sith','MONSTER'},
    }) do
        for _,tp in ipairs({0,3000}) do
            for _,accuracy in ipairs({false,true}) do
                e.pet.name=sample[3]; e.pet_tp=tp; e.state.bpmagicacc:set(accuracy)
                e.state.burstmode:set(accuracy and 'Burst' or 'Normal')
                local spell=mods.data.copy(sp)
                spell.name=sample[1]; spell.english=sample[1]; spell.en=sample[1]; spell.type=sample[2]; spell.target.type=sample[4]
                e.state.lagmode:set(true)
                e.midcast(spell); equipping={}; e.pet_midcast(spell)
                local normal=mods.data.copy(equipping)
                equipping={}; run_due()
                check('pact_equipment_case_'..cases,same(normal,equipping))
                cases=cases+1
            end
        end
    end
    report.pact_cases=cases
    e.pet.name='Garuda'; e.pet_tp=0; e.state.bpmagicacc:set(false); e.state.burstmode:set('Normal')
    e.midcast(sp); e.self_command('toggle lagmode'); e.self_command('toggle lagmode'); equipping={}; run_due()
    check('lag_toggle_discards_pending_compensation',#equipping==0)
    e.midcast(sp)
    e.beforemp=e.player.mp
    e.pet_aftercast(sp)
    equipping={}; run_due()
    check('completed_pact_discards_pending_compensation',#equipping==0)
    e.state.EquipStop:set('precast')
    equipping={}; e.midcast(sp); e.pet_midcast(sp); run_due()
    check('mote_show_set_filter_is_preserved',#equipping==0)
    e.state.EquipStop:set('off')
    -- Exercise the original finite Siphon command builder without retaining its
    -- in-place day overlay. The actual precast selector receives a working set.
    for _,day in ipairs({'Fire','Light','Dark'}) do
        e.world.day_element=day
        local before=mods.data.copy(e.sets)
        e.handle_siphoning()
        check('siphon_source_immutable_'..day,same(before,e.sets))
        local spell={name='Elemental Siphon',english='Elemental Siphon',en='Elemental Siphon',type='JobAbility',action_type='Ability',target={type='SELF',name=player.name}}
        local expected=e.set_combine(before.precast.JA['Elemental Siphon'],day=='Fire' and before.SiphonZodiac or before.SiphonLightDarkDay)
        check('siphon_day_equipment_'..day,same(expected,e.get_precast_set(spell)))
    end
    check('prepared_canonical_data_unchanged_after_actions',same(original_canonical,candidate.resolved.sets))
    check('siphon_working_copy_retains_empty_sentinel',e.sets.managed_empty_probe.head==e.empty)
    -- Queued compensation is rejected after pet action completion/unload.
    e.midcast(sp); local old=timers[#timers].fn
    e.self_command('nova layer M2')
    check('m_button_compatibility',e.Nova.layer=='M2')
    e.self_command('nova weapons'); e.enable('main','sub')
    check('explicit_weapon_lock_survives_enable',disabled.main and disabled.sub)
    local nova=e.Nova
    controller.stop(); local before=#equipping; old()
    check('old_delayed_callback_inert',#equipping==before)
    check('owned_weapon_lock_released',not disabled.main and not disabled.sub and not nova.weapon_lock)
    cleanup_checks()
    controller.stop()
    report.cleanup_errors=controller.errors
    check('cleanup_has_no_errors',#controller.errors==0)
    controller.start()
    check('reload_initializes_once',ready and controller.state=='ready')
    local event_count=size(events)
    controller.start()
    check('repeat_get_sets_has_no_duplicate_callbacks',size(events)==event_count)
    controller.stop()
    cleanup_checks()
end
report.command_count=#commands
