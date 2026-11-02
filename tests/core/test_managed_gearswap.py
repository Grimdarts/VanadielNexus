"""Staged v1 contract, exercised by LuaJIT 2.1 and an isolated Python consumer."""
import importlib.util
import multiprocessing
import os
import sys
from pathlib import Path

import pytest

if os.environ.get('VN_LUA_RUNTIME'):
    sys.path.insert(0, os.environ['VN_LUA_RUNTIME'])
lupa = pytest.importorskip('lupa.luajit21', reason='managed GearSwap requires LuaJIT')

ROOT = Path(__file__).parents[2] / 'staging' / 'gearswap'
MODULE = ROOT / 'PlayerSystem' / 'core' / 'managed_data.lua'
EXAMPLES = ROOT / 'PlayerSystem' / 'examples'


@pytest.fixture(autouse=True)
def quiet_faulthandler():
    import faulthandler
    enabled = faulthandler.is_enabled()
    faulthandler.disable()
    yield
    if enabled:
        faulthandler.enable()


@pytest.fixture
def env():
    lua = lupa.LuaRuntime(encoding=None, unpack_returned_tuples=True)
    module = lua.execute(MODULE.read_bytes())
    lua.globals()[b'M'] = module
    return lua, module


def parse(env, text, limits=None):
    lua, module = env
    return module[b'parse'](text.encode() if isinstance(text, str) else text, b'fixture.lua',
                            lua.table_from(limits or {}))


def evaluate(env, code):
    return env[0].execute(code.encode())


def catalog(env, body=''):
    return env[1][b'catalog'](parse(env, 'return {schema=1,kind="equipment",items={' + body + '}}'))


def resolve(env, body, items='', **options):
    lua, module = env
    opts = {b'job': b'SMN', b'empty': lua.table_from({b'name': b'empty'})}
    opts.update(options)
    return module[b'resolve'](parse(env, 'return {schema=1,kind="sets",job="SMN",definitions={' + body + '}}'),
                               catalog(env, items), lua.table_from(opts))


def test_literals_comments_spans(env):
    source = '\ufeff-- header\r\nreturn {\r\n --[==[ comment ]=] still comment ]==]\r\n title="é", n=-1.25e+2; yes=true, no=false, list={"a",[2]="b",}, } -- end'
    doc = parse(env, source)
    root = doc[b'root'][b'value']
    assert root[b'n'][b'value'] == -125
    assert root[b'no'][b'value'] is False
    title = root[b'title']
    span = title[b'span']
    assert span[b'line'] == 4 and span[b'column'] == 8
    assert source.encode()[span[b'start'] - 1:span[b'finish'] - 1] == '"é"'.encode()
    assert doc[b'source'] == source.encode()


@pytest.mark.parametrize('literal,expected', [
    (r'"a\n\t\a\b\f\r\v\\\"\039"', b'a\n\t\x07\x08\x0c\r\x0b\\"\''),
    ('"a\\\r\nb"', b'a\nb'), (r'"\195\169"', 'é'.encode()),
    ('+.25E2', 25), ('-0.5', -.5), ('1.', 1),
])
def test_literals(env, literal, expected):
    assert parse(env, 'return {value=' + literal + '}')[b'root'][b'value'][b'value'][b'value'] == expected


@pytest.mark.parametrize('source,message', [
    ('return {a=1,a=2}', 'duplicate key'), ('return {"a",[1]="b"}', 'duplicate key'),
    ('return {"a",name="b"}', 'mixed list/map'), ('return {a=nil}', 'unsupported value'),
    ('return {a=gear.cape}', 'unsupported value'), ('return {a=function() end}', 'unsupported value'),
    ('return {a=set_combine({},{})}', 'unsupported value'), ('return {a="a".."b"}', 'expected separator'),
    ('return {a=1+2}', 'expected separator'), ('return {a=[[x]]}', 'expected literal'),
    ('return {a=0x10}', 'expected separator'), ('return {a=1e999}', 'finite'),
    ('return {a="\\256"}', '255'), ('return {a="\\255"}', 'invalid UTF-8'),
    ('return {a="\\z"}', 'unsupported string escape'), ('return {a="x\ny"}', 'unescaped newline'),
    ('return {a="x}', 'unterminated string'), ('return {} --[=[x', 'unterminated long comment'),
    ('return {} print("bad")', 'trailing input'), ('returning {}', 'expected return'),
    ('return true', 'root must'), ('return {true=1}', 'reserved word'),
    ('return {[true]=1}', 'key must'), ('return {[1.5]=1}', 'key must'),
    ('return {[9007199254740992]=1}', 'integer key is not exact'),
    (b'return {a="\xff"}', 'invalid UTF-8'), (b'return {a="\xed\xa0\x80"}', 'invalid UTF-8'),
])
def test_rejected_grammar(env, source, message):
    with pytest.raises(lupa.LuaError, match=message):
        parse(env, source)


