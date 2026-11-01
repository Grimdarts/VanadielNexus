import importlib.util
from pathlib import Path

module_path=Path(__file__).parents[2]/'tools/check_frozen.py'
spec=importlib.util.spec_from_file_location('vn_check_frozen',module_path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_reject_unrelated_icu_and_windows_forwarders_but_keep_qt_and_msvc():
    binaries=[('icuuc.dll','Poppler/icuuc.dll','BINARY'),
              ('icudt78.dll','Poppler/icudt78.dll','BINARY'),
              ('api-ms-win-crt-runtime-l1-1-0.dll','SDK/runtime.dll','BINARY'),
              ('ucrtbase.dll','libheif/ucrtbase.dll','BINARY'),
              ('PySide6/Qt6Core.dll','PySide6/Qt6Core.dll','BINARY'),
              ('PySide6/MSVCP140.dll','PySide6/MSVCP140.dll','BINARY')]
    assert module.filter_windows_binaries(binaries)==binaries[-2:]


def test_source_startup_probe_initializes_every_page(tmp_path):
    import os
    import subprocess
    import sys
    import json
    output=tmp_path/'result.json'
    env=dict(os.environ,VN_DATA_DIR=str(tmp_path/'data'),QT_QPA_PLATFORM='offscreen')
    result=subprocess.run([sys.executable,'-m','vanadiel_nexus','--startup-check',str(output)],
        cwd=Path(__file__).parents[2],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    payload=json.loads(output.read_text())
    assert payload['ok']
    assert {'gear','sets','wishlist','inventory','addons','hotkeys','guides','g13','settings'}<=set(payload['pages'])
    assert payload['spawn']['ok'],payload['spawn']
    assert payload['spawn']['seconds']<=5
