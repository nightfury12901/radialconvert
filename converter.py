"""Conversion engine.

Picks a backend per file type:
  images  -> Pillow (+ pillow-heif for iPhone HEIC / AVIF photos)
  audio / video -> ffmpeg
  pdf     -> PyMuPDF (images, text) and pdf2docx (Word)
  text / markup -> pandoc (PDF via pandoc -> docx -> LibreOffice)
  office docs   -> LibreOffice (soffice), docx/odt -> md/epub via pandoc
  tabular data  -> pandas (PDF via LibreOffice)

Only targets whose backend is actually installed are offered, so the radial
menu never shows an option that would fail. Quality options come from settings.py.
"""
from __future__ import annotations

import functools
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import settings

KINDS = {
    "image": {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "ico", "heic", "heif", "avif"},
    "audio": {"mp3", "wav", "flac", "ogg", "m4a", "aac", "wma", "opus"},
    "video": {"mp4", "mkv", "webm", "avi", "mov", "flv", "wmv", "m4v"},
    "text": {"md", "markdown", "html", "htm", "txt", "rtf", "epub"},
    "office": {"doc", "docx", "odt", "ppt", "pptx", "odp"},
    "sheet": {"xls", "xlsx", "ods", "csv", "tsv", "json"},
    "pdf": {"pdf"},
}

HEIF_EXTS = {"heic", "heif", "avif"}

TARGETS = {
    "image": ["png", "jpg", "webp", "bmp", "gif", "tiff", "ico", "pdf"],
    "audio": ["mp3", "wav", "flac", "ogg", "m4a", "aac", "opus"],
    "video": ["mp4", "mkv", "webm", "avi", "mov", "gif", "mp3"],
    "text": ["docx", "pdf", "html", "md", "txt", "epub", "odt"],
    "office": ["pdf", "docx", "odt", "txt", "html", "md"],
    "sheet": ["csv", "xlsx", "json", "tsv", "pdf"],
    "pdf": ["docx", "png", "jpg", "txt"],
}

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ---------------------------------------------------------------- helpers
def ext_of(path) -> str:
    return Path(path).suffix.lower().lstrip(".")


def _norm(ext: str) -> str:
    return {"jpeg": "jpg", "tif": "tiff", "htm": "html", "markdown": "md"}.get(ext, ext)


def kind_of(path) -> str | None:
    e = ext_of(path)
    for kind, exts in KINDS.items():
        if e in exts:
            return kind
    return None


def _bundled_dirs() -> list[Path]:
    """Folders that may hold ffmpeg.exe / pandoc.exe shipped with the app."""
    dirs = []
    if getattr(sys, "frozen", False):  # running as the packaged exe
        dirs.append(Path(sys.executable).parent / "bin")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(Path(meipass) / "bin")
    else:  # running from source: a ./bin folder (made by tools/fetch_tools.py) is optional
        dirs.append(Path(__file__).resolve().parent / "bin")
    return dirs


def _which(name: str) -> str | None:
    """Like shutil.which, but prefers copies bundled with the app."""
    for d in _bundled_dirs():
        for cand in (d / f"{name}.exe", d / name):
            if cand.is_file():
                return str(cand)
    return shutil.which(name)


def _soffice() -> str | None:
    found = _which("soffice") or _which("libreoffice")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
        cand = Path(base) / "LibreOffice" / "program" / "soffice.exe"
        if base and cand.exists():
            return str(cand)
    return None


def _import_ok(*modules: str) -> bool:
    for name in modules:
        try:
            __import__(name)
            return True
        except Exception:
            continue
    return False


def _have(tool: str) -> bool:
    if tool == "pillow":
        return _import_ok("PIL")
    if tool == "heif":
        return _import_ok("pillow_heif")
    if tool == "pandas":
        return _import_ok("pandas")
    if tool == "pymupdf":
        return _import_ok("pymupdf", "fitz")
    if tool == "pdf2docx":
        return _import_ok("pdf2docx")
    if tool == "soffice":
        return _soffice() is not None
    return _which(tool) is not None


