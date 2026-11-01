"""Child-process entry for reading one GearSwap job file. The only place lupa runs. Qt-free.

gearswap_reader starts `main` in a spawned process. `run` does the work and is also called in-process by the
tests. Lua only ever gets plain tables plus three callbacks: read a source file inside the allowed roots,
resolve an include in GearSwap's order, and check whether a path inside the roots exists.
"""
import os
import re
import time

from . import gearswap_files
from .paths import resource_path

# Every key GearSwap puts in a job file's environment, from refresh.lua:114-147 (user_env), in that order.
# The sandbox builds the env from this list; tests check it (and, locally, that refresh.lua hasn't drifted).
GEARSWAP_USER_ENV_KEYS = (
    'gearswap', '_global', '_settings', '_addon',
    'equip', 'cancel_spell', 'change_target', 'cast_delay', 'print_set', 'set_combine', 'disable', 'enable',
    'send_command', 'windower', 'include', 'midaction', 'pet_midaction', 'set_language', 'show_swaps',
    'debug_mode', 'include_path', 'register_unhandled_command', 'move_spell_target', 'language',
    'string', 'math', 'table', 'set', 'list', 'queue', 'T', 'S', 'L', 'Q', 'pack', 'functions',
    'os', 'texts', 'bit', 'type', 'tostring', 'tonumber', 'pairs', 'ipairs', 'print', 'add_to_chat', 'unpack',
    'next', 'select', 'lua_base_path', 'empty', 'file', 'loadstring', 'assert', 'error', 'pcall', 'io', 'dofile',
    'debug', 'coroutine', 'setmetatable', 'getmetatable', 'rawset', 'rawget', 'require', '_libs',
    'buffactive', 'player', 'world', 'pet', 'fellow', 'alliance', 'party', 'sets',
)
INSTRUCTION_LIMIT = 200_000_000  # about 0.4 s of interpreted Lua (eng review section 1)
GEARSWAP_VERSION = '0.940'
LUPA_MISSING = 'Lua runtime missing (lupa)'


_TOKEN_RE = re.compile(r'''
    (?P<ws>\s+)
  | (?P<comment>--(?:\[(?P<ceq>=*)\[[\s\S]*?\](?P=ceq)\]|[^\n]*))
  | (?P<long>\[(?P<leq>=*)\[[\s\S]*?\](?P=leq)\])
  | (?P<str>"(?:[^"\\\n]|\\[\s\S])*"|'(?:[^'\\\n]|\\[\s\S])*')
  | (?P<num>0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)
  | (?P<name>[A-Za-z_]\w*)
  | (?P<op>\.\.\.|\.\.|==|~=|<=|>=|::|[\s\S])
''', re.X)
# Only sources that might use the extensions below go through the tokenizer (res/items.lua is 5 MB).
_MAYBE_EXTENDED_RE = re.compile(
    r'''["'\]}]\s*(?::\s*[A-Za-z_]|\.(?!\.)|\(|\[)|\b(?:end|true|false|nil|\d+)\s*:\s*[A-Za-z_]|\bend\s*[.(\[]''')
_OPENS = {'function', 'if', 'do', 'repeat'}
_CLOSES = {'end', 'until'}


def windower_syntax(source: str) -> str:
    """Rewrite Windower's Lua syntax extensions into standard Lua for stock LuaJIT.

    Windower's LuaJIT accepts a literal as the start of an expression: `'%s':format(x)`, `1:exp()`,
    `true:fn()` and `function() ... end()` (all in addons/libs). Stock LuaJIT needs parentheses:
    `('%s'):format(x)`. A string, table or function literal directly followed by `:`, `.`, `[` or `(` (and a
    number or boolean followed by `:`) is wrapped in parentheses, which is how Windower reads it. Comments and
    strings are never touched.
    """
    if not _MAYBE_EXTENDED_RE.search(source):
        return source
    tokens = [(m.lastgroup, m[0], m.start(), m.end()) for m in _TOKEN_RE.finditer(source)
              if m.lastgroup not in ('ws', 'comment')]
    inserts = []
    count = len(tokens)
    for i, (kind, value, start, _end) in enumerate(tokens):
        last = None
        if kind in ('str', 'long'):
            last = i
        elif (kind == 'num' or (kind == 'name' and value in ('true', 'false', 'nil'))) and                 i + 1 < count and tokens[i + 1][1] == ':':
            last = i  # 1:exp(), true:fn()
        elif kind == 'op' and value == '{':
            depth = 0
            for j in range(i, count):
                if tokens[j][0] == 'op' and tokens[j][1] in '{}':
                    depth += 1 if tokens[j][1] == '{' else -1
                    if depth == 0:
                        last = j
                        break
        elif kind == 'name' and value == 'function' and i + 1 < count and tokens[i + 1][1] == '(':
            depth = 0
            for j in range(i, count):
                if tokens[j][0] == 'name':
                    if tokens[j][1] in _OPENS:
                        depth += 1
                    elif tokens[j][1] in _CLOSES:
                        depth -= 1
                        if depth == 0:
                            last = j
                            break
        if last is not None and last + 1 < count:
            follow_kind, follow = tokens[last + 1][:2]
            if follow_kind == 'op' and follow in (':', '.', '[', '('):
                inserts.append((start, '('))
                inserts.append((tokens[last][3], ')'))
    if not inserts:
        return source
    out, pos = [], 0
    for offset, text in sorted(inserts, key=lambda item: (item[0], item[1] == '(')):
        out.append(source[pos:offset])
        out.append(text)
        pos = offset
    out.append(source[pos:])
    return ''.join(out)


