-- Read-only Windows service for prepare_host. Trusted LuaJIT FFI only; managed
-- sources never reach ffi or a Lua compiler. Open each path component without
-- following its reparse point, verify the opened handle's final path, and retain
-- non-delete-sharing directory handles until the bounded file read completes.
-- API contract: https://learn.microsoft.com/windows/win32/api/fileapi/nf-fileapi-createfilew
local M={}
function M.new(ffi,root)
    assert(ffi.os=='Windows','Windows profile reader requires Windows LuaJIT')
    if not pcall(ffi.typeof,'VN_PROFILE_FILE_INFO') then
        ffi.cdef[[
            typedef struct { unsigned long attributes; unsigned long times[6];
                unsigned long volume, size_high, size_low, links, index_high, index_low; } VN_PROFILE_FILE_INFO;
            void* __stdcall CreateFileW(const uint16_t*, unsigned long, unsigned long, void*, unsigned long, unsigned long, void*);
            int __stdcall CloseHandle(void*);
            unsigned long __stdcall GetLastError(void);
            unsigned long __stdcall GetFullPathNameW(const uint16_t*, unsigned long, uint16_t*, uint16_t**);
            unsigned long __stdcall GetFinalPathNameByHandleW(void*, uint16_t*, unsigned long, unsigned long);
            int __stdcall GetFileInformationByHandle(void*, VN_PROFILE_FILE_INFO*);
            int __stdcall GetFileSizeEx(void*, int64_t*);
            int __stdcall ReadFile(void*, void*, unsigned long, unsigned long*, void*);
            int __stdcall MultiByteToWideChar(unsigned int, unsigned long, const char*, int, uint16_t*, int);
            int __stdcall WideCharToMultiByte(unsigned int, unsigned long, const uint16_t*, int, char*, int, const char*, int*);
            int __stdcall CompareStringOrdinal(const uint16_t*, int, const uint16_t*, int, int);
        ]]
    end
    local kernel=ffi.load('kernel32')
    local invalid=ffi.cast('void*',-1)
    local function fail(text) error('profile read: '..text..' (Windows error '..tonumber(kernel.GetLastError())..')',0) end
    local function wide(s)
        assert(not s:find('%z'),'NUL in profile path')
        local n=kernel.MultiByteToWideChar(65001,8,s,#s,nil,0)
        if n==0 then fail('invalid UTF-8 path') end
        local result=ffi.new('uint16_t[?]',n+1)
        if kernel.MultiByteToWideChar(65001,8,s,#s,result,n)==0 then fail('path conversion failed') end
        return result
    end
    local function text(w,n)
        local count=kernel.WideCharToMultiByte(65001,0,w,n,nil,0,nil,nil)
        if count==0 then fail('path conversion failed') end
        local out=ffi.new('char[?]',count)
        if kernel.WideCharToMultiByte(65001,0,w,n,out,count,nil,nil)==0 then fail('path conversion failed') end
        return ffi.string(out,count)
    end
    local function full(path)
        local buffer=ffi.new('uint16_t[32768]')
        local n=kernel.GetFullPathNameW(wide(path),32768,buffer,nil)
        if n==0 or n>=32768 then fail('invalid or excessive path') end
        return text(buffer,n):gsub('\\+$','')
    end
    assert(type(root)=='string' and root:match('^[A-Za-z]:[/\\]'),'profile root must be an absolute local drive path')
    root=full(root)
    local allowed={['Equipment.lua']=true,['Settings.lua']=true,['Hotkeys.lua']=true,['Sets/SMN.lua']=true}
    return function(profile,name,limit)
        assert(type(profile)=='string' and profile:match('^[A-Za-z0-9_-]+$'),'invalid profile folder ID')
        assert(allowed[name],'unsupported profile filename')
        assert(type(limit)=='number' and limit>=1 and limit<=2097152 and limit==math.floor(limit),'invalid profile read bound')
        local handles={}
        local function open(path,directory)
            local handle=kernel.CreateFileW(wide(path),directory and 129 or 2147483648,
                directory and 3 or 1,nil,3,35651584,nil) -- backup semantics | open reparse point
            if handle==invalid then
                local code=tonumber(kernel.GetLastError())
                if code==2 or code==3 then return nil end
                fail('cannot open '..path)
            end
            handles[#handles+1]=handle
            local info=ffi.new('VN_PROFILE_FILE_INFO[1]')
            if kernel.GetFileInformationByHandle(handle,info)==0 then fail('cannot inspect '..path) end
            local attr=tonumber(info[0].attributes)
            if math.floor(attr/1024)%2==1 then error('profile read: reparse point rejected '..path,0) end
            if (math.floor(attr/16)%2==1)~=directory then error('profile read: unexpected file type '..path,0) end
            local buffer=ffi.new('uint16_t[32768]')
            local n=kernel.GetFinalPathNameByHandleW(handle,buffer,32768,0)
            if n==0 or n>=32768 then fail('cannot resolve opened handle '..path) end
            local final=text(buffer,n):gsub('^\\\\%?\\','')
            if kernel.CompareStringOrdinal(wide(final),-1,wide(path),-1,1)~=2 then
                error('profile read: unexpected path redirection '..path,0)
            end
            return handle
        end
        local ok,result=pcall(function()
            if not open(root,true) then return nil end
            local base=root..'\\'..profile
            if not open(base,true) then return nil end
            if name:match('^Sets/') and not open(base..'\\Sets',true) then return nil end
            local handle=open(base..'\\'..name:gsub('/','\\'),false)
            if not handle then return nil end
            local size=ffi.new('int64_t[1]')
            if kernel.GetFileSizeEx(handle,size)==0 then fail('cannot read file size '..name) end
            if size[0]>limit then error('profile read: '..profile..'/'..name..' exceeded bytes limit '..limit,0) end
            local buffer=ffi.new('char[?]',limit+1)
            local count=ffi.new('unsigned long[1]')
            if kernel.ReadFile(handle,buffer,limit+1,count,nil)==0 then fail('cannot read '..name) end
            if count[0]>limit then error('profile read: exceeded bytes limit '..limit,0) end
            return ffi.string(buffer,count[0])
        end)
        for i=#handles,1,-1 do kernel.CloseHandle(handles[i]) end
        if not ok then error(result,0) end
        return result
    end
end
return M
