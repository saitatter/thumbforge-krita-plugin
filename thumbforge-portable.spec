# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT), str(ROOT / 'src')],
    datas=[
        ('pyproject.toml', '.'),
    ],
    hiddenimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='thumbforge-portable',
    debug=False,
    strip=False,
    upx=True,
    console=False,
)
