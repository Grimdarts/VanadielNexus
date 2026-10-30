# -*- mode: python ; coding: utf-8 -*-
# Build with:  .\build.ps1   (or: py -m PyInstaller --noconfirm VanadielNexus.spec)

a = Analysis(
    ['vanadiel_nexus/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[('vanadiel_nexus/resources', 'vanadiel_nexus/resources')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Not used by the app; keeps the exe smaller and startup faster
    excludes=['tkinter', 'unittest', 'pydoc', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf',
              'PySide6.QtOpenGL', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtConcurrent', 'PySide6.QtDBus'],
    noarchive=False,
    optimize=0,
)
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
