# build.spec

import sys
import os
from pathlib import Path
import qfluentwidgets

from PyInstaller.utils.hooks import collect_all, collect_data_files

# Increase recursion limit for ML stacks
sys.setrecursionlimit(10000)

# --- Paths ---
qfluent_path = Path(qfluentwidgets.__file__).parent
fluent_resources_path = qfluent_path / "_rc"

# --- Collect ML package resources ---
torch_datas, torch_binaries, torch_hidden = collect_all("torch")
torchvision_datas, torchvision_binaries, torchvision_hidden = collect_all("torchvision")
onnx_datas, onnx_binaries, onnx_hidden = collect_all("onnxruntime")
insight_datas, insight_binaries, insight_hidden = collect_all("insightface")
cv2_datas, cv2_binaries, cv2_hidden = collect_all("cv2")

# OpenCLIP tokenizer / vocab files
openclip_datas = collect_data_files("open_clip")

# --- Analysis ---
a = Analysis(
    ["main.py"],
    pathex=[],

    binaries=[
        *torch_binaries,
        *torchvision_binaries,
        *onnx_binaries,
        *insight_binaries,
        *cv2_binaries,
    ],

    datas=[
        (str(fluent_resources_path), "qfluentwidgets/_rc"),
        ("assets", "assets"),
        (os.path.expanduser("~/.insightface"), ".insightface"),

        *torch_datas,
        *torchvision_datas,
        *onnx_datas,
        *insight_datas,
        *cv2_datas,
        *openclip_datas,
    ],

    hiddenimports=[
        *torch_hidden,
        *torchvision_hidden,
        *onnx_hidden,
        *insight_hidden,
        *cv2_hidden,

        "torch.testing",
        "torch.testing._comparison",
        "torch.testing._internal",

        "sklearn.utils._typedefs",
        "sklearn.utils._heap",
        "sklearn.utils._sorting",
        "sklearn.utils._vector_sentinel",
        "sklearn.neighbors._quad_tree",
    ],

    excludes=[
        "tensorflow",
        "keras",
        "openvino",
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    noarchive=False,
)

# --- Python archive ---
pyz = PYZ(a.pure)

# --- Executable ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PhotoManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/icon.ico",
)

# --- Bundle ---
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PhotoManager",
)