# -*- mode: python ; coding: utf-8 -*-
"""
TMG Suite - PyInstaller Specification File
==========================================

This file configures how PyInstaller builds the executable.

To build the .exe:
    pyinstaller tmg_suite.spec

Output will be in:
    dist/TMG_Suite.exe
"""

block_cipher = None

a = Analysis(
    ['tmg_gui_v3.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'dbf',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'queue',
        'threading',
        'json',
        'os',
        'sys',
        'datetime',
        'shutil',
        'subprocess',
        'platform',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TMG_Suite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window - GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon='icon.ico' if you have one
    version_file=None,
)
