"""gearswap_reader: the spawn contract (three real child processes) and the cache (in-process runs)."""
import os
import shutil
import time
from pathlib import Path

import pytest

if os.environ.get('VN_LUA_RUNTIME'):
    import sys
    sys.path.insert(0, os.environ['VN_LUA_RUNTIME'])

pytest.importorskip('lupa.luajit21', reason='GearSwap sandbox requires lupa (VN_LUA_RUNTIME supported)')

from vanadiel_nexus.core import gearswap_reader as reader, gs_worker, item_res  # noqa: E402

FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'gearswap'
BODY = 'function get_sets() sets.Idle = {head="Hashishin Kavuk +2"} end'


@pytest.fixture(autouse=True)
def quiet_faulthandler():
    """LuaJIT raises Lua errors as Windows SEH exceptions; pytest's faulthandler would print each one."""
    import faulthandler
    enabled = faulthandler.is_enabled()
    faulthandler.disable()
    yield
    if enabled:
        faulthandler.enable()


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / 'Windower'
    shutil.copytree(FIXTURE, root)
    reader.clear_cache()
    yield root
    reader.clear_cache()


@pytest.fixture
def in_process(monkeypatch):
    """Run the worker in this process instead of spawning, and count the runs."""
    runs = []

    def spawn(args, timeout):
        runs.append(args)
        return gs_worker.run(args)
    monkeypatch.setattr(reader, '_spawn', spawn)
    return runs


def write(path: Path, text=BODY):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def bump(path: Path):
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))


def data(tree):
    return tree / 'addons' / 'GearSwap' / 'data'


def read(tree, **kw):
    return reader.read_job(str(tree), 'Alice', 'BLU', appdata=str(tree.parent / 'appdata'), **kw)


# ---------------------------------------------------------------- real spawn (3 tests)

def test_large_result_comes_through_the_pipe(tree):
    lines = ['function get_sets()']
    for i in range(1500):
        lines.append(f'sets.Set{i:04d} = {{head={{name="Hashishin Kavuk +2", augments={{"{"A" * 200}", "B{i}"}}}}, '
                     f'body="Nyame Mail", neck="Fotia Gorget", waist="Fotia Belt"}}')
    lines.append('end')
    write(data(tree) / 'Alice_BLU.lua', '\n'.join(lines))
    started = time.monotonic()
    result = read(tree)
    assert not result.error, result.error_details
    assert len(result.sets) == 1501  # plus sets.naked
    assert {s.path: s for s in result.sets}['sets.Set0000'].pieces['head'].augments[1] == 'B0'
    assert time.monotonic() - started < 30


def test_hung_child_times_out_with_a_message_not_an_exit_code(tree):
    write(data(tree) / 'Alice_BLU.lua')
    started = time.monotonic()
    result = read(tree, timeout=1.5, _test={'_test_hang': True})
    assert result.error == 'took too long to load (over 1.5 s)'
    assert time.monotonic() - started < 10


def test_crashed_child_reports_its_exit_code(tree):
    write(data(tree) / 'Alice_BLU.lua')
    result = read(tree, _test={'_test_crash': True})
    assert result.error == 'the Lua runtime stopped unexpectedly (exit 3)'


# ---------------------------------------------------------------- results and cache (in-process)

def test_no_job_file_lists_where_gearswap_looked(tree, in_process):
    result = read(tree)
    assert result.error == reader.NO_FILE and result.path == ''
    assert str(data(tree) / 'Alice_BLU.lua') in result.searched
    assert in_process == []


