"""Audit a frozen Windows bundle and launch its isolated startup check before installation."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def is_windows_system_dll(name):
    """Use the Windows 10/11 ICU/UCRT ABI; retain Qt's MSVC redistributables."""
    base = name.replace('\\', '/').rsplit('/', 1)[-1].casefold()
    return (base.startswith(('api-ms-win-', 'ext-ms-win-'))
            or base in {'ucrtbase.dll', 'icuuc.dll', 'icuin.dll'}
            or bool(re.fullmatch(r'icudt\d+\.dll', base)))


def filter_windows_binaries(binaries):
    return [entry for entry in binaries if not is_windows_system_dll(entry[0])]


def audit_archive(executable):
    from PyInstaller.archive.readers import CArchiveReader
    archive = CArchiveReader(str(executable))
    invalid = [name for name in archive.toc if is_windows_system_dll(name)]
    if invalid:
        raise ValueError('Conflicting Windows system DLLs bundled: '+', '.join(invalid))


def check(executable, timeout=30):
    executable = Path(executable).resolve()
    audit_archive(executable)
    with tempfile.TemporaryDirectory(prefix='vn-startup-') as temporary:
        root = Path(temporary)
        result = root/'result.json'
        env = dict(os.environ, VN_DATA_DIR=str(root/'data'),
                   QT_QPA_PLATFORM='windows' if os.name=='nt' else 'offscreen')
        process = subprocess.Popen([str(executable), '--startup-check', str(result)], env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
            else:
                process.kill()
            process.wait(timeout=5)
            raise RuntimeError('Frozen startup check timed out')
        if code or not result.exists():
            raise RuntimeError(f'Frozen startup failed: exit {code}, result exists={result.exists()}')
        payload = json.loads(result.read_text(encoding='utf-8'))
        if not payload.get('ok') or not {'gear','sets','guides','g13'}.issubset(payload.get('pages',[])):
            raise RuntimeError('Incomplete frozen startup: '+str(payload))
        if not (payload.get('spawn') or {}).get('ok'):  # the Sets page's Lua child process (multiprocessing spawn)
            raise RuntimeError('Frozen spawn check failed: '+str(payload.get('spawn')))
        return payload


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args=parser.parse_args()
    print(json.dumps(check(args.executable),indent=2))
