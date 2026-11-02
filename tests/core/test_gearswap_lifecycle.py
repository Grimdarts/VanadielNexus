"""Pure lifecycle failures, readiness cancellation and ownership isolation."""
from pathlib import Path

import pytest

from tests.core.test_managed_gearswap import env, quiet_faulthandler  # noqa: F401

STAGE = Path(__file__).parents[2] / 'staging/gearswap/PlayerSystem'


@pytest.fixture
def lifecycle(env):
    lua, _ = env
    lua.globals()[b'Lifecycle'] = lua.execute((STAGE / 'core/lifecycle.lua').read_bytes())
    lua.globals()[b'Ownership'] = lua.execute((STAGE / 'core/ownership.lua').read_bytes())
    lua.globals()[b'SMN'] = lua.execute((STAGE / 'jobs/SMN.lua').read_bytes())
    lua.globals()[b'Host'] = lua.execute((STAGE / 'integrations/prepare_host.lua').read_bytes())
    lua.globals()[b'Eligibility'] = lua.execute((STAGE / 'core/eligibility.lua').read_bytes())
    lua.execute(b'''
        now=0; watches={}; tasks={}; messages={}; ready=false; prepares=0; enters=0; attaches=0; releases=0
        identity={name='Example',server=1,job='SMN'}; fault=''
        host={now=function() return now end,identity=function() return identity end,
            notify=function(m) messages[#messages+1]=m end,
            prepare=function() prepares=prepares+1; if fault=='prepare' then error('bad data') end; return {value=1} end,
            publish=function(value) ready=value; if value and fault=='publish' then error('publish failure') end end,
            watch=function(fn) watches[fn]=true; return function() watches[fn]=nil end end,
            schedule=function(delay,fn) local t={fn=fn,at=now+delay}; tasks[#tasks+1]=t; return function() t.cancelled=true end end,
        }
        adapter={enter=function(candidate,scope)
                enters=enters+1; scope.own(function() releases=releases+1 end)
                if fault=='enter' then error('framework failed') end
                scope.after(0.5,function() if fault=='timer' then error('timer failed') end; fired=(fired or 0)+1 end)
            end,
            attach=function() attaches=attaches+1; if fault=='attach' then error('attach failed') end end}
        binding={profile='local_profile',character='Example',server=1,job='SMN'}
        function new() controller=Lifecycle.new(host,binding,adapter); return controller end
        function tick(time,event)
            now=time; local snapshot={}; for fn in pairs(watches) do snapshot[#snapshot+1]=fn end
            for _,fn in ipairs(snapshot) do fn(event) end
        end
        function count(t) local n=0; for _ in pairs(t) do n=n+1 end; return n end
    ''')
    return lua


def run(lua, code):
    return lua.execute(code.encode())


def test_identity_wait_and_deferred_success(lifecycle):
    assert run(lifecycle, '''identity={}; new().start(); tick(0.49); return prepares==0 and enters==0 and count(watches)==1 and #messages==1''')
    assert run(lifecycle, '''identity={name='Example',server=1,job='SMN'}; tick(0.5); return ready and controller.state=='ready' and enters==1 and count(watches)==1''')
    assert run(lifecycle, '''controller.start(); return enters==1 and attaches==1''')
    assert run(lifecycle, '''tick(1,'logout'); return controller.state=='stopped' and not ready and releases==1 and count(watches)==0''')


@pytest.mark.parametrize('identity,reason', [
    ("{name='Other',server=1}", 'character mismatch'),
    ("{name='Example',server=2}", 'server mismatch'),
    ("{name='Other'}", 'character mismatch'),
    ("{server=2}", 'server mismatch'),
])
def test_identity_mismatch_is_immediate(lifecycle, identity, reason):
    assert run(lifecycle, f"identity={identity}; new().start(); return controller.state=='failed' and prepares==0 and count(watches)==0")
    assert reason.encode() in lifecycle.globals()[b'controller'][b'error']


