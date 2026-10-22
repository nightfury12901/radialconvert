# PyInstaller spec: builds dist/RadialConvert/RadialConvert.exe (folder build; starts fast, fewer antivirus false alarms)
#   pyinstaller RadialConvert.spec --noconfirm
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], ["openpyxl", "xlrd", "odf"]

for pkg in ("pymupdf", "fitz"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# bundled converters (made by tools/fetch_tools.py) and the icon
if Path("bin").exists():
    datas.append(("bin", "bin"))
if Path("assets/icon.ico").exists():
    datas.append(("assets/icon.ico", "assets"))

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "scipy"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RadialConvert",
    console=False,
    icon="assets/icon.ico" if Path("assets/icon.ico").exists() else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="RadialConvert")
