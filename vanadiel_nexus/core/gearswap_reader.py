"""Read every set in a character's GearSwap job file. Qt-free.

read_job finds the file GearSwap would load, runs it in a sandboxed child process (gs_worker + gs_sandbox.lua)
and turns the result into SetReads: canonical paths, aliases, and where each piece came from. Results are
cached until any file the read touched changes. See docs/SET-MANAGER-ENG-REVIEW.md sections 4.1-4.4.
"""
import multiprocessing
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field

from . import gearswap_files, gs_worker, item_res

SLOT_ORDER = ('main', 'sub', 'range', 'ammo', 'head', 'neck', 'ear1', 'ear2',
              'body', 'hands', 'ring1', 'ring2', 'back', 'waist', 'legs', 'feet')
JOB_IDS = {short: i for i, short in enumerate(gearswap_files.JOB_LONG, start=1)}  # res/jobs.lua ids
RES_DEPENDENCIES = ('jobs.lua', 'items.lua', 'job_abilities.lua', 'weapon_skills.lua')
TIMEOUT = 10.0

NO_FILE = 'No GearSwap file'
TOOK_TOO_LONG = 'took too long to load (over {:g} s)'
STOPPED = 'the Lua runtime stopped unexpectedly (exit {})'
NO_ANSWER = 'the Lua runtime closed without an answer'


@dataclass
class Piece:
    slot: str                     # main sub range ammo head neck ear1 ear2 body hands ring1 ring2 back waist legs feet
    original_key: str             # as written, e.g. "left_ear"
    name: str = ''
    augments: list[str] = field(default_factory=list)
    bag: str = ''                 # designated bag, GearSwap enforces it
    priority: int | None = None
    empty: bool = False           # slot set to `empty` on purpose
    table_id: int = 0             # identity of the item table (0 = plain string)
    shared_count: int = 0         # how many slots across all sets use this table_id
    inherited_from: str = ''      # nearest set it came from via set_combine
    origin_path: str = ''         # set that defines it directly ('' = this set)


@dataclass
class SetRead:
    path: str
    keys: list
    pieces: dict[str, Piece]      # by canonical slot; absent = not set
    aliases: list[str] = field(default_factory=list)
    empty_in_file: bool = False   # table with no keys: "no pieces in the file (may be picked at runtime)"
    odd_path: bool = False        # a key in the path has a backslash, both quote types or control characters


@dataclass
class JobRead:
    character: str
    job: str
    sub_job: str
    path: str
    shared_file: bool
    files: dict[str, float]       # every Lua file loaded -> mtime
    absent_deps: list[str] = field(default_factory=list)  # candidates checked before each found file (must stay absent)
    searched: list[str] = field(default_factory=list)     # filled when no job file was found
    sets: list[SetRead] = field(default_factory=list)
    error: str = ''
    error_details: str = ''
    partial: bool = False         # get_sets raised: these are the sets it made before that (eng review D3)
    includes: list[str] = field(default_factory=list)     # files the job included, in load order
    read_at: float = 0.0          # time.time() when the Lua actually ran (a cache hit keeps it)


# ---------------------------------------------------------------- paths