def _tools_needed(kind: str, src: str, dst: str) -> list[str] | None:
    """Backends required for src->dst, or None if the pair is unsupported."""
    if kind == "image":
        return ["pillow", "heif"] if src in HEIF_EXTS else ["pillow"]
    if kind in ("audio", "video"):
        return ["ffmpeg"]
    if kind == "pdf":
        return ["pymupdf", "pdf2docx"] if dst == "docx" else ["pymupdf"]
    if kind == "text":
        return ["pandoc", "soffice"] if dst == "pdf" else ["pandoc"]
    if kind == "office":
        if dst == "md":
            return ["pandoc"] if src in ("docx", "odt") else None
        return ["soffice"]
    if kind == "sheet":
        if dst == "pdf":
            return None if src == "json" else ["soffice"]
        return ["pandas"]
    return None


# ---------------------------------------------------------------- ffmpeg encoders
# The bundled ffmpeg is an LGPL build, which has no libx264, so the H.264 encoder
# is picked at run time from whatever the installed ffmpeg actually offers.
AUDIO_ENCODERS = {
    "mp3": ("libmp3lame",),
    "ogg": ("libvorbis",),
    "opus": ("libopus",),
    "flac": ("flac",),
    "wav": ("pcm_s16le",),
    "m4a": ("aac",),
    "aac": ("aac",),
}
_LOSSY_AUDIO = {"mp3", "m4a", "aac", "ogg", "opus"}
_H264 = ("libx264", "libopenh264", "h264_mf")


@functools.lru_cache(maxsize=1)
def _encoders() -> frozenset[str]:
    exe = _which("ffmpeg")
    if not exe:
        return frozenset()
    try:
        out = subprocess.run(
            [exe, "-hide_banner", "-encoders"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
            creationflags=_NO_WINDOW, timeout=30,
        ).stdout
    except Exception:
        return frozenset()
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 6 and parts[0][0] in "VAS":
            names.add(parts[1])
    return frozenset(names)


def _pick(available, *names: str) -> str | None:
    return next((n for n in names if n in available), None)


def _video_encoder(fmt: str, available=None) -> str | None:
    available = _encoders() if available is None else available
    if fmt in ("mp4", "mkv", "mov"):
        return _pick(available, *_H264, "mpeg4")
    if fmt == "webm":
        return _pick(available, "libvpx-vp9", "libvpx")
    if fmt == "avi":
        return _pick(available, "mpeg4", *_H264)
    if fmt == "gif":
        return _pick(available, "gif")
    return None


def _ffmpeg_can_write(dst: str) -> bool:
    available = _encoders()
    if dst in AUDIO_ENCODERS:
        return any(e in available for e in AUDIO_ENCODERS[dst])
    return _video_encoder(dst, available) is not None


def _video_args(fmt: str, quality: str, available=None) -> list[str]:
    """Encoder + quality arguments for a video format. quality: high | medium | small."""
    available = _encoders() if available is None else available
    enc = _video_encoder(fmt, available)
    i = {"high": 0, "medium": 1, "small": 2}.get(quality, 0)
    if enc == "libx264":
        args = ["-c:v", "libx264", "-preset", "medium", "-crf", str((18, 23, 28)[i])]
    elif enc in ("libopenh264", "h264_mf"):
        args = ["-c:v", enc, "-b:v", ("8M", "4M", "1500k")[i]]
    elif enc == "mpeg4":
        args = ["-c:v", "mpeg4", "-q:v", str((2, 5, 9)[i])]
    elif enc == "libvpx-vp9":
        args = ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str((30, 36, 42)[i]), "-row-mt", "1"]
    elif enc == "libvpx":
        args = ["-c:v", "libvpx", "-b:v", ("4M", "2M", "800k")[i], "-crf", str((10, 20, 30)[i])]
    else:
        args = []
    if enc in _H264:
        args += ["-pix_fmt", "yuv420p"]
    return args