def test_identity_timeout_and_explicit_retry(lifecycle):
    assert run(lifecycle, "identity={}; new().start(); tick(9.5); return controller.state=='waiting'")
    assert run(lifecycle, "tick(10); return controller.state=='failed' and count(watches)==0 and #messages==2")
    assert run(lifecycle, "identity={name='Example',server=1}; controller.start(); return ready and prepares==1")


@pytest.mark.parametrize('event', ['logout', 'job change'])
def test_wait_is_cancelled_without_framework(lifecycle, event):
    assert run(lifecycle, f"identity={{}}; new().start(); tick(0.5,'{event}'); return controller.state=='stopped' and prepares==0 and count(watches)==0")


@pytest.mark.parametrize('fault', ['prepare', 'enter', 'attach', 'publish'])
def test_failure_teardown_and_retry(lifecycle, fault):
    assert run(lifecycle, f"fault='{fault}'; new().start(); return controller.state=='failed' and not ready and count(watches)==0")
    assert run(lifecycle, "fault=''; controller.start(); return ready and controller.state=='ready'")
    assert run(lifecycle, "controller.stop(); controller.stop(); return not ready and count(watches)==0")


def test_stale_callback_cannot_touch_new_attempt(lifecycle):
    assert run(lifecycle, "new().start(); local old=tasks[1].fn; controller.stop(); controller.start(); old(); return not fired and ready")
    assert run(lifecycle, "tasks[#tasks].fn(); return fired==1")


def test_delayed_callback_failure_unpublishes_and_cleans(lifecycle):
    assert run(lifecycle, "fault='timer'; new().start(); tasks[1].fn(); return controller.state=='failed' and not ready and releases==1 and count(watches)==0")


def test_owned_event_failure_after_ready_runs_cleanup(lifecycle):
    assert run(lifecycle, "local old=adapter.enter; adapter.enter=function(c,s) old(c,s); event=s.guard(function() error('late event failed') end) end; new().start(); event(); return controller.state=='failed' and not ready and releases==1")


@pytest.mark.parametrize('phase', ['prepare', 'enter', 'attach', 'publish'])
def test_reentrant_abort_during_setup_cannot_republish_ready(lifecycle, phase):
    target = 'host' if phase in ('prepare', 'publish') else 'adapter'
    assert run(lifecycle, f'''local original={target}.{phase}; {target}.{phase}=function(...)
        local result=original(...)
        controller.stop('reentrant cancellation')
        return result
    end; new().start(); return controller.state=='stopped' and not ready and count(watches)==0''')


def test_guarded_setup_event_failure_cannot_resume_initialization(lifecycle):
    assert run(lifecycle, "adapter.enter=function(c,s) s.guard(function() error('setup event failed') end)() end; new().start(); return controller.state=='failed' and not ready and attaches==0")


@pytest.mark.parametrize('field,value', [('profile', "'../wrong'"), ('profile', "'C:/wrong'"),
    ('character', "''"), ('server', "'ServerName'"), ('server', '0'), ('server', '1.5'), ('job', "'BLU'")])
def test_binding_validation(lifecycle, field, value):
    assert run(lifecycle, f"binding.{field}={value}; local ok=pcall(new); return not ok and prepares==0")


def test_smn_schema_defaults_and_modes(lifecycle):
    assert run(lifecycle, "local o=SMN.options(); return o.defaults.lag_compensation and o.defaults.modes.favor=='MP Saver' and o.settings_schema.fields.modes.fields.tplock.type=='boolean' and o.commands['summon.garuda'].command=='smn garuda'")


def test_cleanup_continues_after_one_disposer_fails(lifecycle):
    assert run(lifecycle, "adapter.enter=function(c,s) s.own(function() releases=releases+1 end); s.own(function() error('cleanup failure') end); error('setup failure') end; new().start(); return releases==1 and #controller.errors==1 and controller.state=='failed'")


def test_reentrant_stop_during_failed_cleanup_keeps_failure(lifecycle):
    assert run(lifecycle, "adapter.enter=function(c,s) s.own(function() controller.stop() end); error('setup failed') end; new().start(); return controller.state=='failed' and not ready and count(watches)==0")


