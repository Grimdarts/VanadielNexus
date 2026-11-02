-- Inactive bootstrap used by the staged entry and the offline harness.
-- Keep binding metadata outside maintained updates. Native services are injected
-- by a reviewed host, never by an executable PlayerProfiles file.
local M={}
function M.install(env,binding,services,modules)
    local controller
    env.get_sets=function() return controller.start() end
    env.file_unload=function() if controller then controller.stop('unload') end end
    local host=modules.host.new(env,services,modules)
    local adapter=modules.adapter.new(env,host,modules)
    controller=modules.lifecycle.new(host,binding,adapter)
    return controller
end
return M
