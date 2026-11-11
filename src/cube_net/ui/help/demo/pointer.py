# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Pointer`: the mouse pointer of an animation, drawn over its sheet.

It looks like the real one would at that spot (the cursors of `cursors.py`; an arrow where the app shows the system's
arrow or hand). A click shows a ring spreading from it, and while CTRL is held a key cap says so next to it: without
them a click or a held key couldn't be seen.

The README's animation shows it too: after changing it, run scripts/make_readme_animation.py.
"""

import time
from collections.abc import Callable
from functools import cache

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QWidget

from cube_net.ui.i18n import tr
from cube_net.ui.sheet.cursors import CURSOR_PX, OUTLINE, CursorKind, cursor_for

# How long the ring of a click spreads (ms), and how large it gets (px).
RIPPLE_MS = 450
RIPPLE_RADIUS_PX = 22.0

# The ring's colour.
RIPPLE = QColor(32, 33, 36, 150)

# The key cap shown while CTRL is held: its offset from the pointer's tip (px) and colours.
KEY_OFFSET = QPointF(20, 22)
KEY_FILL = QColor("#FFFFFF")
KEY_TEXT = QColor("#202124")

# How often (ms) the ring is repainted while it spreads.
FRAME_MS = 16


class Pointer(QWidget):
    """Covers its parent (the sheet's viewport) and lets every mouse event through. It keeps sheet positions, and
    `to_view` turns them into the viewport's pixels when it paints (the view may have zoomed since)."""

    def __init__(self, parent: QWidget, to_view: Callable[[QPointF], QPointF]) -> None:
        super().__init__(parent)
        self._to_view = to_view
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._position: QPointF | None = None
        self._kind = CursorKind.ARROW
        self._ctrl = False
        self._ripples: list[tuple[QPointF, float]] = []
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._tick)

    def set_state(self, position: QPointF, kind: CursorKind, ctrl: bool) -> None:
        """Where the tip is (sheet coordinates), what it looks like, and whether CTRL is held."""
        self._position, self._kind, self._ctrl = QPointF(position), kind, ctrl
        self.update()

    def position(self) -> QPointF | None:
        return None if self._position is None else QPointF(self._position)

    def kind(self) -> CursorKind:
        return self._kind

    def ripple(self) -> None:
        """A click: a ring spreads from the tip."""
        if self._position is not None:
            self._ripples.append((QPointF(self._position), time.monotonic()))
            self._timer.start()

    def _tick(self) -> None:
        now = time.monotonic()
        self._ripples = [(p, t) for p, t in self._ripples if now - t < RIPPLE_MS / 1000]
        if not self._ripples:
            self._timer.stop()
        self.update()

    def paintEvent(self, event: QPaintEvent | None) -> None:
        parent = self.parentWidget()
        if parent is not None and self.size() != parent.size():
            self.resize(parent.size())
        if self._position is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        now = time.monotonic()
        for spot, start in self._ripples:
            centre = self._to_view(spot)
            progress = min(1.0, (now - start) / (RIPPLE_MS / 1000))
            colour = QColor(RIPPLE)
            colour.setAlphaF(RIPPLE.alphaF() * (1 - progress))
            painter.setPen(QPen(colour, 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            radius = 4 + (RIPPLE_RADIUS_PX - 4) * progress
            painter.drawEllipse(centre, radius, radius)
        tip = self._to_view(self._position)
        if self._ctrl:
            self._paint_key(painter, tip + KEY_OFFSET, tr("Ctrl"))
        pixmap, hotspot = pointer_image(self._kind)
        painter.drawPixmap(tip - hotspot, pixmap)
        painter.end()

    def _paint_key(self, painter: QPainter, top_left: QPointF, text: str) -> None:
        font = QFont(self.font())
        font.setPointSizeF(font.pointSizeF() * 0.85)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        rect = QRectF(top_left, metrics.boundingRect(text).size().toSizeF()).adjusted(0, 0, 12, 6)
        painter.setPen(QPen(OUTLINE, 1.2))
        painter.setBrush(KEY_FILL)
        painter.drawRoundedRect(rect.translated(0, 2), 4, 4)  # the key's side
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(KEY_TEXT)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


def pointer_image(kind: CursorKind) -> tuple[QPixmap, QPointF]:
    """The picture of the pointer and where its tip is in it."""
    if kind in (CursorKind.ARROW, CursorKind.BUTTON):
        return _arrow()
    cursor = cursor_for(kind)
    return cursor.pixmap(), QPointF(cursor.hotSpot())


@cache
def _arrow() -> tuple[QPixmap, QPointF]:
    """The usual arrow: white with a dark outline, its tip in the top left corner."""
    ratio = 2.0
    pixmap = QPixmap(round(CURSOR_PX * ratio), round(CURSOR_PX * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    tip = QPointF(3, 2)
    shape = [(0, 0), (0, 17), (4.2, 13.2), (7, 19.5), (9.8, 18.3), (7.1, 12.2), (12.5, 12.2)]
    painter.setPen(QPen(OUTLINE, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawPolygon(QPolygonF([tip + QPointF(x, y) for x, y in shape]))
    painter.end()
    return pixmap, tip