def test_read_fills_job_read(tree, in_process):
    write(data(tree) / 'Alice-gear.lua', 'helm = {name="Herculean Helm"}')
    job = write(data(tree) / 'Alice_BLU.lua', "include('Alice-gear.lua')\n" + BODY)
    result = read(tree, sub_job='war')
    assert (result.character, result.job, result.sub_job, result.path) == ('Alice', 'BLU', 'WAR', str(job))
    assert not result.shared_file and not result.error and not result.partial
    assert [s.path for s in result.sets] == ['sets.Idle', 'sets.naked']
    assert os.path.normpath(str(job)) in result.files
    assert [os.path.basename(p) for p in result.includes] == ['alice-gear.lua']
    assert in_process[0]['job_id'] == 16 and in_process[0]['sub_job_id'] == 1


def test_partial_read_keeps_sets(tree, in_process):
    write(data(tree) / 'Alice_BLU.lua', 'function get_sets() sets.A = {head="x"} error("boom") end')
    result = read(tree)
    assert result.partial and 'boom' in result.error
    assert 'sets.A' in [s.path for s in result.sets]


def test_cache_hit_and_invalidation_by_mtime(tree, in_process):
    job = write(data(tree) / 'Alice_BLU.lua')
    first = read(tree)
    assert read(tree) is first and len(in_process) == 1
    write(job, BODY.replace('+2', '+3'))
    bump(job)
    second = read(tree)
    assert len(in_process) == 2 and second.sets[0].pieces['head'].name == 'Hashishin Kavuk +3'


def test_cache_invalidated_by_an_included_file_change(tree, in_process):
    gear = write(data(tree) / 'Alice-gear.lua', 'helm = "Hashishin Kavuk +2"')
    write(data(tree) / 'Alice_BLU.lua', "include('Alice-gear.lua')\nfunction get_sets() sets.A = {head=helm} end")
    read(tree)
    write(gear, 'helm = "Hashishin Kavuk +3"')
    bump(gear)
    assert read(tree).sets[0].pieces['head'].name == 'Hashishin Kavuk +3' and len(in_process) == 2


def test_new_higher_priority_job_file_is_picked_up(tree, in_process):
    write(data(tree) / 'Alice_BLU.lua')
    read(tree)
    better = write(data(tree) / 'Alice' / 'BLU.lua', BODY.replace('Idle', 'FromFolder'))
    result = read(tree)
    assert result.path == str(better) and result.shared_file
    assert result.sets[0].path == 'sets.FromFolder'


def test_new_higher_priority_include_is_picked_up(tree, in_process):
    write(data(tree) / 'alice-gear.lua', 'helm = "Hashishin Kavuk +2"')
    write(data(tree) / 'Alice_BLU.lua', "include('Alice-gear.lua')\nfunction get_sets() sets.A = {head=helm} end")
    read(tree)
    write(data(tree) / 'Alice' / 'alice-gear.lua', 'helm = "Hashishin Kavuk +3"')  # data/<Char>/ comes first
    assert read(tree).sets[0].pieces['head'].name == 'Hashishin Kavuk +3' and len(in_process) == 2


def test_res_change_invalidates(tree, in_process):
    write(data(tree) / 'Alice_BLU.lua')
    read(tree)
    bump(tree / 'res' / 'items.lua')
    read(tree)
    assert len(in_process) == 2


def test_force_rereads_and_clears_item_res(tree, in_process):
    write(data(tree) / 'Alice_BLU.lua')
    read(tree)
    item_res.items(str(tree))
    assert any(str(tree).lower() in key[1] for key in item_res._CACHE)
    read(tree, force=True)
    assert len(in_process) == 2
    assert not any(str(tree).lower() in key[1] for key in item_res._CACHE)


def test_clear_cache_for_a_windower_change(tree, in_process):
    write(data(tree) / 'Alice_BLU.lua')
    read(tree)
    reader.clear_cache(str(tree))
    read(tree)
    assert len(in_process) == 2


def test_process_problems_are_not_cached(tree, monkeypatch):
    write(data(tree) / 'Alice_BLU.lua')
    calls = []
    monkeypatch.setattr(reader, '_spawn', lambda args, timeout: calls.append(1) or {'error': reader.NO_ANSWER})
    read(tree)
    read(tree)
    assert len(calls) == 2
