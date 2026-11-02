-- Managed player data v1. Pure Lua 5.1: no file I/O, include, or evaluation.
-- Hosts supply source bytes, maintained schemas/commands and the real empty sentinel.
-- Spans are 1-based byte offsets [start, finish); columns count UTF-8 characters.
local M = {}
local limits = {bytes=2097152, depth=64, values=100000, records=4096, references=64, materialized_values=100000}
local function copy(v,seen,charge)
    if charge then charge() end
    if type(v) ~= 'table' then return v end
    seen=seen or {}
    if seen[v] then return seen[v] end
    local out = {}
    seen[v]=out
    for k, x in pairs(v) do out[k] = copy(x,seen,charge) end
    return out
end
M.copy = copy

local function utf8(s)
    local i = 1
    while i <= #s do
        local b = s:byte(i)
        local n = b < 128 and 1 or b >= 194 and b <= 223 and 2
            or b >= 224 and b <= 239 and 3 or b >= 240 and b <= 244 and 4
        if not n or i+n-1 > #s then return i end
        for j=i+1,i+n-1 do
            local c = s:byte(j)
            if c < 128 or c > 191 then return j end
        end
        local c = s:byte(i+1)
        if (b == 224 and c < 160) or (b == 237 and c > 159)
            or (b == 240 and c < 144) or (b == 244 and c > 143) then return i end
        i = i+n
    end
end

