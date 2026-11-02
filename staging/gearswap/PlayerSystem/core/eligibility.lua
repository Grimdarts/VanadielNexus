-- Resource eligibility only. Never infers ownership, augments, race, or rank.
local M={}
local bits={main=0,sub=1,range=2,ammo=3,head=4,body=5,hands=6,legs=7,feet=8,neck=9,waist=10,
    ear1=11,ear2=12,ring1=13,ring2=14,back=15}
function M.validator(items,bags,band,job_id,level)
    assert(type(items)=='table' and next(items),'item resources unavailable; cannot validate profile gear')
    local by_name,by_bag={},{}
    local function index(name,row)
        if not name then return end
        local key=name:lower()
        if by_name[key]==nil then by_name[key]=row
        elseif by_name[key]~=row then by_name[key]=false end
    end
    for _,row in pairs(items) do
        index(row.en or row.english,row)
        index(row.enl or row.english_log,row)
    end
    for _,row in pairs(bags or {}) do
        local name=row.en or row.english
        if name and row.equippable then by_bag[name:lower():gsub('%s+','')]=true end
    end
    local function contains(value,index)
        if type(value)=='table' then return value[index]==true end -- Windower resources Set
        return type(value)=='number' and band(value,2^index)~=0 -- raw res bitmask
    end
    return function(item,slot)
        local name=type(item)=='table' and item.name or item
        local row=by_name[name:lower()]
        if row==false then return false,'ambiguous item resource '..name end
        if not row then return false,'unknown item resource '..name end
        if not row.slots or not row.jobs then return false,'item has no equipment eligibility '..name end
        local allowed=contains(row.slots,bits[slot])
        if slot=='ear1' or slot=='ear2' then allowed=contains(row.slots,11) or contains(row.slots,12) end
        if slot=='ring1' or slot=='ring2' then allowed=contains(row.slots,13) or contains(row.slots,14) end
        if not allowed then return false,name..' cannot equip in '..slot end
        if not contains(row.jobs,job_id) or (row.level or 0)>level then return false,name..' is not eligible for this job/level' end
        if type(item)=='table' and item.bag then
            if not next(by_bag) then return false,'bag resources unavailable' end
            local key=item.bag:lower():gsub('%s+','')
            if key=='wardrobe1' then key='wardrobe' end
            if not by_bag[key] then return false,'unknown equipment bag '..item.bag end
        end
        return true
    end
end
return M
