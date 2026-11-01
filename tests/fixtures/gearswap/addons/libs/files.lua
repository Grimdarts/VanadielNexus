-- Stand-in for Windower's files lib (test fixture). Paths are relative to windower.addon_path, like the real one.
_libs = _libs or {}
require('strings')
local files = {}
_libs.files = files
function files.new(path) return setmetatable({path = path}, {__index = files}) end
function files.exists(f) return windower.file_exists(windower.addon_path .. f.path) end
function files.read(f)
    local fh = io.open(windower.addon_path .. f.path, 'r')
    if not fh then return nil end
    local text = fh:read('*a')
    fh:close()
    return text
end
function files.write(f, text)
    local fh = io.open(windower.addon_path .. f.path, 'w')
    fh:write(text)
    fh:close()
end
return files
