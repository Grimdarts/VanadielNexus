-- Stand-in for Windower's json lib (test fixture).
_libs = _libs or {}
require('tables')
require('strings')
local files = require('files')
json = {}
_libs.json = json
return json