def test_profile_code_is_never_executed(env):
    env[0].globals()[b'touched'] = False
    with pytest.raises(lupa.LuaError):
        parse(env, 'return {a=(function() touched=true return 1 end)()}')
    assert env[0].globals()[b'touched'] is False


@pytest.mark.parametrize('source,limit,value,message', [
    ('return {}', b'bytes', 8, 'bytes limit'),
    ('return {{{}}}', b'depth', 2, 'depth limit'),
    ('return {1,2}', b'values', 2, 'values limit'),
])
def test_parser_limits(env, source, limit, value, message):
    with pytest.raises(lupa.LuaError, match=message):
        parse(env, source, {limit: value})


ITEMS = 'cape={label="Cape A",name="Cape",augments={"Pet +1"},bag="Wardrobe",priority=1}'


def test_ordered_inheritance_reference_override_omit_and_isolation(env):
    result = resolve(env, '''
      final={path={"midcast","Pet","Magic.Acc"},bases={"base","later"},slots={body={empty=true},right_ear="Ear"}},
      base={path={"base"},slots={back={ref="cape"},head="Old",neck="Old Neck"}},
      later={path={"later"},slots={head="New",neck={omit=true}}},
      constrained={path={"constrained"},bases={"base"},slots={back={ref="cape",bag="Wardrobe 2",priority=9}}},
      blank={path={"blank"}},
    ''', ITEMS)
    defs = result[b'definitions']
    gear = result[b'sets'][b'midcast'][b'Pet'][b'Magic.Acc']
    assert gear[b'head'] == b'New' and gear[b'neck'] is None and gear[b'ear2'] == b'Ear'
    assert gear[b'body'][b'name'] == b'empty'
    assert len(result[b'sets'][b'blank']) == 0
    p = defs[b'final'][b'provenance'][b'back']
    assert list(p[b'chain'].values()) == [b'final', b'base']
    assert p[b'defining_set'] == b'base' and p[b'record_id'] == b'cape' and not p[b'override']
    assert p[b'span'][b'file'] == b'fixture.lua' and p[b'catalog_span'] is not None
    assert defs[b'final'][b'provenance'][b'neck'][b'omitted']
    assert result[b'sets'][b'constrained'][b'back'][b'bag'] == b'Wardrobe 2'
    assert result[b'sets'][b'base'][b'back'][b'bag'] == b'Wardrobe'
    gear[b'back'][b'augments'][1] = b'Changed'
    assert result[b'sets'][b'base'][b'back'][b'augments'][1] == b'Pet +1'
    assert defs[b'final'][b'equipment'][b'back'][b'augments'][1] == b'Pet +1'


def test_replacement_does_not_merge_augments(env):
    result = resolve(env, 'a={path={"a"},slots={back={ref="cape"}}},b={path={"b"},bases={"a"},slots={back="Plain"}}', ITEMS)
    assert result[b'sets'][b'b'][b'back'] == b'Plain'


def test_alias_identity_and_self_cycle(env):
    result = resolve(env, 'perp={path={"idle","Avatar"},aliases={{"engaged"},{"perp"},{"engaged","Perp"}},slots={head="Hat"}}')
    env[0].globals()[b'R'] = result
    assert evaluate(env, 'return R.sets.idle.Avatar==R.sets.engaged and R.sets.engaged==R.sets.perp and R.sets.engaged.Perp==R.sets.engaged')
    assert evaluate(env, 'local c=M.copy(R.sets); return c~=R.sets and c.engaged.Perp==c.engaged and c.engaged==c.perp')