function M.parse(source, file, overrides)
    file = file or '<data>'
    local cap = copy(limits)
    for k,v in pairs(overrides or {}) do
        assert(cap[k] and type(v)=='number' and v>=1 and v==math.floor(v), 'invalid limit '..k)
        cap[k] = math.min(cap[k], v) -- callers may tighten, never disable bounds
    end
    if #source>cap.bytes then error(file..':1:1: exceeded bytes limit '..cap.bytes,0) end
    local p, count, starts, continuation = 1, 0, {1}, {}
    -- Build line index once, including CR and CRLF, for cheap repeated locations.
    local i=1
    while i<=#source do
        local c=source:sub(i,i)
        local byte=source:byte(i)
        if byte>=128 and byte<=191 then continuation[#continuation+1]=i end
        if c=='\r' or c=='\n' then
            if c=='\r' and source:sub(i+1,i+1)=='\n' then i=i+1 end
            starts[#starts+1]=i+1
        end
        i=i+1
    end
    local function before(list,at)
        local lo,hi=0,#list
        while lo<hi do
            local mid=math.floor((lo+hi+1)/2)
            if list[mid]<at then lo=mid else hi=mid-1 end
        end
        return lo
    end
    local function span(a,b)
        local line=before(starts,a+1)
        local multibyte=before(continuation,a)-before(continuation,starts[line])
        return {file=file, start=a, finish=b, line=line, column=a-starts[line]-multibyte+1}
    end
    local function fail(message, at)
        local s=span(at or p,at or p)
        error(file..':'..s.line..':'..s.column..': '..message,0)
    end
    local bad=utf8(source)
    if bad then fail('invalid UTF-8',bad) end
    if source:sub(1,3)=='\239\187\191' then p=4 end
    local function skip()
        while p<=#source do
            local c=source:sub(p,p)
            if c:match('%s') then p=p+1
            elseif source:sub(p,p+1)=='--' then
                p=p+2
                local eq=source:match('^%[(=*)%[',p)
                if eq then
                    local close=']'..eq..']'
                    local last=source:find(close,p+#eq+2,true)
                    if not last then fail('unterminated long comment') end
                    p=last+#close
                else
                    while p<=#source and not source:sub(p,p):match('[\r\n]') do p=p+1 end
                end
            else break end
        end
    end
    local function expect(c)
        skip()
        if source:sub(p,p)~=c then fail('expected '..c) end
        p=p+1
    end
    local escapes={a='\7',b='\8',f='\12',n='\n',r='\r',t='\t',v='\11', ['\\']='\\', ['"']='"', ["'"]="'"}
    local function quoted()
        local q=source:sub(p,p)
        p=p+1
        local parts={}
        while p<=#source do
            local c=source:sub(p,p)
            p=p+1
            if c==q then
                local s=table.concat(parts)
                if utf8(s) then fail('string escapes produce invalid UTF-8') end
                return s
            elseif c=='\r' or c=='\n' then fail('unescaped newline in string',p-1)
            elseif c=='\\' then
                c=source:sub(p,p)
                if c:match('%d') then
                    local digits=source:match('^%d%d?%d?',p)
                    local n=tonumber(digits)
                    if n>255 then fail('decimal escape exceeds 255') end
                    parts[#parts+1]=string.char(n); p=p+#digits
                elseif c=='\r' or c=='\n' then
                    if c=='\r' and source:sub(p+1,p+1)=='\n' then p=p+1 end
                    parts[#parts+1]='\n'; p=p+1
                elseif escapes[c] then parts[#parts+1]=escapes[c]; p=p+1
                else fail('unsupported string escape') end
            else parts[#parts+1]=c end
        end
        fail('unterminated string')
    end
    local reserved={['and']=true,['break']=true,['do']=true,['else']=true,['elseif']=true,
        ['end']=true,['false']=true,['for']=true,['function']=true,['if']=true,['in']=true,
        ['local']=true,['nil']=true,['not']=true,['or']=true,['repeat']=true,['return']=true,
        ['then']=true,['true']=true,['until']=true,['while']=true}
    local value
    value=function(depth)
        skip(); local a=p
        count=count+1
        if count>cap.values then fail('exceeded values limit '..cap.values) end
        local c=source:sub(p,p)
        local v, shape, keys
        if c=='{' then
            if depth>cap.depth then fail('exceeded depth limit '..cap.depth) end
            p=p+1; v={}; keys={}
            local implicit=1
            skip()
            while source:sub(p,p)~='}' do
                local key, keyspan
                local ka=p
                if source:sub(p,p)=='[' then
                    p=p+1; skip()
                    local kn=value(depth+1)
                    key=kn.value
                    if type(key)~='string' and not (type(key)=='number' and key==math.floor(key)) then
                        fail('key must be literal string or integer',ka)
                    end
                    if type(key)=='number' and math.abs(key)>9007199254740991 then fail('integer key is not exact',ka) end
                    expect(']'); expect('='); keyspan=kn.span
                else
                    local name=source:match('^([A-Za-z_][A-Za-z0-9_]*)',p)
                    local saved=p
                    if name then p=p+#name; skip() end
                    if name and source:sub(p,p)=='=' then
                        if reserved[name] then fail('reserved word cannot be an identifier key',saved) end
                        key=name; keyspan=span(saved,saved+#name); p=p+1
                    else p=saved; key=implicit; implicit=implicit+1; keyspan=span(p,p) end
                end
                if v[key]~=nil then fail('duplicate key '..tostring(key),ka) end
                v[key]=value(depth+1); keys[key]=keyspan
                local kind=type(key)=='number' and 'array' or 'map'
                if shape and kind~=shape then fail('mixed list/map table',ka) end
                shape=kind
                skip(); c=source:sub(p,p)
                if c==',' or c==';' then p=p+1; skip()
                elseif c~='}' then fail('expected separator or }; unsupported expressions use custom-Lua copy workflow') end
            end
            p=p+1
        elseif c=='"' or c=="'" then v=quoted()
        elseif source:match('^[A-Za-z_]',p) then
            local word=source:match('^[A-Za-z_][A-Za-z0-9_]*',p); p=p+#word
            if word=='true' then v=true elseif word=='false' then v=false
            else fail('unsupported value '..word..'; use custom-Lua copy workflow',a) end
        else
            local token=source:match('^[+-]?%d+%.?%d*[eE][+-]?%d+',p)
                or source:match('^[+-]?%.%d+[eE][+-]?%d+',p)
                or source:match('^[+-]?%d+%.?%d*',p) or source:match('^[+-]?%.%d+',p)
            if not token then fail('expected literal; use custom-Lua copy workflow') end
            v=tonumber(token); p=p+#token
            if not v or v~=v or v==math.huge or v==-math.huge then fail('number must be finite',a) end
        end
        return {value=v, span=span(a,p), shape=shape, keys=keys}
    end
    skip()
    if source:sub(p,p+5)~='return' or source:sub(p+6,p+6):match('[A-Za-z0-9_]') then fail('expected return') end
    p=p+6; skip()
    if source:sub(p,p)~='{' then fail('root must be a literal table') end
    local root=value(1)
    skip(); if p<=#source then fail('unexpected trailing input; use custom-Lua copy workflow') end
    return {root=root, source=source, file=file, limits=cap}
end

local function fail(n,context,message)
    local s=n.span
    error(s.file..':'..s.line..':'..s.column..': '..context..': '..message,0)
end
local function map(n,context)
    if not n or type(n.value)~='table' or n.shape=='array' then fail(n,context,'expected named map') end
    return n.value
end
local function fields(n,allowed,context)
    local t=map(n,context)
    for k,v in pairs(t) do if not allowed[k] then fail(v,context..'.'..k,'unknown field') end end
    return t
end
local function required(t,k,n,context)
    if not t[k] then fail(n,context,'missing '..k) end
    return t[k]
end
local function scalar(n,kind,context,nonempty)
    if type(n.value)~=kind or (nonempty and n.value=='') then fail(n,context,'expected '..kind..(nonempty and ' (nonempty)' or '')) end
    return n.value
end
local function integer(n,context)
    local v=scalar(n,'number',context)
    if v~=math.floor(v) or math.abs(v)>9007199254740991 then fail(n,context,'expected exact integer') end
    return v
end
local function array(n,context)
    if type(n.value)~='table' or n.shape=='map' then fail(n,context,'expected ordered array') end
    local count=0
    for k in pairs(n.value) do
        count=count+1
        if k<1 or k~=math.floor(k) then fail(n,context,'array positions must be positive integers') end
    end
    for i=1,count do if not n.value[i] then fail(n,context,'array has a hole at '..i) end end
    return n.value,count
end
local function root(doc,kind,allowed)
    local t=fields(doc.root,allowed,kind)
    if scalar(required(t,'schema',doc.root,kind),'number',kind..'.schema')~=1 then fail(t.schema,kind,'unsupported schema; expected 1') end
    if scalar(required(t,'kind',doc.root,kind),'string',kind..'.kind')~=kind then fail(t.kind,kind,'wrong kind; expected '..kind) end
    return t
end
local function id(n,context)
    local s=scalar(n,'string',context,true)
    if not s:match('^[A-Za-z][A-Za-z0-9_]*$') then fail(n,context,'invalid stable ID '..s) end
    return s
end
local function bounded_map(n,context,cap)
    local t=map(n,context); local count=0
    for k in pairs(t) do
        count=count+1
        if count>cap then fail(n,context,'exceeded records limit '..cap) end
        if not k:match('^[A-Za-z][A-Za-z0-9_]*$') then fail(n,context,'invalid stable ID '..k) end
    end
    return t
end
local function constraints(t,context,out)
    if t.bag then out.bag=scalar(t.bag,'string',context..'.bag',true) end
    if t.priority then out.priority=integer(t.priority,context..'.priority') end
end
function M.catalog(doc)
    local t=root(doc,'equipment',{schema=true,kind=true,items=true})
    local items=bounded_map(required(t,'items',doc.root,'equipment'),'equipment.items',doc.limits.records)
    local out={}
    for k,n in pairs(items) do
        local c='equipment.items.'..k
        local r=fields(n,{name=true,label=true,augments=true,bag=true,priority=true},c)
        local item={name=scalar(required(r,'name',n,c),'string',c..'.name',true)}
        scalar(required(r,'label',n,c),'string',c..'.label',true)
        constraints(r,c,item)
        if r.augments then
            item.augments={}
            for i,a in ipairs(array(r.augments,c..'.augments')) do item.augments[i]=scalar(a,'string',c..'.augments['..i..']') end
        end
        out[k]={item=item, label=r.label.value, span=copy(n.span)}
    end
    return out
end

-- Aliases verified against GearSwap/statics.lua slot_map (2026-11-02).
local slots={}
for _,s in ipairs({'main','sub','range','ammo','head','neck','ear1','ear2','body','hands','ring1','ring2','back','waist','legs','feet'}) do slots[s]=s end
for a,s in pairs({ranged='range',left_ear='ear1',right_ear='ear2',learring='ear1',rearring='ear2',lear='ear1',rear='ear2',left_ring='ring1',right_ring='ring2',lring='ring1',rring='ring2'}) do slots[a]=s end
local function path(n,context)
    local a,count=array(n,context)
    if count==0 then fail(n,context,'path must not be empty') end
    local out={}
    for i,v in ipairs(a) do
        if type(v.value)=='string' then
            out[i]=scalar(v,'string',context)
        else out[i]=integer(v,context); if out[i]<0 then fail(v,context,'negative path component') end end
    end
    return out
end
local function pathkey(p)
    local out={}
    for _,v in ipairs(p) do out[#out+1]=type(v)..':'..#tostring(v)..':'..tostring(v) end
    return table.concat(out,'/')
end
function M.resolve(doc,catalog,options)
    options=options or {}
    local t=root(doc,'sets',{schema=true,kind=true,job=true,definitions=true})
    local job=scalar(required(t,'job',doc.root,'sets'),'string','sets.job',true)
    local materialized=0
    local function materialize(value,node,context)
        return copy(value,nil,function()
            materialized=materialized+1
            if materialized>doc.limits.materialized_values then
                fail(node,context,'exceeded materialized_values limit '..doc.limits.materialized_values)
            end
        end)
    end
    if not job:match('^[A-Z][A-Z][A-Z]?$') or (options.job and options.job~=job) then fail(t.job,'sets.job','unexpected job '..job) end
    local defs=bounded_map(required(t,'definitions',doc.root,job),'sets.definitions',doc.limits.records)
    local parsed, destinations, aliases={},{},{}
    for k,n in pairs(defs) do
        local c=job..' set '..k
        local r=fields(n,{path=true,bases=true,slots=true,aliases=true},c)
        local p=path(required(r,'path',n,c),c..'.path'); local key=pathkey(p)
        if destinations[key] then fail(r.path,c,'duplicate canonical path') end
        destinations[key]=k
        local d={node=n,path=p,bases={},slots={}}; parsed[k]=d
        if r.bases then
            for _,b in ipairs(array(r.bases,c..'.bases')) do d.bases[#d.bases+1]={id=id(b,c..'.bases'),node=b} end
        end
        if r.slots then
            for raw,v in pairs(map(r.slots,c..'.slots')) do
                local s=slots[raw:lower()]
                if not s then fail(v,c..' slot '..raw,'unknown slot') end
                if d.slots[s] then fail(v,c..' slot '..s,'duplicate slot alias') end
                d.slots[s]=v
            end
        end
        if r.aliases then
            for _,a in ipairs(array(r.aliases,c..'.aliases')) do aliases[#aliases+1]={path=path(a,c..'.aliases'),id=k,node=a} end
        end
    end
    local memo, visiting, chain={},{},{}
    local resolve
    resolve=function(k,at)
        if visiting[k] then fail(at,job..' set '..k,'inheritance cycle: '..table.concat(chain,' -> ')..' -> '..k) end
        if #chain>=doc.limits.references then fail(at,job..' set '..k,'exceeded references limit '..doc.limits.references) end
        if memo[k] then
            if #chain+memo[k].depth>doc.limits.references then fail(at,job..' set '..k,'exceeded references limit '..doc.limits.references) end
            return memo[k]
        end
        local d=parsed[k]
        if not d then fail(at,job..' set '..chain[#chain],'missing base '..k) end
        visiting[k]=true; chain[#chain+1]=k
        local out={equipment={},provenance={},depth=1}
        for _,b in ipairs(d.bases) do
            local base=resolve(b.id,b.node)
            out.depth=math.max(out.depth,base.depth+1)
            for s,v in pairs(base.equipment) do out.equipment[s]=base.provenance[s].empty and options.empty or materialize(v,d.node,job..' set '..k..' slot '..s) end
            for s,v in pairs(base.provenance) do
                if v.omitted then out.equipment[s]=nil end
                out.provenance[s]=materialize(v,d.node,job..' set '..k..' slot '..s)
                table.insert(out.provenance[s].chain,1,k)
                out.provenance[s].override=false
            end
        end
        for s,n in pairs(d.slots) do
            local c=job..' set '..k..' slot '..s
            local item,ref,omitted,isempty
            if type(n.value)=='string' then item=scalar(n,'string',c,true)
            else
                local r=fields(n,{ref=true,bag=true,priority=true,empty=true,omit=true},c)
                local modes=(r.ref and 1 or 0)+(r.empty and 1 or 0)+(r.omit and 1 or 0)
                if modes~=1 then fail(n,c,'expected exactly one of ref, empty, omit') end
                if r.ref then
                    ref=id(r.ref,c)
                    if not catalog[ref] then fail(r.ref,c,'missing catalog reference '..ref) end
                    item=materialize(catalog[ref].item,n,c); constraints(r,c,item)
                else
                    if r.bag or r.priority then fail(n,c,'constraints require ref') end
                    local marker=r.empty or r.omit
                    if marker.value~=true then fail(marker,c,'marker must be true') end
                    omitted=r.omit~=nil; isempty=not omitted
                    if isempty then
                        if options.empty==nil then fail(n,c,'host must supply GearSwap empty sentinel') end
                        item=options.empty
                    end
                end
            end
            if item and not isempty and options.validate_item then
                local accepted,reason=options.validate_item(item,s)
                if not accepted then fail(n,c,reason or 'item is not eligible for slot') end
            end
            out.equipment[s]=item
            out.provenance[s]={defining_set=k,chain={k},record_id=ref,span=materialize(n.span,n,c),
                catalog_span=ref and materialize(catalog[ref].span,n,c) or nil,override=true,omitted=omitted or false,
                empty=isempty or false,bag=type(item)=='table' and item.bag or nil,
                priority=type(item)=='table' and item.priority or nil}
        end
        chain[#chain]=nil; visiting[k]=nil; memo[k]=out
        return out
    end
    for k,d in pairs(parsed) do resolve(k,d.node) end
    -- Materialize distinct canonical tables first. Never follow an existing alias while mounting.
    local runtime, nodes, owners, canonical_tables={},{},{},{}
    local ordered={}
    for k,d in pairs(parsed) do ordered[#ordered+1]={id=k,path=d.path,node=d.node} end
    table.sort(ordered,function(a,b) return #a.path<#b.path end)
    local function mount(entry,alias)
        local current=runtime; local prefix={}
        for i,key in ipairs(entry.path) do
            prefix[i]=key; local pk=pathkey(prefix)
            local slot=type(key)=='string' and slots[key:lower()]
            if canonical_tables[current] and slot then
                fail(entry.node,job..' set '..entry.id,'path collides with equipment slot '..key)
            end
            if i==#entry.path then
                local target=nodes[entry.id]
                if owners[pk] then fail(entry.node,job..' set '..entry.id,'conflicting path destination') end
                if current[key]~=nil then fail(entry.node,job..' set '..entry.id,'path overwrites namespace') end
                current[key]=target; owners[pk]=entry.id
            else
                if current[key]==nil then current[key]={} end
                if type(current[key])~='table' then fail(entry.node,job,'path is not a table') end
                current=current[key]
            end
        end
    end
    for k,r in pairs(memo) do
        nodes[k]={}
        canonical_tables[nodes[k]]=k
        for s,v in pairs(r.equipment) do
            nodes[k][s]=r.provenance[s] and r.provenance[s].empty and options.empty or materialize(v,parsed[k].node,job..' set '..k..' slot '..s)
        end
    end
    for _,e in ipairs(ordered) do mount(e,false) end
    table.sort(aliases,function(a,b) return #a.path<#b.path end)
    for _,e in ipairs(aliases) do mount(e,true) end
    return {job=job,sets=runtime,definitions=memo,paths=parsed}
end

-- Schemas are maintained code: {type='map',fields={...}}, {type='array',item=...},
-- or scalar {type='boolean'|'string'|'number'|'integer', enum={...}, required=true}.
-- Empty table shape is determined by schema, never by Lua's length operator.
local function merge(n,schema,base,context)
    if type(n.value)=='table' and n.value.remove then
        fields(n,{remove=true},context)
        if n.value.remove.value~=true then fail(n,context,'remove marker must be true') end
        if schema.required then fail(n,context,'required entry cannot be removed') end
        return nil
    end
    local kind=schema.type
    if kind=='map' then
        local out=copy(base or {})
        for k,v in pairs(map(n,context)) do
            local child=(schema.fields or {})[k]
            if not child then fail(v,context..'.'..k,'unknown setting') end
            out[k]=merge(v,child,out[k],context..'.'..k)
        end
        return out
    elseif kind=='array' then
        local out={}
        for i,v in ipairs(array(n,context)) do
            out[i]=merge(v,schema.item,nil,context..'['..i..']')
            if out[i]==nil then fail(v,context,'cannot remove array element') end
        end
        return out
    end
    local v=kind=='integer' and integer(n,context) or scalar(n,kind,context)
    if schema.enum then
        local found=false; for _,allowed in ipairs(schema.enum) do if v==allowed then found=true end end
        if not found then fail(n,context,'unsupported value '..tostring(v)) end
    end
    return v
end
local function complete(value,schema,n,context)
    if value==nil then if schema.required then fail(n,context,'missing required entry') end; return end
    if schema.type=='map' then
        if type(value)~='table' then fail(n,context,'expected map') end
        for k in pairs(value) do if not (schema.fields or {})[k] then fail(n,context..'.'..k,'unknown setting') end end
        for k,child in pairs(schema.fields or {}) do complete(value[k],child,n,context..'.'..k) end
    elseif schema.type=='array' then
        if type(value)~='table' then fail(n,context,'expected array') end
        for i,v in ipairs(value) do complete(v,schema.item,n,context..'['..i..']') end
    else
        local expected=schema.type=='integer' and 'number' or schema.type
        if type(value)~=expected then fail(n,context,'expected '..expected) end
        if schema.type=='integer' and (value~=math.floor(value) or math.abs(value)>9007199254740991) then fail(n,context,'expected exact integer') end
        if schema.enum then
            local found=false; for _,allowed in ipairs(schema.enum) do if value==allowed then found=true end end
            if not found then fail(n,context,'unsupported value '..tostring(value)) end
        end
    end
end
local function groups(doc,kind,job)
    local t=root(doc,kind,{schema=true,kind=true,shared=true,jobs=true})
    local shared=required(t,'shared',doc.root,kind)
    map(shared,kind..'.shared')
    local jobs=map(required(t,'jobs',doc.root,kind),kind..'.jobs')
    for k,n in pairs(jobs) do
        if not k:match('^[A-Z][A-Z][A-Z]?$') then fail(n,kind..'.jobs','invalid job '..k) end
        map(n,kind..'.jobs.'..k)
    end
    return shared,jobs[job]
end
function M.settings(doc,job,schema,defaults)
    local shared,localjob=groups(doc,'settings',job)
    local result=merge(shared,schema,defaults,'settings.shared')
    if localjob then result=merge(localjob,schema,result,'settings.jobs.'..job) end
    complete(result,schema,doc.root,'settings')
    return result
end

local function chord(key)
    -- Windower: ! Alt, ^ Ctrl, @ Win, # Apps, ~ Shift, % suppresses in chat.
    -- Deliberately bounded keys. Broaden through maintained validation when needed.
    local modifiers,name=key:match('^([!%^@#~%%]*)([a-z0-9.+*/=-]+)$')
    if not modifiers then return false end
    local seen={}; for c in modifiers:gmatch('.') do if seen[c] then return false end; seen[c]=true end
    local normalized=''
    for _,c in ipairs({'!','^','@','#','~','%'}) do if seen[c] then normalized=normalized..c end end
    normalized=normalized..name
    if name:match('^[a-z0-9]$') then return normalized end
    if name=='-' or name=='=' or name:match('^numpad[0-9]$')
        or name=='numpadenter' or name=='numpad.' or name=='numpad+'
        or name=='numpad-' or name=='numpad*' or name=='numpad/' then return normalized end
    local f=tonumber(name:match('^f(%d+)$'))
    if f and f>=1 and f<=12 and name=='f'..f then return normalized end
    return ({escape=true,tab=true,enter=true,space=true,backspace=true,insert=true,delete=true,
        home=true,['end']=true,pageup=true,pagedown=true,up=true,down=true,left=true,right=true})[name] and normalized or false
end
M.normalize_chord=chord
function M.hotkeys(doc,job,commands,defaults)
    local shared,localjob=groups(doc,'hotkeys',job)
    local out=copy(defaults or {})
    local function apply(n,context)
        local seen={}
        for key,v in pairs(map(n,context)) do
            local c=context..'.'..key
            local normalized=chord(key)
            if not normalized then fail(v,c,'unsupported key chord') end
            if seen[normalized] then fail(v,c,'duplicate equivalent key chord') end
            seen[normalized]=true; key=normalized
            local r=fields(v,{command=true,args=true,remove=true},c)
            if r.remove then
                fields(v,{remove=true},c)
                if r.remove.value~=true then fail(v,c,'remove marker must be true') end
                out[key]=nil
            else
                local command=scalar(required(r,'command',v,c),'string',c..'.command',true)
                local spec=commands[command]
                if not spec or (spec.jobs and not spec.jobs[job]) then fail(r.command,c,'unknown or inapplicable command '..command) end
                local args={}
                if r.args then
                    if not spec.args then fail(r.args,c,'command takes no arguments') end
                    args=merge(r.args,spec.args,nil,c..'.args'); complete(args,spec.args,r.args,c..'.args')
                elseif spec.args then complete(nil,spec.args,v,c..'.args') end
                out[key]={command=command,args=args}
            end
        end
    end
    apply(shared,'hotkeys.shared'); if localjob then apply(localjob,'hotkeys.jobs.'..job) end
    return out
end

-- Atomic pure candidate preparation. This does not choose a profile, enter a
-- framework, attach controls, or publish ready state. Those are adapter duties.
function M.prepare(sources,options)
    local docs,missing={},{}
    local names={'Equipment.lua','Settings.lua','Hotkeys.lua','Sets/'..options.job..'.lua'}
    for _,name in ipairs(names) do if not sources[name] then missing[#missing+1]=name end end
    if #missing>0 then error('missing required profile file '..table.concat(missing,', ')..'; create it from PlayerSystem/examples',0) end
    for _,name in ipairs(names) do
        docs[name]=M.parse(sources[name],(options.profile or '<profile>')..'/'..name,options.limits)
    end
    local catalog=M.catalog(docs['Equipment.lua'])
    local sets=M.resolve(docs['Sets/'..options.job..'.lua'],catalog,options)
    local settings=M.settings(docs['Settings.lua'],options.job,options.settings_schema,options.defaults)
    local hotkeys=M.hotkeys(docs['Hotkeys.lua'],options.job,options.commands,options.hotkeys)
    return {catalog=catalog,resolved=sets,settings=settings,hotkeys=hotkeys,documents=docs}
end
return M
