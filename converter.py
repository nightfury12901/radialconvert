"""Conversion engine.

Picks a backend per file type:
  images  -> Pillow
  audio / video -> ffmpeg
  text / markup -> pandoc (PDF via pandoc -> docx -> LibreOffice)
  office docs   -> LibreOffice (soffice), docx/odt -> md/epub via pandoc
  tabular data  -> pandas (PDF via LibreOffice)

Only targets whose backend is actually installed are offered, so the radial
menu never shows an option that would fail.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KINDS = {
    "image": {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "ico"},
    "audio": {"mp3", "wav", "flac", "ogg", "m4a", "aac", "wma", "opus"},
    "video": {"mp4", "mkv", "webm", "avi", "mov", "flv", "wmv", "m4v"},
    "text": {"md", "markdown", "html", "htm", "txt", "rtf", "epub"},
    "office": {"doc", "docx", "odt", "ppt", "pptx", "odp"},
    "sheet": {"xls", "xlsx", "ods", "csv", "tsv", "json"},
    "pdf": {"pdf"},
}

TARGETS = {
    "image": ["png", "jpg", "webp", "bmp", "gif", "tiff", "ico", "pdf"],
    "audio": ["mp3", "wav", "flac", "ogg", "m4a", "aac"],
    "video": ["mp4", "mkv", "webm", "avi", "mov", "gif", "mp3"],
    "text": ["docx", "pdf", "html", "md", "txt", "epub", "odt"],
    "office": ["pdf", "docx", "odt", "txt", "html", "md"],
    "sheet": ["csv", "xlsx", "json", "tsv", "pdf"],
    "pdf": ["png", "jpg", "txt"],
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


def _have(tool: str) -> bool:
    if tool == "pillow":
        try:
            import PIL  # noqa: F401
            return True
        except ImportError:
            return False
    if tool == "pandas":
        try:
            import pandas  # noqa: F401
            return True
        except ImportError:
            return False
    if tool == "pymupdf":
        try:
            import fitz  # noqa: F401
            return True
        except ImportError:
            return False
    if tool == "soffice":
        return _soffice() is not None
    return _which(tool) is not None


def _tools_needed(kind: str, src: str, dst: str) -> list[str] | None:
    """Backends required for src->dst, or None if the pair is unsupported."""
    if kind == "image":
        return ["pillow"]
    if kind in ("audio", "video"):
        return ["ffmpeg"]
    if kind == "pdf":
        return ["pymupdf"]
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
        if needed and all(_have(t) for t in needed):
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
    from PIL import Image

    with Image.open(src) as im:
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
        im.save(dst, pil_fmt)


def _ffmpeg(src: Path, dst: Path, fmt: str, kind: str) -> None:
    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if fmt == "gif" and kind == "video":
        cmd += ["-vf", "fps=12,scale=480:-1:flags=lanczos"]
    elif kind == "video" and fmt in ("mp3", "wav", "flac", "ogg", "m4a", "aac"):
        cmd += ["-vn"]
    _run(cmd + [str(dst)])


def _pdf(src: Path, dst: Path, fmt: str) -> Path:
    """PDF -> txt, or png/jpg (one file for a 1-page PDF, a folder of pages otherwise)."""
    import fitz  # PyMuPDF

    with fitz.open(src) as doc:
        if fmt == "txt":
            dst.write_text("\n\n".join(page.get_text() for page in doc), encoding="utf-8")
            return dst
        if len(doc) == 1:
            doc[0].get_pixmap(dpi=150).save(str(dst))
            return dst
        folder = _unique(src.with_name(f"{src.stem}_pages"))
        folder.mkdir()
        for n, page in enumerate(doc, 1):
            page.get_pixmap(dpi=150).save(str(folder / f"page_{n:03d}.{fmt}"))
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
