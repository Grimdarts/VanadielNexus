"""T4 adapter against local real SMN/Mote sources; always read-only."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

from tests.core.test_managed_gearswap import quiet_faulthandler  # noqa: F401

pytest.importorskip('lupa.luajit21', reason='SMN integration requires LuaJIT')
WINDOWER = Path(r'C:\Users\Jason\Games\Windower4')
pytestmark = pytest.mark.skipif(not (WINDOWER / 'addons/GearSwap').is_dir(), reason="Jason's local SMN sources unavailable")
ROOT = Path(__file__).parents[1]


def probe(**kwargs):
    spec = importlib.util.spec_from_file_location('smn_integration_probe', ROOT / 'staging/gearswap/check_smn_integration.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run(WINDOWER, 'Someonesmall', **kwargs)


@pytest.mark.parametrize('subjob', ['', 'SCH', 'RDM', 'WHM'])
def test_smn_mote_parity_and_lifecycle(subjob):
    result = probe(subjob=subjob)
    assert result['state'] == 'ready'
    assert all(result['checks'].values())
    assert result['pact_cases'] == 32
    assert not result['cleanup_errors']


@pytest.mark.parametrize('fault', ['prepare', 'entry', 'globals', 'setup', 'setup_event', 'controls', 'publish', 'event'])
def test_partial_framework_failure_cleanup_and_retry(fault):
    result = probe(fault=fault)
    assert result['state'] == 'failed'
    assert all(result['checks'].values())
    assert not result['cleanup_errors']


def test_probe_changes_no_installed_lua():
    data = WINDOWER / 'addons/GearSwap/data'
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in data.rglob('*.lua')}
    probe()
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in data.rglob('*.lua')}
    assert after == before
