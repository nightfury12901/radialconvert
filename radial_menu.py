"""Circular (pie / radial) menu widget that pops up centred on the cursor."""
from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class RadialMenu(QWidget):
    chosen = Signal(str)
    cancelled = Signal()

    SIZE = 460
    OUTER = 200
    INNER = 70
    GAP = 2.0  # degrees between segments

    BASE = QColor(28, 28, 32, 228)
    HOVER = QColor(255, 140, 0, 245)

    def __init__(self, title: str, items: list[str], parent=None):
        super().__init__(parent)
        self.title = title
        self.items = items
        self.hover = -1
        self._done = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.resize(self.SIZE, self.SIZE)

    # ------------------------------------------------------------ showing
    def show_at(self, pos):
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        half = self.SIZE // 2
        x = min(max(pos.x() - half, geo.left()), geo.right() - self.SIZE)
        y = min(max(pos.y() - half, geo.top()), geo.bottom() - self.SIZE)
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def _finish(self, fmt: str | None):
        if self._done:
            return
        self._done = True
        self.close()
        if fmt:
            self.chosen.emit(fmt)
        else:
            self.cancelled.emit()

    # ------------------------------------------------------------ geometry
    def _index_at(self, pos) -> int:
        dx = pos.x() - self.width() / 2
        dy = pos.y() - self.height() / 2
        r = math.hypot(dx, dy)
        if not (self.INNER < r < self.OUTER):
            return -1
        angle = math.degrees(math.atan2(-dy, dx))  # counter-clockwise from east
        clockwise_from_top = (90 - angle) % 360
        return int(clockwise_from_top // (360 / len(self.items)))

    # ------------------------------------------------------------ painting
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))  # near-invisible: lets clicks outside the ring register

        c = QPointF(self.width() / 2, self.height() / 2)
        O, I = self.OUTER, self.INNER
        outer = QRectF(c.x() - O, c.y() - O, 2 * O, 2 * O)
        inner = QRectF(c.x() - I, c.y() - I, 2 * I, 2 * I)
        n = len(self.items)
        seg = 360.0 / n

        label_font = QFont("Segoe UI", 13, QFont.Bold)
        for i, label in enumerate(self.items):
            start = 90 - i * seg - self.GAP / 2
            span = -(seg - self.GAP)
            path = QPainterPath()
            path.arcMoveTo(outer, start)
            path.arcTo(outer, start, span)
            path.arcTo(inner, start + span, -span)
            path.closeSubpath()

            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            p.setBrush(self.HOVER if i == self.hover else self.BASE)
            p.drawPath(path)

            mid = math.radians(90 - (i + 0.5) * seg)
            rmid = (O + I) / 2
            tx, ty = c.x() + rmid * math.cos(mid), c.y() - rmid * math.sin(mid)
            p.setFont(label_font)
            p.setPen(QColor(20, 20, 20) if i == self.hover else QColor(240, 240, 240))
            p.drawText(QRectF(tx - 40, ty - 14, 80, 28), Qt.AlignCenter, label.upper())

        # centre disc
        p.setPen(QPen(QColor(255, 255, 255, 50), 1))
        p.setBrush(QColor(20, 20, 24, 235))
        p.drawEllipse(c, I - 8, I - 8)
        title_font = QFont("Segoe UI", 9)
        p.setFont(title_font)
        p.setPen(QColor(230, 230, 230))
        text = QFontMetrics(title_font).elidedText(self.title, Qt.ElideMiddle, 2 * (I - 18))
        p.drawText(QRectF(c.x() - I + 10, c.y() - 22, 2 * I - 20, 24), Qt.AlignCenter, text)
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(255, 140, 0))
        p.drawText(QRectF(c.x() - I + 10, c.y() + 2, 2 * I - 20, 18), Qt.AlignCenter, "convert to…")

    # ------------------------------------------------------------ input
    def mouseMoveEvent(self, e):
        idx = self._index_at(e.position())
        if idx != self.hover:
            self.hover = idx
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            idx = self._index_at(e.position())
            self._finish(self.items[idx] if idx >= 0 else None)
        else:
            self._finish(None)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._finish(None)
        elif Qt.Key_1 <= e.key() <= Qt.Key_9:
            i = e.key() - Qt.Key_1
            if i < len(self.items):
                self._finish(self.items[i])

    def event(self, e):
        if e.type() == QEvent.WindowDeactivate:
            self._finish(None)
        return super().event(e)
