-- Stand-in for Windower's queues lib (test fixture).
_libs = _libs or {}
require('tables')
queue = {}
function Q(t) return setmetatable(t or {}, {__index = queue}) end
_libs.queues = queue
return queue