def test_identity_loss_after_ready_unloads(lifecycle):
    assert run(lifecycle, "new().start(); identity={}; tick(1); return controller.state=='stopped' and not ready and releases==1")


def test_control_ownership_preserves_competing_changes_and_unowned_keys(lifecycle):
    assert run(lifecycle, '''
        local active=true; local disposers={}; local controls={['bind:f9']='previous', ['bind:f10']='unrelated'}
        local function send(c)
            local verb,key,value=c:match('^(%a+)%s+(%S+)%s*(.*)$')
            if verb=='bind' then controls['bind:'..key]=value end
            if verb=='unbind' then controls['bind:'..key]=nil end
        end
        local lib={new=function() return {destroy=function() end} end}
        local e={send_command=send,windower={register_event=function() return 1 end,unregister_event=function() end},
            texts=lib,require=function() return lib end,coroutine={},register_unhandled_command=function() end,gearswap={}}
        local h={get_control=function(kind,key) return controls[kind..':'..key] end}
        local s={active=function() return active end,own=function(fn) disposers[#disposers+1]=fn end,after=function() end}
        local lease=Ownership.enter(e,h,s,M)
        e.send_command('bind f9 owned')
        e.send_command('unbind f10')
        controls['bind:f9']='someone else changed it'
        active=false; disposers[1]()
        return controls['bind:f9']=='someone else changed it' and controls['bind:f10']=='unrelated'
    ''')


def test_snapshot_failure_during_cleanup_still_restores_environment(lifecycle):
    assert run(lifecycle, '''
        local disposers={}; local payload=nil; local broken=false
        local function send(c) payload=c:match('^bind f9 (.+)$') end
        local lib={new=function() return {destroy=function() end} end}
        local e={send_command=send,windower={register_event=function() return 1 end,unregister_event=function() end},
            texts=lib,require=function() return lib end,coroutine={},register_unhandled_command=function() end,gearswap={}}
        local s={active=function() return true end,own=function(fn) disposers[#disposers+1]=fn end,after=function() end}
        local lease=Ownership.enter(e,{get_control=function() if broken then error('snapshot unavailable') end; return payload end},s,M)
        e.send_command('bind f9 owned'); broken=true
        local ok=pcall(disposers[1])
        return not ok and e.send_command==send and e.texts==lib
    ''')


def test_native_objects_destroy_once_when_legacy_cleanup_throws(lifecycle):
    assert run(lifecycle, '''
        local disposers={}; local destroyed=0
        local lib={new=function() return {destroy=function() destroyed=destroyed+1 end} end}
        local e={send_command=function() end,windower={register_event=function() return 1 end,unregister_event=function() end},
            texts=lib,require=function() return lib end,coroutine={},register_unhandled_command=function() end,gearswap={}}
        local s={active=function() return true end,own=function(fn) disposers[#disposers+1]=fn end,after=function() end}
        local lease=Ownership.enter(e,{get_control=function() end},s,M)
        local text=e.texts.new(); local image=e.require('images').new()
        e.user_unload=function() text:destroy(); error('legacy failed') end
        local ok=pcall(disposers[1])
        return not ok and destroyed==2 and e.texts==lib
    ''')


def test_host_uses_real_identity_fields_and_cleans_partial_watch(lifecycle):
    assert run(lifecycle, '''
        local registrations=0; local released={}
        local e={windower={ffxi={get_player=function() return {name='Example',main_job='SMN'} end,
            get_info=function() return {server=77,zone=999} end},
            register_event=function() registrations=registrations+1; if registrations==3 then error('watch failure') end; return registrations end,
            unregister_event=function(id) released[id]=true end}}
        local services={read_profile=function() end,get_control=function() end,now=function() end,schedule=function() end}
        local h=Host.new(e,services,{spec=SMN,data=M})
        local identity=h.identity(); local ok=pcall(h.watch,function() end)
        return identity.server==77 and identity.name=='Example' and not ok and released[1] and released[2]
    ''')