@pytest.mark.parametrize('body,message', [
    ('a={path={"a"},bases={"missing"}}', 'missing base missing'),
    ('a={path={"a"},bases={"b"}},b={path={"b"},bases={"a"}}', 'inheritance cycle: .* -> .* ->'),
    ('a={path={"a"},slots={back={ref="missing"}}}', 'SMN set a slot back: missing catalog reference missing'),
    ('a={path={"a"},slots={wat="Hat"}}', 'unknown slot'),
    ('a={path={"a"},slots={ear1="A",left_ear="B"}}', 'duplicate slot alias'),
    ('a={path={"a"},slots={head={empty=false}}}', 'marker must be true'),
    ('a={path={"a"},slots={head={omit=true,bag="Bag"}}}', 'constraints require ref'),
    ('a={path={"a"},slots={head={ref="cape",empty=true}}}', 'exactly one'),
    ('a={path={"a"},slots={head={name="Hat"}}}', 'unknown field'),
    ('a={path={"a"}},b={path={"a"}}', 'duplicate canonical path'),
    ('a={path={"a"},aliases={{"b"}}},b={path={"b"}}', 'conflicting path'),
    ('a={path={"a"},aliases={{"a"}}}', 'conflicting path'),
    ('a={path={"a"},aliases={{"x"},{"x"}}}', 'conflicting path'),
    ('a={path={"a"},slots={back={ref="cape"}}},b={path={"a","back","extra"}}', 'collides with equipment'),
    ('a={path={"a"},slots={ear1="Ear"}},b={path={"a","left_ear","extra"}}', 'collides with equipment'),
    ('a={path={"a"},slots={ear1="Ear"}},b={path={"a","Left_Ear","extra"}}', 'collides with equipment'),
    ('a={path={"a"},slots={ear1="Ear"}},b={path={"a","EAR1","extra"}}', 'collides with equipment'),
    ('a={path={"a"}},b={path={"a","Head"}}', 'collides with equipment'),
    ('a={path={"a"},slots={head={omit=true}}},b={path={"a","head"}}', 'collides with equipment'),
    ('a={path={"a"}},b={path={"b"},aliases={{"a","lear"}}}', 'collides with equipment'),
    ('a={path={"a"},slots={range="Bow"}},b={path={"b"},aliases={{"a","ranged","extra"}}}', 'collides with equipment'),
    ('a={path={}}', 'path must not be empty'), ('a={path={-1}}', 'negative path'),
    ('a={path={[2]="a"}}', 'hole'), ('a={path={true}}', 'expected number'),
    ('a={path={"a"},bases={[0]="b"}}', 'positive integers'),
    ('a={path={"a"},unexpected=true}', 'unknown field'),
])
def test_resolution_errors(env, body, message):
    with pytest.raises(lupa.LuaError, match=message):
        resolve(env, body, ITEMS)


@pytest.mark.parametrize('items,message', [
    ('a={name="Hat"}', 'missing label'), ('a={label="Hat",name=""}', 'nonempty'),
    ('a={name="Hat",label="Hat",extra=1}', 'unknown field'),
    ('a={name="Hat",label="Hat",priority=1.5}', 'exact integer'),
    ('a={name="Hat",label="Hat",bag=1}', 'expected string'),
    ('a={name="Hat",label="Hat",augments={[2]="A"}}', 'hole'),
    ('["bad-id"]={name="Hat",label="Hat"}', 'invalid stable ID'),
])
def test_catalog_errors(env, items, message):
    with pytest.raises(lupa.LuaError, match=message):
        catalog(env, items)


def test_empty_augments_are_distinct_from_unspecified(env):
    cat = catalog(env, 'a={name="Cape",label="A",augments={}},b={name="Cape",label="B"}')
    assert len(cat[b'a'][b'item'][b'augments']) == 0
    assert cat[b'b'][b'item'][b'augments'] is None


