"""Settings window (opened from the tray menu or by right-clicking the drop circle)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

import settings

LABELS = {
    "video_quality": {"high": "High (bigger files)", "medium": "Medium", "small": "Small file (lower quality)"},
    "video_max_width": {
        0: "Keep original size",
        1920: "1080p (1920 px wide)",
        1280: "720p (1280 px wide)",
        854: "480p (854 px wide)",
        640: "360p (640 px wide)",
    },
    "gif_width": {w: f"{w} px wide" for w in settings.CHOICES["gif_width"]},
    "audio_bitrate": {b: f"{b} kbps" for b in settings.CHOICES["audio_bitrate"]},
    "pdf_dpi": {
        100: "100 DPI (small files)",
        150: "150 DPI (standard)",
        200: "200 DPI",
        300: "300 DPI (print quality)",
    },
}


def _combo(key: str) -> QComboBox:
    box = QComboBox()
    for value in settings.CHOICES[key]:
        box.addItem(LABELS[key][value], value)
    return box


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RadialConvert settings")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(420)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 100)
        self.spin = QSpinBox()
        self.spin.setRange(1, 100)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        quality_row = QHBoxLayout()
        quality_row.addWidget(self.slider, 1)
        quality_row.addWidget(self.spin)

        self.combos = {key: _combo(key) for key in settings.CHOICES}
        self.open_folder = QCheckBox("Open the folder when a conversion finishes")

        form = QFormLayout()
        form.addRow("Image quality (JPG, WebP)", quality_row)
        form.addRow("Video quality", self.combos["video_quality"])
        form.addRow("Video size limit", self.combos["video_max_width"])
        form.addRow("GIF width (from video)", self.combos["gif_width"])
        form.addRow("Audio bitrate (MP3, AAC, OGG, Opus)", self.combos["audio_bitrate"])
        form.addRow("PDF to image resolution", self.combos["pdf_dpi"])
        form.addRow(self.open_folder)

        hint = QLabel("PNG, FLAC and WAV are always lossless, so quality settings don't apply to them.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(lambda: self._load(settings.DEFAULTS))

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

        self._load(settings.load())

    def _load(self, cfg: dict):
        self.spin.setValue(cfg["image_quality"])
        for key, box in self.combos.items():
            box.setCurrentIndex(max(0, box.findData(cfg[key])))
        self.open_folder.setChecked(cfg["open_folder"])

    def _collect(self) -> dict:
        cfg = {"image_quality": self.spin.value(), "open_folder": self.open_folder.isChecked()}
        for key, box in self.combos.items():
            cfg[key] = box.currentData()
        return cfg

    def _save(self):
        settings.save(self._collect())
        self.accept()
