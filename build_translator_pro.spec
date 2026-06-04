# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

customtkinter_datas = collect_data_files('customtkinter')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=customtkinter_datas,  # UI theme JSON is generated at runtime; no font files are bundled.
    hiddenimports=[
        'customtkinter',
        'docx',
        'pdfplumber',
        'PyPDF2',
        'reportlab',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy', 'seaborn',
        'IPython', 'jupyter', 'notebook', 'pytest', 'tkinter.test',
        'PIL.ImageQt', 'tkinter.test', 'idlelib', 'turtle',
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
    [],
    exclude_binaries=True,
    name='TranslatorPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TranslatorPro',
)