def test_schema_version_kind_and_missing_fields(env):
    for text, message in [('return {schema=2,kind="equipment",items={}}', 'unsupported schema'),
                          ('return {schema=1,kind="sets",items={}}', 'wrong kind'),
                          ('return {schema=1,kind="equipment"}', 'missing items')]:
        with pytest.raises(lupa.LuaError, match=message):
            env[1][b'catalog'](parse(env, text))


SCHEMA = '''{type='map',required=true,fields={
    lag_compensation={type='boolean',required=true},
    display={type='map',fields={size={type='integer'},color={type='string',enum={'blue','gold'}}}},
    list={type='array',item={type='string'}},optional={type='boolean'}
}}'''


def settings(env, shared, job='{}'):
    env[0].globals()[b'D'] = parse(env, 'return {schema=1,kind="settings",shared=' + shared + ',jobs={SMN=' + job + '}}')
    return evaluate(env, "return M.settings(D,'SMN'," + SCHEMA + ",{lag_compensation=true,display={size=9,color='blue'},list={'a','b'},optional=true})")


def test_settings_merge_list_replace_and_remove(env):
    value = settings(env, '{display={size=7},list={"c"}}', '{lag_compensation=false,list={},optional={remove=true},display={color="gold"}}')
    assert value[b'lag_compensation'] is False
    assert value[b'display'][b'size'] == 7 and value[b'display'][b'color'] == b'gold'
    assert len(value[b'list']) == 0 and value[b'optional'] is None


@pytest.mark.parametrize('shared,message', [
    ('{lag_compensation={remove=true}}', 'required entry'), ('{unknown=true}', 'unknown setting'),
    ('{lag_compensation="true"}', 'expected boolean'), ('{display={size=1.5}}', 'exact integer'),
    ('{display={color="red"}}', 'unsupported value'), ('{list={[2]="b"}}', 'hole'),
    ('{optional={remove=false}}', 'remove marker'), ('{optional={remove=true,x=1}}', 'unknown field'),
])
def test_settings_errors(env, shared, message):
    with pytest.raises(lupa.LuaError, match=message):
        settings(env, shared)


def hotkeys(env, shared, job='{}'):
    env[0].globals()[b'D'] = parse(env, 'return {schema=1,kind="hotkeys",shared=' + shared + ',jobs={SMN=' + job + '}}')
    return evaluate(env, """return M.hotkeys(D,'SMN',{
        toggle={jobs={SMN=true},args={type='array',required=true,item={type='string',enum={'lag_compensation'}}}},
        plain={},other={jobs={BLU=true}}
    },{})""")


def test_hotkeys_override_remove_and_arguments(env):
    out = hotkeys(env, '{["!f11"]={command="toggle",args={"lag_compensation"}},f9={command="plain"}}', '{f9={remove=true}}')
    assert out[b'f9'] is None and out[b'!f11'][b'args'][1] == b'lag_compensation'


@pytest.mark.parametrize('shared,message', [
    ('{f99={command="plain"}}', 'unsupported key'), ('{["!!f1"]={command="plain"}}', 'unsupported key'),
    ('{f1={command="missing"}}', 'unknown or inapplicable'), ('{f1={command="other"}}', 'unknown or inapplicable'),
    ('{f1={command="toggle"}}', 'missing required'), ('{f1={command="toggle",args={"bad"}}}', 'unsupported value'),
    ('{f1={command="plain",args={}}}', 'takes no arguments'), ('{f1={remove=false}}', 'marker must'),
    ('{f1={command="plain",remove=true}}', 'unknown field'),
])
def test_hotkeys_errors(env, shared, message):
    with pytest.raises(lupa.LuaError, match=message):
        hotkeys(env, shared)


