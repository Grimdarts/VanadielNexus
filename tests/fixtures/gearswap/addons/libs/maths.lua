-- Stand-in for Windower's maths lib (test fixture).
_libs = _libs or {}
require('functions')
debug.setmetatable(0, {__index = math})
_libs.maths = math
return math