def _deny_attributes(obj, name, is_setting):
    raise AttributeError('not available in the GearSwap sandbox')


def _slash(path: str) -> str:
    return path.replace('\\', '/')


def _to_python(value, depth=0):
    """Lua tables → dicts/lists (keys 1..n → list; an empty table → [])."""
    if depth > 64:
        return None
    from lupa import luajit21 as lupa
    if lupa.lua_type(value) == 'table':
        items = list(value.items())
        if not items:
            return []
        keys = [k for k, _ in items]
        if all(isinstance(k, int) for k in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
            return [_to_python(v, depth + 1) for _, v in sorted(items, key=lambda kv: kv[0])]
        return {k: _to_python(v, depth + 1) for k, v in items}
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _lua_table(lua, value):
    if isinstance(value, dict):
        return lua.table_from({k: _lua_table(lua, v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return lua.table_from([_lua_table(lua, v) for v in value])
    return value


def run(args: dict) -> dict:
    """Read one job file. args: windower_dir, character, job, job_long, job_id, sub_job, sub_job_long,
    sub_job_id, job_path, appdata (optional), instruction_limit (optional).

    Returns {nodes, edges, includes, files, absent_deps, error, error_details, partial, timed_out}.
    """
    try:
        from lupa import luajit21 as lupa
    except ImportError:
        return {'error': LUPA_MISSING, 'error_details': 'Install lupa: py -3 -m pip install lupa'}

    windower_dir = os.path.abspath(args['windower_dir'])
    character = args.get('character', '')
    appdata = args.get('appdata')
    roots = gearswap_files.allowed_roots(windower_dir, appdata)
    files = []
    absent = []

    def py_read_source(path):
        path = str(path)
        if not os.path.isabs(path):
            path = os.path.join(windower_dir, path)
        if not gearswap_files.inside_roots(path, roots) or not os.path.isfile(path):
            return None
        try:
            with open(path, 'rb') as source:
                text = windower_syntax(source.read().decode('utf-8', errors='replace'))
        except OSError:
            return None
        normal = os.path.normpath(path)
        if normal not in files:
            files.append(normal)
        return text

    def py_resolve(name, include_path=None):
        path, earlier = gearswap_files.find_first(windower_dir, character, [str(name)], include_path or '', appdata)
        absent.extend(p for p in earlier if p not in absent)
        return path and _slash(path)

    def py_exists(path, kind):
        path = str(path)
        if not gearswap_files.inside_roots(path, roots):
            return False
        return os.path.isdir(path) if kind == 'dir' else os.path.isfile(path)

    try:
        res_names = sorted(name[:-4] for name in os.listdir(os.path.join(windower_dir, 'res')) if name.endswith('.lua'))
    except OSError:
        res_names = []
    lua = lupa.LuaRuntime(register_eval=False, register_builtins=False, unpack_returned_tuples=True,
                          attribute_filter=_deny_attributes)
    cfg = _lua_table(lua, {
        'windower_dir': _slash(windower_dir).rstrip('/') + '/',
        'character': character, 'job': args.get('job', ''), 'job_long': args.get('job_long', ''),
        'job_id': args.get('job_id', 0), 'sub_job': args.get('sub_job') or None,
        'sub_job_long': args.get('sub_job_long') or None, 'sub_job_id': args.get('sub_job_id', 0),
        'job_path': _slash(os.path.abspath(args['job_path'])),
        'instruction_limit': int(args.get('instruction_limit') or INSTRUCTION_LIMIT),
        'gearswap_version': GEARSWAP_VERSION,
        'user_env_keys': list(GEARSWAP_USER_ENV_KEYS),
        'res_names': res_names,
    })
    with open(resource_path('gs_sandbox.lua'), encoding='utf-8') as source:
        sandbox = lua.execute('return function(...) ' + 'return assert(loadstring(...))' + ' end')(
            source.read(), '@gs_sandbox.lua')
    try:
        result = _to_python(sandbox(cfg, py_read_source, py_resolve, py_exists))
    except lupa.LuaError as error:  # the sandbox itself failed (a bug, or a lib it couldn't survive)
        text = str(error)
        result = {'error': text.splitlines()[0] if text else 'Lua error', 'error_details': text}
    if not isinstance(result, dict):
        result = {}
    result['files'] = files
    result['absent_deps'] = absent
    result.setdefault('nodes', [])
    result.setdefault('edges', [])
    result.setdefault('includes', [])
    result['includes'] = [os.path.normpath(p) for p in result['includes'] or []]
    return result


def main(conn, args: dict) -> None:
    """Child-process entry (spawn): run and send the result back over the pipe."""
    if args.get('_test_crash'):
        os._exit(3)
    if args.get('_test_hang'):
        time.sleep(60)
    try:
        result = run(args)
    except Exception as error:  # report, never hang the parent
        result = {'error': f'{type(error).__name__}: {error}', 'error_details': repr(error)}
    conn.send(result)
    conn.close()