_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_LUA_KEYWORDS = {'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'goto', 'if', 'in',
                 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', 'while'}
_CONTROL_RE = re.compile(r'[\x00-\x1f\x7f]')


def _escape(key: str) -> str:
    def control(match):
        char = match[0]
        return {'\n': '\\n', '\t': '\\t'}.get(char, '\\%03d' % ord(char))
    return _CONTROL_RE.sub(control, key.replace('\\', '\\\\'))


def render_key(key) -> str:
    if isinstance(key, bool):
        return f'[{str(key).lower()}]'
    if isinstance(key, (int, float)):
        return f'[{key:g}]' if isinstance(key, float) else f'[{key}]'
    if _IDENT_RE.match(key) and key not in _LUA_KEYWORDS:
        return '.' + key
    escaped = _escape(key)
    if "'" not in key:
        return f"['{escaped}']"
    if '"' not in key:
        return f'["{escaped}"]'
    return "['" + escaped.replace("'", "\\'") + "']"


def render_path(keys) -> str:
    return 'sets' + ''.join(render_key(k) for k in keys)


def odd_key(key) -> bool:
    """A key Equip now can't safely type: backslash, both quote types, or any control character (D12)."""
    return isinstance(key, str) and ('\\' in key or ("'" in key and '"' in key) or bool(_CONTROL_RE.search(key)))


# ---------------------------------------------------------------- source text

_LONG_BRACKET_RE = re.compile(r'\[(=*)\[')


def strip_comments(text: str) -> str:
    """Lua source with comments blanked out (strings kept), line breaks preserved so line numbers still match."""
    out = []
    i, n = 0, len(text)
    while i < n:
        char = text[i]
        if char in '"\'':
            j = i + 1
            while j < n and text[j] != char and text[j] != '\n':
                j += 2 if text[j] == '\\' else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith('--', i):
            match = _LONG_BRACKET_RE.match(text, i + 2)
            if match:
                close = ']' + match[1] + ']'
                end = text.find(close, match.end())
                end = n if end < 0 else end + len(close)
            else:
                end = text.find('\n', i)
                end = n if end < 0 else end
            out.append(re.sub(r'[^\n]', ' ', text[i:end]))
            i = end
        elif char == '[' and _LONG_BRACKET_RE.match(text, i):
            match = _LONG_BRACKET_RE.match(text, i)
            close = ']' + match[1] + ']'
            end = text.find(close, match.end())
            end = n if end < 0 else end + len(close)
            out.append(text[i:end])
            i = end
        else:
            out.append(char)
            i += 1
    return ''.join(out)


_QUOTED_KEY_RE = re.compile(r"""\[\s*(?:'([^']*)'|"([^"]*)")\s*\]""")


def normalise_path(text: str, *, case_sensitive: bool = False) -> str:
    """`sets.precast.WS['Savage Blade']` → `sets.precast.ws.savage blade` (spaces outside keys removed)."""
    def quoted(match):
        return '.' + (match[1] if match[1] is not None else match[2])
    text = _QUOTED_KEY_RE.sub(lambda m: '\0' + quoted(m).replace(' ', '\1') + '\0', text)
    text = re.sub(r'\s+', '', text).replace('\0', '').replace('\1', ' ')
    return text if case_sensitive else text.casefold()


_PATH_TEXT = r"""sets(?:\s*\.\s*[A-Za-z_]\w*|\s*\[\s*(?:'[^']*'|"[^"]*"|\d+)\s*\])*"""
_ALIAS_LINE_RE = re.compile(r'^\s*(' + _PATH_TEXT + r')\s*=\s*(' + _PATH_TEXT + r')\s*[,;]?\s*$', re.M)


def alias_lines(texts) -> set[str]:
    """Normalised left-hand paths of bare alias assignments (`sets.a = sets.b`) in comment-stripped source."""
    found = set()
    for text in texts:
        for match in _ALIAS_LINE_RE.finditer(strip_comments(text)):
            found.add(normalise_path(match[1]))
    return found


def _read_text(path: str) -> str:
    try:
        with open(path, encoding='utf-8', errors='replace') as source:
            return source.read()
    except OSError:
        return ''


# ---------------------------------------------------------------- sets from the sandbox's graph

def build_sets(raw: dict, alias_paths: set[str] = frozenset()) -> list[SetRead]:
    """Nodes and edges from gs_sandbox.lua → SetReads in walk order.

    Canonical path per table: never a bare alias line while another path exists (D24), then the most keys,
    then walk order. The table's children live under its canonical path; other paths become aliases.
    """
    nodes = {node['id']: node for node in raw.get('nodes') or []}
    order = [node['id'] for node in raw.get('nodes') or []]
    incoming = defaultdict(list)
    for index, edge in enumerate(raw.get('edges') or []):
        incoming[edge['child']].append((index, edge['parent'], edge['key']))

    canon = {0: ((), (), (0,))}  # node -> (keys, edge ranks, node chain)

    def score(candidate, alias_count):
        keys, ranks, _ = candidate
        alias = alias_count > 1 and normalise_path(render_path(keys)) in alias_paths
        return (alias, -len(keys), ranks)

    for _ in range(16):  # re-rooting a parent moves its children; settle in a few rounds
        changed = False
        for node_id in order:
            options = []
            for index, parent, key in incoming[node_id]:
                if parent not in canon or node_id in canon[parent][2]:
                    continue
                keys, ranks, chain = canon[parent]
                options.append((keys + (key,), ranks + (index,), chain + (node_id,)))
            if not options:
                continue
            best = min(options, key=lambda c: score(c, len(options)))
            if canon.get(node_id) != best:
                canon[node_id] = best
                changed = True
        if not changed:
            break

    paths = {node_id: render_path(canon[node_id][0]) for node_id in canon}
    odd = {node_id: any(odd_key(k) for k in canon[node_id][0]) for node_id in canon}

    table_uses = defaultdict(int)
    for node_id in order:
        for piece in nodes[node_id].get('pieces') or []:
            if piece.get('table_id'):
                table_uses[piece['table_id']] += 1

    def origin(node_id, slot):
        seen = set()
        current = node_id
        for _ in range(32):
            piece = next((p for p in nodes.get(current, {}).get('pieces') or [] if p['slot'] == slot), None)
            source = piece and piece.get('from')
            if not source or source in seen or source not in canon:
                break
            seen.add(current)
            current = source
        return '' if current == node_id else paths.get(current, '')

    result = []
    for node_id in sorted((n for n in order if n in canon), key=lambda n: canon[n][1]):
        node = nodes[node_id]
        if node['kind'] not in ('set', 'empty'):
            continue
        keys = list(canon[node_id][0])
        aliases = []
        for index, parent, key in incoming[node_id]:
            if parent in canon and node_id not in canon[parent][2]:
                path = render_path(canon[parent][0] + (key,))
                if path != paths[node_id] and path not in aliases:
                    aliases.append(path)
        pieces = {}
        for raw_piece in node.get('pieces') or []:
            source = raw_piece.get('from')
            pieces[raw_piece['slot']] = Piece(
                slot=raw_piece['slot'], original_key=str(raw_piece.get('original_key', raw_piece['slot'])),
                name=raw_piece.get('name', ''), augments=list(raw_piece.get('augments') or []),
                bag=raw_piece.get('bag', ''), priority=raw_piece.get('priority'),
                empty=bool(raw_piece.get('empty')), table_id=raw_piece.get('table_id', 0),
                shared_count=table_uses.get(raw_piece.get('table_id', 0), 0) if raw_piece.get('table_id') else 0,
                inherited_from=paths.get(source, '') if source else '',
                origin_path=origin(node_id, raw_piece['slot']) if source else '')
        result.append(SetRead(path=paths[node_id], keys=keys, pieces=pieces, aliases=aliases,
                              empty_in_file=node['kind'] == 'empty', odd_path=odd[node_id]))
    return result


# ---------------------------------------------------------------- the child process

def _spawn(args: dict, timeout: float) -> dict:
    """Run gs_worker.main in a spawned child. Order matters: poll → recv → join, or a big result deadlocks (D5)."""
    context = multiprocessing.get_context('spawn')
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=gs_worker.main, args=(sender, args), daemon=True)
    process.start()
    sender.close()
    result, timed_out = None, False
    try:
        if receiver.poll(timeout):
            try:
                result = receiver.recv()
            except (EOFError, OSError):
                result = None
        else:
            timed_out = True
            process.terminate()
    finally:
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join(2)
        receiver.close()
    if timed_out:  # terminate() gives exit -15; the message comes from the flag, not the code (D5)
        return {'error': TOOK_TOO_LONG.format(timeout)}
    if result is None:
        code = process.exitcode
        return {'error': STOPPED.format(code) if code else NO_ANSWER}
    return result


