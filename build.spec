# build.spec

import sys
import os
from pathlib import Path
import qfluentwidgets

# --- Paths ---
qfluent_path = Path(qfluentwidgets.__file__).parent
fluent_resources_path = qfluent_path / '_rc'

# Set the recursion limit higher for complex packages
sys.setrecursionlimit(5000)

# --- Analysis Phase ---
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (str(fluent_resources_path), 'qfluentwidgets/_rc'),
        (os.path.expanduser("~/.insightface"), ".insightface"),
        ('assets', 'assets') # Include our own assets folder
    ],
    hiddenimports=[
        'sklearn.utils._typedefs',
        'sklearn.utils._heap',
        'sklearn.utils._sorting',
        'sklearn.utils._vector_sentinel',
        'sklearn.neighbors._quad_tree',
        'torch',
        'torchvision',
        'open_clip',
        'onnxruntime',
        'insightface',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# --- Packaging Phase ---
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PhotoManager',
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
    icon='assets/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PhotoManager'
)