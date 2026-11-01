-- Stand-in for Windower's strings lib (test fixture). Like the real one, it sets the string metatable.
_libs = _libs or {}
require('functions')
require('maths')
local string = require('string')
debug.setmetatable('', {__index = function(str, k) return string[k] end})
string.wmatch = windower.wc_match
function string.startswith(s, prefix) return s:sub(1, #prefix) == prefix end
_libs.strings = string
return string