def _video_audio_args(fmt: str, bitrate: int, available=None) -> list[str]:
    available = _encoders() if available is None else available
    codec = None
    if fmt in ("mp4", "mkv", "mov"):
        codec = _pick(available, "aac")
    elif fmt == "webm":
        codec = _pick(available, "libopus", "libvorbis")
    elif fmt == "avi":
        codec = _pick(available, "libmp3lame")
    return (["-c:a", codec] if codec else []) + ["-b:a", f"{bitrate}k"]


def targets_for(path) -> list[str]:
    """Formats this file can be converted to, with working backends only."""
    kind = kind_of(path)
    if not kind:
        return []
    src = _norm(ext_of(path))
    out = []
    for dst in TARGETS[kind]:
        if dst == src:
            continue
        needed = _tools_needed(kind, src, dst)
        if not (needed and all(_have(t) for t in needed)):
            continue
        if kind in ("audio", "video") and not _ffmpeg_can_write(dst):
            continue
        out.append(dst)
    return out


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    i = 1
    while True:
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
        i += 1


def _run(cmd: list[str]) -> None:
    if not os.path.isabs(cmd[0]):
        cmd = [_which(cmd[0]) or cmd[0]] + cmd[1:]
    # stdin=DEVNULL: windowed (no-console) apps have no valid stdin, which breaks child processes on Windows
    proc = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, creationflags=_NO_WINDOW)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        raise RuntimeError(f"{Path(cmd[0]).name} failed: " + " | ".join(tail))


