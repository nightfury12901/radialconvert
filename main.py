"""RadialConvert - convert any file to any format from a circular menu.

Usage:
  python main.py                 tray app + floating drop circle
  python main.py "C:\\path\\file"  open the radial menu for that file right away
                                 (this is what the Explorer right-click entry runs)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QSystemTrayIcon, QWidget

import converter
from radial_menu import RadialMenu

ORANGE = QColor(255, 140, 0)


def make_icon(size=64) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(ORANGE)
    p.setPen(Qt.NoPen)
    p.drawEllipse(2, 2, size - 4, size - 4)
    p.setPen(QColor(30, 30, 30))
    p.setFont(QFont("Segoe UI", int(size * 0.4), QFont.Bold))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "⇄")
    p.end()
    return QIcon(pm)


class Worker(QThread):
    done = Signal(bool, str)

    def __init__(self, src: str, fmt: str):
        super().__init__()
        self.src, self.fmt = src, fmt

    def run(self):
        try:
            self.done.emit(True, str(converter.convert(self.src, self.fmt)))
        except Exception as exc:  # surfaced to the user as a tray message
            self.done.emit(False, str(exc))


class DropCircle(QWidget):
    """Small always-on-top orange circle. Drop a file on it, or double-click to browse."""

    def __init__(self, on_file):
        super().__init__()
        self.on_file = on_file
        self._drag = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.resize(84, 84)
        self.setToolTip("Drop a file here (double-click to browse)")
        self._hot = False

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(255, 170, 40) if self._hot else ORANGE)
        p.setPen(QColor(255, 255, 255, 120))
        p.drawEllipse(3, 3, 78, 78)
        p.setPen(QColor(30, 30, 30))
        p.setFont(QFont("Segoe UI", 26, QFont.Bold))
        p.drawText(self.rect(), Qt.AlignCenter, "⇄")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            self._hot = True
            self.update()
            e.acceptProposedAction()

    def dragLeaveEvent(self, _):
        self._hot = False
        self.update()

    def dropEvent(self, e):
        self._hot = False
        self.update()
        urls = e.mimeData().urls()
        if urls:
            self.on_file(urls[0].toLocalFile())

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None

    def mouseDoubleClickEvent(self, _):
        self.on_file(None)


class RadialConvert:
    def __init__(self, app: QApplication, cli_file: str | None):
        self.app = app
        self.cli = cli_file is not None
        self.menu = None
        self.workers: set[Worker] = set()
        self.last_output: str | None = None

        self.tray = QSystemTrayIcon(make_icon())
        self.tray.setToolTip("RadialConvert")
        tray_menu = QMenu()
        act_pick = QAction("Convert file…", tray_menu, triggered=lambda: self.pick_file())
        act_circle = QAction("Show / hide drop circle", tray_menu, triggered=self.toggle_circle)
        act_quit = QAction("Quit", tray_menu, triggered=app.quit)
        for a in (act_pick, act_circle, act_quit):
            tray_menu.addAction(a)
        self.tray.setContextMenu(tray_menu)
        self.tray._menu = tray_menu  # keep a reference alive
        self.tray.activated.connect(
            lambda reason: self.pick_file() if reason == QSystemTrayIcon.Trigger else None
        )
        self.tray.messageClicked.connect(self.reveal_output)
        self.tray.show()

        self.circle = None
        if self.cli:
            QTimer.singleShot(0, lambda: self.open_menu(cli_file))
        else:
            self.circle = DropCircle(lambda path: self.open_menu(path) if path else self.pick_file())
            geo = app.primaryScreen().availableGeometry()
            self.circle.move(geo.right() - 120, geo.bottom() - 160)
            self.circle.show()

    # ---------------------------------------------------------- actions
    def toggle_circle(self):
        if self.circle:
            self.circle.setVisible(not self.circle.isVisible())

    def pick_file(self):
        path, _ = QFileDialog.getOpenFileName(None, "Choose a file to convert")
        if path:
            self.open_menu(path)

    def open_menu(self, path: str):
        path = os.path.abspath(path)
        targets = converter.targets_for(path)
        if not targets:
            kind = converter.kind_of(path)
            hint = "Unsupported file type." if not kind else "Install ffmpeg / pandoc / LibreOffice for more formats."
            self.tray.showMessage("Nothing to convert to", f"{Path(path).name}: {hint}", QSystemTrayIcon.Warning)
            if self.cli:
                QTimer.singleShot(4000, self.app.quit)
            return
        self.menu = RadialMenu(Path(path).name, targets)
        self.menu.chosen.connect(lambda fmt: self.start(path, fmt))
        self.menu.cancelled.connect(lambda: self.app.quit() if self.cli else None)
        self.menu.show_at(QCursor.pos())

    def start(self, path: str, fmt: str):
        self.tray.showMessage("Converting…", f"{Path(path).name} → .{fmt}", QSystemTrayIcon.Information, 2000)
        w = Worker(path, fmt)
        self.workers.add(w)
        w.done.connect(lambda ok, msg, w=w: self.finished(w, ok, msg))
        w.start()

    def finished(self, worker: Worker, ok: bool, msg: str):
        self.workers.discard(worker)
        if ok:
            self.last_output = msg
            self.tray.showMessage("Done", f"Saved {Path(msg).name} (click to show in folder)", QSystemTrayIcon.Information, 5000)
        else:
            self.tray.showMessage("Conversion failed", msg, QSystemTrayIcon.Critical, 8000)
        if self.cli and not self.workers:
            QTimer.singleShot(6000, self.app.quit)

    def reveal_output(self):
        if self.last_output and sys.platform == "win32":
            os.startfile(str(Path(self.last_output).parent))


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    cli_file = sys.argv[1] if len(sys.argv) > 1 else None
    _keep = RadialConvert(app, cli_file)  # noqa: F841
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