def test_host_preparation_uses_restricted_reader_and_keeps_removal_intent(lifecycle):
    assert run(lifecycle, '''
        local sources={
            ['Equipment.lua']='return {schema=1,kind="equipment",items={}}',
            ['Settings.lua']='return {schema=1,kind="settings",shared={},jobs={SMN={lag_compensation=false,modes={favor="All Out"}}}}',
            ['Hotkeys.lua']='return {schema=1,kind="hotkeys",shared={f9={remove=true},f10={remove=true}},jobs={SMN={f10={command="controls.ws"}}}}',
            ['Sets/SMN.lua']='return {schema=1,kind="sets",job="SMN",definitions={a={path={"idle"},slots={head="Example Hat"}}}}',
        }
        local reads=0
        local services={read_profile=function(profile,file,limit)
            assert(profile=='local_profile' and limit==2097152); reads=reads+1; return sources[file]
        end,get_control=function() end,now=function() end,schedule=function() end,validate_item=function() return true end}
        local h=Host.new({empty={name='empty'}},services,{spec=SMN,data=M,lifecycle=Lifecycle})
        local candidate=h.prepare(binding)
        assert(reads==4 and candidate.removed_hotkeys.f9 and not candidate.removed_hotkeys.f10)
        assert(not candidate.settings.lag_compensation and candidate.settings.modes.favor=='All Out')
        sources['Settings.lua']='return {schema=1,kind="settings",shared={evil=os.execute("bad")},jobs={}}'
        local ok=pcall(h.prepare,binding)
        return not ok and candidate.hotkeys.f10.command=='controls.ws'
    ''')


@pytest.mark.parametrize('item,slot,accepted', [
    ("'Hat'", 'head', True), ("'Hat'", 'feet', False), ("'Other Job'", 'head', False),
    ("'Too High'", 'head', False), ("'Unknown'", 'head', False),
    ("{name='Hat',bag='Wardrobe 1'}", 'head', True),
    ("{name='Hat',bag='Safe'}", 'head', False),
    ("{name='Hat',bag='Unknown'}", 'head', False),
    ("'Earring'", 'ear2', True), ("'Ring'", 'ring2', True),
])
def test_resource_eligibility(lifecycle, item, slot, accepted):
    result = run(lifecycle, f'''
        local band=require('bit').band
        local check=Eligibility.validator({{
            {{en='Hat',slots=16,jobs=32768,level=99}}, {{en='Other Job',slots=16,jobs=2,level=99}},
            {{en='Too High',slots=16,jobs=32768,level=100}},
            {{en='Earring',slots=2048,jobs=32768,level=1}},{{en='Ring',slots=8192,jobs=32768,level=1}},
        }},{{{{en='Wardrobe',equippable=true}},{{en='Safe',equippable=false}}}},band,15,99)
        return check({item},'{slot}')
    ''')
    assert (result[0] if isinstance(result, tuple) else result) is accepted


def test_processed_resource_sets_and_log_names_are_supported(lifecycle):
    assert run(lifecycle, '''
        local check=Eligibility.validator({{en='Hat',enl='a fine hat',slots={[4]=true},jobs={[15]=true},level=99}},
            {},require('bit').band,15,99)
        return check('a fine hat','head') and not check('a fine hat','feet')
    ''')


def test_ambiguous_resource_names_fail_deterministically(lifecycle):
    assert run(lifecycle, '''
        local check=Eligibility.validator({{en='Hat',slots=16,jobs=32768},{en='Hat',slots=16,jobs=2}},
            {},require('bit').band,15,99)
        local ok,message=check('Hat','head')
        return not ok and message=='ambiguous item resource Hat'
    ''')


def test_baseline_keyboard_syntax_is_supported(lifecycle):
    assert run(lifecycle, "return M.normalize_chord('@numpad.')=='@numpad.' and M.normalize_chord('!%numpad+')=='!%numpad+' and M.normalize_chord('^-')=='^-'")
