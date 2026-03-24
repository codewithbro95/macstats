# -*- mode: python ; coding: utf-8 -*-
# MacStats.spec — PyInstaller bundle spec
# Produces a self-contained MacStats.app (no Python required on the target machine)

import os

block_cipher = None

# Read version from the VERSION file at build time
with open('VERSION') as _f:
    APP_VERSION = _f.read().strip()

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/app-icon.icns', 'assets'),
        ('VERSION', '.'),   # bundled so main.py can read it at runtime
    ],
    hiddenimports=[
        'rumps',
        'psutil',
        'psutil._psmacosx',
        'AppKit',
        'Foundation',
        'objc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MacStats',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app-icon.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MacStats',
)

app = BUNDLE(
    coll,
    name='MacStats.app',
    icon='assets/app-icon.icns',
    bundle_identifier='com.macstats.app',
    info_plist={
        'CFBundleName': 'MacStats',
        'CFBundleDisplayName': 'MacStats',
        'CFBundleVersion': APP_VERSION,
        'CFBundleShortVersionString': APP_VERSION,
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,
        'NSAppleEventsUsageDescription': 'MacStats needs Accessibility access to display system stats.',
    },
)
