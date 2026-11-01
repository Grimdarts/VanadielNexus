"""Local only: read Jason's real GearSwap jobs from his Windower folder (read-only).

Skips unless C:\\Users\\Jason\\Games\\Windower4 exists. Nothing from that folder is copied into the repo.
"""
import hashlib
import os
import re
import time
from pathlib import Path

import pytest

WINDOWER = Path(r'C:\Users\Jason\Games\Windower4')
CHARACTER = 'Someonesmall'
JOBS = ('BLU', 'RUN', 'SMN', 'SCH', 'NIN', 'COR', 'BST', 'RDM')

pytestmark = pytest.mark.skipif(not (WINDOWER / 'addons' / 'GearSwap').is_dir(),
                                reason="Jason's Windower folder is not on this PC")
pytest.importorskip('lupa.luajit21', reason='GearSwap sandbox requires lupa')

from vanadiel_nexus.core import gearswap_reader as reader, gs_worker  # noqa: E402


@pytest.fixture(scope='module')
def reads():
    reader.clear_cache()
    return {job: reader.read_job(str(WINDOWER), CHARACTER, job) for job in JOBS}


def _hash_tree(root: Path) -> dict:
    # Nova-controls-live.json is rewritten every second by the game while a job is loaded, so it is left out.
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*'))
            if p.is_file() and p.name != 'Nova-controls-live.json'}


def test_all_eight_jobs_load_with_no_error(reads):
    for job, read in reads.items():
        assert not read.error, f'{job}: {read.error}\n{read.error_details}'
        assert not read.partial
        assert read.sets, job


# Assignments in Jason's files that correctly produce no listed set.
NOT_SETS = {
    'sets.precast.fc.resistant': "SMN: inside `if use_resistant then`, which is off",
    'sets.midcast.summoning magic': 'SMN: assigned sets.midcast.BloodPactWard, which is nil (the set is under .Pet)',
    'sets.idle.avatar.perp': 'SMN: sets.engaged.Perp = sets.perp makes sets.idle.Avatar contain itself (a cycle)',
}


def test_set_counts_and_every_assigned_set_is_listed(reads):
    counts = {job: len(read.sets) for job, read in reads.items()}
    assert counts['BLU'] >= 70 and counts['RUN'] >= 70 and counts['SMN'] >= 100 and counts['SCH'] >= 50, counts
    for job in ('BLU', 'RUN', 'SMN', 'SCH'):
        read = reads[job]
        listed = {reader.normalise_path(p) for s in read.sets for p in [s.path] + s.aliases}
        texts = [reader._read_text(p) for p in [read.path] + read.includes]
        assigned = set()
        for text in texts:
            for match in re.finditer(r'^\s*(sets(?:\.[A-Za-z_]\w*|\[\s*(?:\'[^\']*\'|"[^"]*")\s*\])+)\s*=[^=]',
                                     reader.strip_comments(text), re.M):
                assigned.add(reader.normalise_path(match[1]))
        # Children of an aliased table are listed once, under its canonical path.
        alias_of = {reader.normalise_path(a): reader.normalise_path(s.path) for s in read.sets for a in s.aliases}

        def canonical(path):
            for alias, target in sorted(alias_of.items(), key=lambda kv: -len(kv[0])):
                if path.startswith(alias + '.'):
                    return canonical(target + path[len(alias):])
            return path
        assigned = {canonical(p) for p in assigned}
        containers = {p for p in assigned if any(other.startswith(p + '.') for other in listed)}
        missing = sorted(p for p in assigned - listed - containers - set(NOT_SETS) if not p.endswith('.index'))
        assert not missing, f'{job}: assigned but not listed: {missing[:10]}'


def test_shared_mote_and_nova_files_are_included(reads):
    for job in ('NIN', 'COR', 'BST', 'RDM'):
        names = [os.path.basename(p) for p in reads[job].includes]
        assert 'nova-common.lua' in names and 'mote-include.lua' in names, (job, names)
        assert any(s.empty_in_file for s in reads[job].sets)
    assert 'mote-include.lua' in [os.path.basename(p) for p in reads['SCH'].includes]


def test_index_lists_are_not_sets_and_smn_aliases_point_to_the_canonical_set(reads):
    blu = {s.path for s in reads['BLU'].sets}
    assert 'sets.SavageBlade.Attack' in blu and not any(p.endswith('.index') for p in blu)
    smn = {s.path: s for s in reads['SMN'].sets}
    canonical = smn['sets.midcast.Pet.MagicalBloodPactRage']
    assert {'sets.magicalpact', 'sets.midcast.Pet.IfritMagicalBloodPactRage'} <= set(canonical.aliases)
    assert 'sets.magicalpact' not in smn and 'sets.midcast.Pet.IfritMagicalBloodPactRage' not in smn
    run = {s.path for s in reads['RUN'].sets}
    assert 'sets.Idle.Standard' in run


def test_reading_changes_no_file_under_windower():
    before = {**_hash_tree(WINDOWER / 'addons' / 'GearSwap' / 'data'), **_hash_tree(WINDOWER / 'addons' / 'libs')}
    reader.clear_cache()
    for job in JOBS:
        reader.read_job(str(WINDOWER), CHARACTER, job)
    after = {**_hash_tree(WINDOWER / 'addons' / 'GearSwap' / 'data'), **_hash_tree(WINDOWER / 'addons' / 'libs')}
    assert before == after


def test_blu_cold_read_within_5s_and_warm_within_0_2s():
    started = time.monotonic()
    read = reader.read_job(str(WINDOWER), CHARACTER, 'BLU', force=True)
    cold = time.monotonic() - started
    started = time.monotonic()
    again = reader.read_job(str(WINDOWER), CHARACTER, 'BLU')
    warm = time.monotonic() - started
    assert not read.error and again is read
    assert cold <= 5.0 and warm <= 0.2, (cold, warm)


def test_user_env_keys_match_the_installed_refresh_lua():
    text = (WINDOWER / 'addons' / 'GearSwap' / 'refresh.lua').read_text(encoding='utf-8', errors='replace')
    block = text[text.index('user_env = {'):]
    block = block[:block.index("user_env['_G'] = user_env")]
    block = re.sub(r'--[^\n]*', '', block)
    block = re.sub(r'sets=\{naked = \{.*', '', block, flags=re.S)  # the naked set's slot keys are not env keys
    keys = re.findall(r'([A-Za-z_]\w*)\s*=', block.replace('user_env = {', ''))
    keys.append('sets')
    assert list(dict.fromkeys(keys)) == list(gs_worker.GEARSWAP_USER_ENV_KEYS)


def test_sets_page_construction_is_fast(qtbot, tmp_path, monkeypatch):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    monkeypatch.setenv('VN_DATA_DIR', str(tmp_path))
    from vanadiel_nexus import __version__
    from vanadiel_nexus.ui.context import AppContext
    from vanadiel_nexus.ui.pages.sets import SetsPage
    ctx = AppContext(__version__)
    ctx.windower_dir = str(WINDOWER)
    started = time.perf_counter()
    page = SetsPage(ctx)
    elapsed = time.perf_counter() - started
    qtbot.addWidget(page)
    assert elapsed <= 0.05, elapsed
