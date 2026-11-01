-- Stand-in for Windower's functions lib (test fixture). Like the real one, it calls debug.setmetatable at load.
_libs = _libs or {}
functions = {}
_libs.functions = functions
debug.setmetatable(false, {__index = function() return nil end})
return functions
