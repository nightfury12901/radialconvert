"""User settings, stored as JSON in %LOCALAPPDATA%\\RadialConvert\\settings.json.

Read fresh on every conversion, so changes apply immediately. Invalid or missing
values silently fall back to the defaults.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "image_quality": 90,      # JPG / WebP / PDF->JPG, 1-100
    "video_quality": "high",  # high | medium | small
    "video_max_width": 0,     # 0 = keep original size
    "gif_width": 480,         # max width of GIFs made from video
    "audio_bitrate": 192,     # kbps for MP3 / AAC / M4A / OGG / Opus
    "pdf_dpi": 150,           # resolution when turning PDF pages into images
    "open_folder": True,      # show the result in Explorer when done
}

CHOICES = {
    "video_quality": ("high", "medium", "small"),
    "video_max_width": (0, 1920, 1280, 854, 640),
    "gif_width": (320, 480, 640, 800),
    "audio_bitrate": (96, 128, 192, 256, 320),
    "pdf_dpi": (100, 150, 200, 300),
}


def path() -> Path:
    base = os.environ.get("RADIALCONVERT_DIR") or (
        Path(os.environ.get("LOCALAPPDATA", Path.home())) / "RadialConvert"
    )
    return Path(base) / "settings.json"


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
    except Exception:
        return cfg
    if not isinstance(data, dict):
        return cfg
    for key, value in data.items():
        if key not in DEFAULTS:
            continue
        if key == "image_quality":
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cfg[key] = max(1, min(100, int(value)))
        elif key == "open_folder":
            if isinstance(value, bool):
                cfg[key] = value
        elif value in CHOICES[key]:
            cfg[key] = value
    return cfg


def save(cfg: dict) -> None:
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    clean = {k: cfg[k] for k in DEFAULTS if k in cfg}
    p.write_text(json.dumps(clean, indent=2), encoding="utf-8")
