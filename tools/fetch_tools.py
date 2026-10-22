"""Download ffmpeg (LGPL build) and pandoc into ./bin so they ship inside the app.

Run before packaging:  python tools/fetch_tools.py
Safe to re-run; existing files are kept.
"""
import io
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
LICENSES = BIN / "licenses"

# LGPL build of ffmpeg (no GPL-only encoders such as x264/x265), which is the safe one to redistribute.
FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-lgpl.zip"
PANDOC_API = "https://api.github.com/repos/jgm/pandoc/releases/latest"


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "RadialConvert-build"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def extract(zf: zipfile.ZipFile, suffix: str, dest: Path) -> bool:
    for name in zf.namelist():
        if name.lower().endswith(suffix.lower()):
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            return True
    return False


def get_ffmpeg():
    if (BIN / "ffmpeg.exe").exists():
        return
    print("Downloading ffmpeg ...")
    with zipfile.ZipFile(io.BytesIO(download(FFMPEG_URL))) as zf:
        if not extract(zf, "/bin/ffmpeg.exe", BIN / "ffmpeg.exe"):
            sys.exit("ffmpeg.exe not found in archive")
        extract(zf, "/LICENSE.txt", LICENSES / "ffmpeg-LICENSE.txt")


def get_pandoc():
    if (BIN / "pandoc.exe").exists():
        return
    print("Downloading pandoc ...")
    release = json.loads(download(PANDOC_API))
    asset = next(a for a in release["assets"] if a["name"].endswith("windows-x86_64.zip"))
    with zipfile.ZipFile(io.BytesIO(download(asset["browser_download_url"]))) as zf:
        if not extract(zf, "/pandoc.exe", BIN / "pandoc.exe"):
            sys.exit("pandoc.exe not found in archive")
        extract(zf, "/COPYING.rtf", LICENSES / "pandoc-COPYING.rtf")


if __name__ == "__main__":
    BIN.mkdir(exist_ok=True)
    get_ffmpeg()
    get_pandoc()
    print("Tools ready in", BIN)
