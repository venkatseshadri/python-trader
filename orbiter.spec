# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['orbiter/main.py'],
    pathex=['.', './ShoonyaApi-py'],
    binaries=[],
    datas=[('version.txt', '.'), ('manifest.json', '.')],
    hiddenimports=['orbiter.utils.version', 'orbiter.utils.system', 'orbiter.utils.logger', 'orbiter.utils.lock', 'orbiter.utils.argument_parser', 'orbiter.core.app', 'talib', 'talib.stream', 'talib._ta_lib', 'api_helper', 'api_helper.ShoonyaApiPy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='orbiter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