def test_limits_and_real_sentinel(env):
    lua, module = env
    doc = parse(env, 'return {schema=1,kind="equipment",items={a={},b={}}}', {b'records': 1})
    with pytest.raises(lupa.LuaError, match='records limit'):
        module[b'catalog'](doc)
    doc = parse(env, 'return {schema=1,kind="sets",job="SMN",definitions={a={path={"a"},bases={"b"}},b={path={"b"}}}}', {b'references': 1})
    with pytest.raises(lupa.LuaError, match='references limit'):
        module[b'resolve'](doc, lua.table(), lua.table())
    doc = parse(env, 'return {schema=1,kind="sets",job="SMN",definitions={a={path={"a"},slots={head={empty=true}}},b={path={"b"},bases={"a"}}}}')
    with pytest.raises(lupa.LuaError, match='empty sentinel'):
        module[b'resolve'](doc, lua.table(), lua.table())
    lua.globals()[b'D'] = doc
    assert evaluate(env, 'local e={name="empty"}; local r=M.resolve(D,{}, {empty=e}); return r.sets.a.head==e and r.sets.b.head==e')


def example_args():
    sources = {name: (EXAMPLES / name).read_bytes() for name in ['Equipment.lua', 'Settings.lua', 'Hotkeys.lua', 'Sets/SMN.lua']}
    return {'sources': sources, 'options': {
        'job': 'SMN', 'profile': 'example', 'empty': {'name': 'empty'}, 'commands': {},
        'defaults': {'lag_compensation': True},
        'settings_schema': {'type': 'map', 'required': True, 'fields': {'lag_compensation': {'type': 'boolean', 'required': True}}},
    }}


def staged_run(args):
    # Importable helper for Windows spawn without adding staged code to the app.
    spec = importlib.util.spec_from_file_location('managed_worker', ROOT / 'managed_worker.py')
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    return worker.run(args)


def consumer(sender, args):
    try:
        sender.send(staged_run(args))
    finally:
        sender.close()


def test_staged_candidate_in_real_spawned_worker():
    ctx = multiprocessing.get_context('spawn')
    receiver, sender = ctx.Pipe(duplex=False)
    process = ctx.Process(target=consumer, args=(sender, example_args()), daemon=True)
    process.start()
    sender.close()
    try:
        assert receiver.poll(10), 'managed consumer timed out'
        result = receiver.recv()
        process.join(3)
        assert result['error'] == ''
        assert result['settings']['lag_compensation'] is True
        assert result['canonical']['pact_accuracy']['equipment']['back']['augments'][1].startswith('Pet:')
        assert process.exitcode == 0
    finally:
        if process.is_alive():
            process.terminate()
            process.join(3)
        receiver.close()


def test_worker_uses_same_parser_and_has_atomic_failure():
    args = example_args()
    assert staged_run(args)['error'] == ''
    args['sources']['Sets/SMN.lua'] = b'return {schema=1,kind="sets",job="SMN",definitions={a={path={"a"},slots={head={ref="missing"}}}}}'
    result = staged_run(args)
    assert 'SMN set a slot head: missing catalog reference missing' in result['error']
    assert 'canonical' not in result and 'settings' not in result
    del args['sources']['Equipment.lua']
    assert 'missing required profile file Equipment.lua' in staged_run(args)['error']
    result = staged_run({'operation': 'parse', 'source': b'return {x="\xff"}'})
    assert 'invalid UTF-8' in result['error']


def test_utf8_columns_and_key_spans(env):
    source = 'return {["é"]="one", next="two"}'
    doc = parse(env, source)
    assert doc[b'root'][b'value'][b'next'][b'span'][b'column'] == source.index('"two"') + 1
    key = doc[b'root'][b'keys'][b'next']
    assert doc[b'source'][key[b'start']-1:key[b'finish']-1] == b'next'


def test_resource_eligibility_callback(env):
    lua, _ = env
    lua.globals()[b'D'] = parse(env, 'return {schema=1,kind="sets",job="SMN",definitions={a={path={"a"},slots={head="Boots"}}}}')
    with pytest.raises(lupa.LuaError, match='SMN set a slot head: wrong slot'):
        evaluate(env, 'return M.resolve(D,{}, {validate_item=function(item,slot) return false,"wrong slot" end})')


def test_alias_cannot_overwrite_implicit_namespace(env):
    with pytest.raises(lupa.LuaError, match='overwrites namespace'):
        resolve(env, 'a={path={"idle","Avatar"}},b={path={"b"},aliases={{"idle"}}}')