# ---------------------------------------------------------------- read_job and its cache

_CACHE = {}  # (normcase windower, character, job, sub_job) -> (JobRead, res mtimes)


def _mtime(path: str):
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return None


def _res_mtimes(windower_dir: str) -> dict:
    return {name: _mtime(os.path.join(windower_dir, 'res', name)) for name in RES_DEPENDENCIES}


def _cache_key(windower_dir, character, job, sub_job):
    return (os.path.normcase(os.path.abspath(windower_dir)), character, job, sub_job or '')


def _valid(entry, windower_dir, search) -> bool:
    read, res = entry
    if not search.path or os.path.normcase(search.path) != os.path.normcase(read.path):
        return False
    if any(_mtime(path) != mtime for path, mtime in read.files.items()):
        return False
    if any(os.path.exists(path) for path in read.absent_deps):
        return False
    return _res_mtimes(windower_dir) == res


def clear_cache(windower_dir: str = None) -> None:
    """Forget cached reads (for one Windower folder, or all)."""
    if windower_dir is None:
        _CACHE.clear()
        return
    folder = os.path.normcase(os.path.abspath(windower_dir))
    for key in [k for k in _CACHE if k[0] == folder]:
        del _CACHE[key]


def read_job(windower_dir: str, character: str, job: str, sub_job: str = '', force: bool = False,
             timeout: float = TIMEOUT, appdata: str = None, _test: dict = None) -> JobRead:
    """Every set in the file GearSwap would load for this character's job. Never raises for Lua problems:
    they come back in JobRead.error. force=True (⟳ Reload files) skips the cache and re-reads res."""
    job = (job or '').upper()
    sub_job = (sub_job or '').upper()
    search = gearswap_files.find_job_file(windower_dir, character, job, appdata)
    if not search.path:
        return JobRead(character, job, sub_job, '', False, {}, searched=search.searched, error=NO_FILE)
    key = _cache_key(windower_dir, character, job, sub_job)
    if force:
        _CACHE.pop(key, None)
        item_res.clear(windower_dir)
    elif key in _CACHE and _valid(_CACHE[key], windower_dir, search):
        return _CACHE[key][0]

    res = _res_mtimes(windower_dir)
    args = {'windower_dir': windower_dir, 'character': character, 'job': job,
            'job_long': gearswap_files.JOB_LONG.get(job, job), 'job_id': JOB_IDS.get(job, 0),
            'sub_job': sub_job, 'sub_job_long': gearswap_files.JOB_LONG.get(sub_job, sub_job),
            'sub_job_id': JOB_IDS.get(sub_job, 0), 'job_path': search.path, 'appdata': appdata}
    args.update(_test or {})
    raw = _spawn(args, timeout)

    files = {}
    for path in [search.path] + list(raw.get('files') or []):
        files.setdefault(os.path.normpath(path), _mtime(path))
    includes = list(raw.get('includes') or [])
    error = raw.get('error') or ''
    details = raw.get('error_details') or ''
    if error and raw.get('load_errors'):
        details += '\n\nWindower libraries that failed to load:\n' + '\n'.join(raw['load_errors'])
    sets = []
    if raw.get('nodes'):
        texts = [_read_text(path) for path in [search.path] + includes]
        sets = build_sets(raw, alias_lines(texts))
    read = JobRead(character, job, sub_job, search.path, search.shared, files,
                   absent_deps=list(raw.get('absent_deps') or []), sets=sets, error=error, error_details=details,
                   partial=bool(raw.get('partial')) and bool(error), includes=includes, read_at=time.time())
    transient = error.startswith(('took too long', 'the Lua runtime')) or error == gs_worker.LUPA_MISSING
    if not transient and not _test:  # process problems are worth retrying; Lua errors stay until a file changes
        _CACHE[key] = (read, res)
    return read
