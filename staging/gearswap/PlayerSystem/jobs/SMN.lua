-- Maintained schemas and literal command registry. No player equipment here.
local M={}
local modes={
    OffenseMode={'Perp','Melee'},CastingMode={'Normal','Resistant','PDT'},IdleMode={'Normal','PDT'},
    damagetaken={'None','DT','PDT','MDT'},petdamagetaken={'None','DT'},favor={'MP Saver','All Out'},
    burstmode={'Normal','Burst'},DefenseMode={'None','Physical','Magical'},
    PhysicalDefenseMode={'PDT'},MagicalDefenseMode={'MDT'},PCTargetMode={'default','stpt','stal','stpc'},
    EquipStop={'off','precast','midcast','pet_midcast'},HybridMode={'Normal'},RangedMode={'Normal'},
    WeaponskillMode={'Normal'},RestingMode={'Normal'},
}
local bool_modes={'cpmode','movement','tplock','impactmode','pullmode','magiceva','idlehealer','bpmagicacc','Kiting','SelectNPCTargets'}
local flags={display_hud=false,display_icon=true,display_states=false,hud_draggable=true,
    debug_gs1=false,usemephitas=false,use_melee=true,use_enfeeb=true,use_player_mab=true,
    use_resistant=false,use_icon=false,conduit_lock=true,custom_includes=false,
    shattersoul_set=true,use_bliss=true,use_cataclysm=true,exp_rings=false,
    load_debugging=false,useall_bp_reduction_gear=false,cureIV=true,use_dualbox=false}
M.mode_values=modes; M.boolean_modes=bool_modes
function M.options()
    local defaults={lag_compensation=true,modes={},legacy={}}
    local schema={type='map',required=true,fields={
        lag_compensation={type='boolean',required=true},
        modes={type='map',required=true,fields={}},legacy={type='map',required=true,fields={}},
    }}
    local commands={}
    for name,values in pairs(modes) do
        defaults.modes[name]=values[1]
        schema.fields.modes.fields[name]={type='string',enum=values,required=true}
        commands['mode.'..name..'.cycle']={command='cycle '..name,label='Cycle '..name}
    end
    for _,name in ipairs(bool_modes) do
        defaults.modes[name]=false
        schema.fields.modes.fields[name]={type='boolean',required=true}
        commands['mode.'..name..'.toggle']={command='toggle '..name,label='Toggle '..name}
    end
    for name,value in pairs(flags) do
        defaults.legacy[name]=value; schema.fields.legacy.fields[name]={type='boolean',required=true}
    end
    commands['mode.lag_compensation.toggle']={command='toggle lagmode',label='Lag compensation'}
    for _,name in ipairs({'carbuncle','fenrir','diabolos','ifrit','shiva','garuda','titan','ramuh','leviathan','caitsith','siren','atomos','lightspirit'}) do
        commands['summon.'..name]={command='smn '..name,label='Summon '..name}
    end
    for _,name in ipairs({'cure','curaga','buffoffense','buffdefense','buffspecial','debuff1','debuff2','sleep','misc1','misc2','misc3','misc4','nuke2','nuke4','bp70','bp75','bprage1','astralflow'}) do
        commands['pact.'..name]={command='pact '..name,label='Pact '..name}
    end
    for _,name in ipairs({'supportmode','nukemode','buffrotation','siphon','release','toggle_hud','force_hud_refresh'}) do
        commands[name]={command=name,label=name}
    end
    for _,name in ipairs({'melee','ws','casting','idle'}) do
        commands['controls.'..name]={command='nova cycle '..name,label='Cycle '..name}
    end
    commands['controls.hud']={command='nova hud',label='Controls HUD'}
    commands['controls.weapons']={command='nova weapons',label='Weapon lock'}
    return {job='SMN',defaults=defaults,settings_schema=schema,commands=commands,hotkeys={}}
end
function M.apply(env,settings)
    env.LagMode=nil -- obsolete split flag is never an authority in the adapter
    for name,value in pairs(settings.legacy) do env[name]=value end
    if env.state then
        for name,value in pairs(settings.modes) do
            assert(env.state[name] and env.state[name].set,'missing SMN mode '..name)
            env.state[name]:set(value)
        end
        env.state.lagmode=env.M(settings.lag_compensation,'Lag Mode')
    end
end
return M
