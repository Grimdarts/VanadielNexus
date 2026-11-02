"""Read-only local SMN integration probe in the existing Nexus sandbox.

No active files or Python application routes are modified. Source modules are
inserted into a temporary sandbox copy as trusted code. All commands, events,
timers and HUD resources are recorded/stubbed. Equipment stays in memory; only
assertion results leave the worker. This is not a personal-profile conversion.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from vanadiel_nexus.core import gearswap_files, gs_worker  # noqa: E402

MODULES = {
    'data': 'core/managed_data.lua', 'lifecycle': 'core/lifecycle.lua',
    'ownership': 'core/ownership.lua', 'spec': 'jobs/SMN.lua',
    'pacts': 'jobs/smn_pacts.lua', 'adapter': 'integrations/mote_smn.lua',
    'host': 'integrations/prepare_host.lua', 'bootstrap': 'integrations/bootstrap.lua',
    'eligibility': 'core/eligibility.lua',
}


def run(windower_dir, character, subjob='SCH', fault='', probe=None):
    base = Path(__file__).parent / 'PlayerSystem'
    modules = 'local managed_modules={}\n' + '\n'.join(
        f'managed_modules.{name}=(function()\n{(base / rel).read_text(encoding="utf-8")}\nend)()'
        for name, rel in MODULES.items())
    instrument = (ROOT / 'tests/fixtures/managed_smn_probe.lua').read_text(encoding='utf-8')
    sandbox = (ROOT / 'vanadiel_nexus/resources/gs_sandbox.lua').read_text(encoding='utf-8')
    anchor = 'result.edges = edges\nreturn result'
    assert sandbox.count(anchor) == 1
    code = (f'local probe_fault={json.dumps(fault)}\n' + modules + '\n' + instrument)
    if probe:
        code += '\n' + probe
    staged = sandbox.replace(anchor, 'result.edges = edges\nsethook(guard,"",STEP)\n' + code + '\nsethook()\nreturn result')
    with tempfile.TemporaryDirectory(prefix='vn-smn-t4-') as directory:
        path = Path(directory) / 'probe.lua'
        path.write_text(staged, encoding='utf-8')
        original = gs_worker.resource_path
        gs_worker.resource_path = lambda name: str(path) if name == 'gs_sandbox.lua' else original(name)
        try:
            selected = gearswap_files.find_job_file(str(windower_dir), character, 'SMN')
            assert selected.path, 'SMN entry missing'
            result = gs_worker.run(dict(windower_dir=str(windower_dir), character=character, job='SMN',
                job_long='Summoner', job_id=15, sub_job=subjob,
                sub_job_long={'SCH': 'Scholar', 'WHM': 'White Mage', 'RDM': 'Red Mage'}.get(subjob, ''),
                sub_job_id={'SCH': 20, 'WHM': 3, 'RDM': 5}.get(subjob, 0), job_path=selected.path))
        finally:
            gs_worker.resource_path = original
    if result.get('error'):
        raise RuntimeError(result.get('error_details') or result['error'])
    return result['smn_integration']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windower', required=True)
    parser.add_argument('--character', required=True)
    parser.add_argument('--subjob', default='SCH')
    parser.add_argument('--fault', default='')
    args = parser.parse_args()
    print(json.dumps(run(args.windower, args.character, args.subjob, args.fault), indent=2))
