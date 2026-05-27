# ksei_dashboard.spec
# Build with:  py -m PyInstaller ksei_dashboard.spec
# Output  :  dist/KSEI_Dashboard/KSEI_Dashboard.exe

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

# ── Collect everything from the major packages ────────────────────────────────
st_datas,  st_bins,  st_hidden  = collect_all("streamlit")
alt_datas, alt_bins, alt_hidden = collect_all("altair")
pm_datas,  pm_bins,  pm_hidden  = collect_all("pdfminer")
pp_datas,  pp_bins,  pp_hidden  = collect_all("pdfplumber")
pd_datas,  pd_bins,  pd_hidden  = collect_all("pandas")
nx_datas,  nx_bins,  nx_hidden  = collect_all("networkx")

# ── Our own app files (placed in the root of _internal/) ─────────────────────
app_datas = [
    ("app.py",      "."),
    ("parser.py",   "."),
    ("db.py",       "."),
    ("analysis.py", "."),
]

all_datas    = (st_datas + alt_datas + pm_datas + pp_datas +
                pd_datas + nx_datas + app_datas)
all_binaries = st_bins + alt_bins + pm_bins + pp_bins + pd_bins + nx_bins
all_hidden   = (st_hidden + alt_hidden + pm_hidden + pp_hidden +
                pd_hidden + nx_hidden + [
    # Explicit extras that collect_all sometimes misses
    "streamlit.web.cli",
    "streamlit.web.bootstrap",
    "streamlit.components.v1",
    "streamlit.elements",
    "streamlit.runtime",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.state",
    "streamlit.server",
    "pdfplumber",
    "pdfminer.high_level",
    "pdfminer.layout",
    "pdfminer.converter",
    "pypdfium2",
    "sqlite3",
    "_sqlite3",
    "json",
    "io",
    "re",
    "threading",
    "webbrowser",
    "socket",
    "importlib.metadata",
    "pkg_resources",
    "pkg_resources.extern",
    "packaging",
    "packaging.version",
    "packaging.requirements",
    "packaging.specifiers",
    "click",
    "click.core",
    "toml",
    "tomli",
    "pyarrow",
    "tzdata",
    "pytz",
    "dateutil",
    "dateutil.parser",
])

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused heavy packages to reduce size
        "matplotlib",
        "scipy",
        "sklearn",
        "PIL",
        "Pillow",
        "tkinter",
        "_tkinter",
        "wx",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "black",
        "mypy",
        "sphinx",
        "docutils",
        # numba / llvmlite are ~120 MB and not used by our app
        "numba",
        "llvmlite",
        # sympy is large and unused
        "sympy",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KSEI_Dashboard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX can cause false-positive antivirus hits
    console=True,       # Keep console so errors are visible; set False for production
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="KSEI_Dashboard",
)
