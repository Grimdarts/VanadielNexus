-- Stand-in for Windower's lists lib (test fixture).
_libs = _libs or {}
require('tables')
list = {}
function L(t) return setmetatable(t or {}, {__index = list}) end
_libs.lists = list
return list