# ---------------------------------------------------------------- backends
def _image(src: Path, dst: Path, fmt: str) -> None:
    from PIL import Image, ImageOps

    if ext_of(src) in HEIF_EXTS:
        import pillow_heif

        pillow_heif.register_heif_opener()
    quality = int(settings.load()["image_quality"])

    with Image.open(src) as opened:
        im = ImageOps.exif_transpose(opened)  # iPhone photos store rotation in EXIF
        if fmt == "ico":
            im.convert("RGBA").save(dst, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            return
        if fmt in ("jpg", "bmp", "pdf") and im.mode in ("RGBA", "LA", "P"):
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            im = bg
        elif im.mode not in ("RGB", "RGBA", "L", "P"):
            im = im.convert("RGB")
        pil_fmt = {"jpg": "JPEG", "tiff": "TIFF", "pdf": "PDF"}.get(fmt, fmt.upper())
        options: dict = {}
        if fmt == "jpg":
            options = {"quality": quality, "optimize": True}
        elif fmt == "webp":
            options = {"quality": quality, "method": 4}
        elif fmt == "png":
            options = {"optimize": True}
        elif fmt == "pdf":
            options = {"quality": quality}
        im.save(dst, pil_fmt, **options)


def _ffmpeg(src: Path, dst: Path, fmt: str, kind: str) -> None:
    cfg = settings.load()
    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if fmt in AUDIO_ENCODERS:  # audio file, or audio extracted from a video
        cmd += ["-vn"]
        if fmt in _LOSSY_AUDIO:
            cmd += ["-b:a", f"{cfg['audio_bitrate']}k"]
    elif fmt == "gif":
        w = cfg["gif_width"]
        graph = (
            f"fps=12,scale='min({w},iw)':-1:flags=lanczos,split[s0][s1];"
            "[s0]palettegen[p];[s1][p]paletteuse"
        )
        cmd += ["-vf", graph, "-loop", "0"]
    else:
        cmd += _video_args(fmt, cfg["video_quality"])
        if cfg["video_max_width"]:
            cmd += ["-vf", f"scale='min({cfg['video_max_width']},iw)':-2"]
        cmd += _video_audio_args(fmt, int(cfg["audio_bitrate"]))
        if fmt == "mp4":
            cmd += ["-movflags", "+faststart"]
    _run(cmd + [str(dst)])


def _pdf(src: Path, dst: Path, fmt: str) -> Path:
    """PDF -> docx / txt / png / jpg (images: one file for 1 page, a folder of pages otherwise)."""
    if fmt == "docx":
        from pdf2docx import Converter

        cv = Converter(str(src))
        try:
            cv.convert(str(dst))
        finally:
            cv.close()
        return dst

    try:
        import pymupdf
    except ImportError:  # older PyMuPDF
        import fitz as pymupdf

    cfg = settings.load()
    dpi, quality = int(cfg["pdf_dpi"]), int(cfg["image_quality"])

    def save(pix, target: Path):
        if fmt == "jpg":
            try:
                pix.save(str(target), jpg_quality=quality)
                return
            except TypeError:
                pass
        pix.save(str(target))

    with pymupdf.open(src) as doc:
        if fmt == "txt":
            dst.write_text("\n\n".join(page.get_text() for page in doc), encoding="utf-8")
            return dst
        if len(doc) == 1:
            save(doc[0].get_pixmap(dpi=dpi), dst)
            return dst
        folder = _unique(src.with_name(f"{src.stem}_pages"))
        folder.mkdir()
        for n, page in enumerate(doc, 1):
            save(page.get_pixmap(dpi=dpi), folder / f"page_{n:03d}.{fmt}")
        return folder


def _pandoc(src: Path, dst: Path, fmt: str) -> None:
    cmd = ["pandoc", str(src), "-o", str(dst)]
    if fmt == "html":
        cmd.append("-s")
    if fmt == "epub":
        cmd += ["--metadata", f"title={src.stem}"]
    _run(cmd)


def _soffice_convert(src: Path, dst: Path, fmt: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _run([_soffice(), "--headless", "--convert-to", fmt, "--outdir", tmp, str(src)])
        produced = Path(tmp) / f"{src.stem}.{fmt}"
        if not produced.exists():
            raise RuntimeError("LibreOffice produced no output")
        shutil.move(str(produced), dst)


def _sheet(src: Path, dst: Path, src_ext: str, fmt: str) -> None:
    import pandas as pd

    if src_ext == "csv":
        df = pd.read_csv(src)
    elif src_ext == "tsv":
        df = pd.read_csv(src, sep="\t")
    elif src_ext == "json":
        df = pd.read_json(src)
    else:
        df = pd.read_excel(src)
    if fmt == "csv":
        df.to_csv(dst, index=False)
    elif fmt == "tsv":
        df.to_csv(dst, sep="\t", index=False)
    elif fmt == "json":
        df.to_json(dst, orient="records", indent=2, force_ascii=False)
    elif fmt == "xlsx":
        df.to_excel(dst, index=False)


# ---------------------------------------------------------------- public API
def convert(path, fmt: str) -> Path:
    """Convert `path` to `fmt`, writing next to the original. Returns output path."""
    src = Path(path)
    kind = kind_of(src)
    src_ext = _norm(ext_of(src))
    if not kind or fmt not in targets_for(src):
        raise ValueError(f"Cannot convert .{src_ext} to .{fmt} with the installed tools")
    dst = _unique(src.with_suffix(f".{fmt}"))

    if kind == "pdf":
        return _pdf(src, dst, fmt)
    if kind == "image":
        _image(src, dst, fmt)
    elif kind in ("audio", "video"):
        _ffmpeg(src, dst, fmt, kind)
    elif kind == "text":
        if fmt == "pdf":  # pandoc -> docx -> LibreOffice -> pdf
            with tempfile.TemporaryDirectory() as tmp:
                mid = Path(tmp) / f"{src.stem}.docx"
                _pandoc(src, mid, "docx")
                _soffice_convert(mid, dst, "pdf")
        else:
            _pandoc(src, dst, fmt)
    elif kind == "office":
        if fmt == "md":
            _pandoc(src, dst, fmt)
        else:
            _soffice_convert(src, dst, fmt)
    elif kind == "sheet":
        if fmt == "pdf":
            _soffice_convert(src, dst, fmt)
        else:
            _sheet(src, dst, src_ext, fmt)
    return dst