-- Stand-in for Windower's sets lib (test fixture).
_libs = _libs or {}
require('tables')
set = {}
function set.contains(s, value) return rawget(s, value) == true end
function S(t)
    local s = {}
    for _, v in pairs(t or {}) do s[v] = true end
    return setmetatable(s, {__index = set})
end
_libs.sets = set
return set
