-- Stand-in for Windower's tables lib (test fixture).
_libs = _libs or {}
require('maths')
local table = require('table')
function table.contains(t, value)
    for _, v in pairs(t) do if v == value then return true end end
    return false
end
function T(t) return setmetatable(t or {}, {__index = table}) end
_libs.tables = table
return table
