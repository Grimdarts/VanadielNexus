# -*- mode: python ; coding: utf-8 -*-
# Build with:  .\build.ps1   (or: py -m PyInstaller --noconfirm VanadielNexus.spec)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(SPECPATH) / 'tools'))
from check_frozen import filter_windows_binaries

a = Analysis(
    ['vanadiel_nexus/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[('vanadiel_nexus/resources', 'vanadiel_nexus/resources')],
    # The Sets page runs GearSwap Lua in a spawned child: lupa's LuaJIT runtime and the child's entry module
    hiddenimports=['lupa.luajit21', 'vanadiel_nexus.core.gs_worker'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Not used by the app; keeps the exe smaller and startup faster
    excludes=['tkinter', 'unittest', 'pydoc', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf',
              'PySide6.QtOpenGL', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtConcurrent', 'PySide6.QtDBus'],
    noarchive=False,
    optimize=0,
)
# Qt6Core imports Windows' unversioned ICU ABI. Never shadow it with Poppler's
# icuuc.dll or collect API-set/CRT forwarding DLLs from an unrelated PATH entry.
a.binaries = filter_windows_binaries(a.binaries)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VanadielNexus',
    icon='assets/VanadielNexus.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX-packed exes trip antivirus far more often
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