def test_distinct_augmented_copies_preserve_ids_and_constraints(env):
    result = resolve(env, 'a={path={"a"},slots={back={ref="one"}}},b={path={"b"},slots={back={ref="two"}}}',
                     'one={label="Same",name="Cape",augments={"A"}},two={label="Same",name="Cape",augments={"B"}}')
    assert result[b'definitions'][b'a'][b'provenance'][b'back'][b'record_id'] == b'one'
    assert result[b'sets'][b'a'][b'back'][b'label'] is None
    assert result[b'sets'][b'b'][b'back'][b'augments'][1] == b'B'


def test_all_installed_slot_aliases(env):
    aliases = {'ranged': 'range', 'left_ear': 'ear1', 'right_ear': 'ear2', 'learring': 'ear1',
               'rearring': 'ear2', 'lear': 'ear1', 'rear': 'ear2', 'left_ring': 'ring1',
               'right_ring': 'ring2', 'lring': 'ring1', 'rring': 'ring2', 'HEAD': 'head', 'LEFT_EAR': 'ear1'}
    for alias, slot in aliases.items():
        result = resolve(env, 'a={path={"a"},slots={' + alias + '="Item"}}')
        assert result[b'sets'][b'a'][slot.encode()] == b'Item'


def test_equivalent_hotkey_chords_override_and_collide(env):
    out = hotkeys(env, '{["^!f1"]={command="plain"}}', '{["!^f1"]={remove=true}}')
    assert len(out) == 0
    with pytest.raises(lupa.LuaError, match='duplicate equivalent'):
        hotkeys(env, '{["^!f1"]={command="plain"},["!^f1"]={command="plain"}}')


def test_nested_required_array_fields_and_type_validation(env):
    env[0].globals()[b'D'] = parse(env, 'return {schema=1,kind="settings",shared={entries={{}}},jobs={}}')
    with pytest.raises(lupa.LuaError, match='missing required entry'):
        evaluate(env, "return M.settings(D,'SMN',{type='map',fields={entries={type='array',item={type='map',fields={name={type='string',required=true}}}}}}, {})")


def test_worker_instruction_budget_and_large_input_bound():
    result = staged_run({'operation': 'parse', 'source': b'return {' + b'1,' * 5000 + b'}', 'instruction_limit': 10000})
    assert 'managed instruction limit' in result['error']
    result = staged_run({'operation': 'parse', 'source': b' ' * (2097152 + 1)})
    assert 'bytes limit 2097152' in result['error']


def test_generic_paths_keep_punctuation_numbers_and_slot_names(env):
    result = resolve(env, 'a={path={"range",0,"A.B C",""},slots={head="Hat"}}')
    assert result[b'sets'][b'range'][0][b'A.B C'][b''][b'head'] == b'Hat'


def test_reference_limit_is_not_bypassed_by_memoization(env):
    # Run repeatedly: Lua hash order cannot change whether a deep graph passes.
    lua, module = env
    doc = parse(env, 'return {schema=1,kind="sets",job="SMN",definitions={a={path={"a"},bases={"b"}},b={path={"b"},bases={"c"}},c={path={"c"}}}}', {b'references': 2})
    for _ in range(3):
        with pytest.raises(lupa.LuaError, match='references limit'):
            module[b'resolve'](doc, lua.table(), lua.table())


def test_reference_copy_amplification_is_bounded_before_large_allocation(env):
    lua, module = env
    items = catalog(env, 'cape={label="Cape",name="Cape",augments={' + ','.join('"A"' for _ in range(32)) + '}}')
    definitions = ','.join(f's{i}={{path={{"s{i}"}},slots={{back={{ref="cape"}}}}}}' for i in range(32))
    source = 'return {schema=1,kind="sets",job="SMN",definitions={' + definitions + '}}'
    doc = parse(env, source, {b'materialized_values': 200})
    with pytest.raises(lupa.LuaError, match=r'fixture.lua:.*SMN set s\d+ slot back: exceeded materialized_values limit 200'):
        module[b'resolve'](doc, items, lua.table())
    assert items[b'cape'][b'item'][b'augments'][1] == b'A'
