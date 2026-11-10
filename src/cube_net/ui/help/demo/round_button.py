# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`RoundButton`: the big round button over an animation: play (a triangle) before it starts, replay (an arrow going
round) after it ends."""

import math
from enum import Enum

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QEnterEvent, QMouseEvent, QPainter, QPainterPath, QPaintEvent, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

# The button's diameter (px).
DIAMETER_PX = 72

# Its disc (a little darker while the mouse is over it) and its symbol.
DISC = QColor(32, 33, 36, 150)
DISC_HOVERED = QColor(32, 33, 36, 200)
SYMBOL = QColor("#FFFFFF")


class Symbol(Enum):
    # Start the animation.
    PLAY = "play"

    # Start it again from the beginning.
    REPLAY = "replay"


class RoundButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(QSize(DIAMETER_PX, DIAMETER_PX))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._symbol = Symbol.PLAY
        self._hovered = False

    def symbol(self) -> Symbol:
        return self._symbol

    def set_symbol(self, symbol: Symbol) -> None:
        self._symbol = symbol
        self.update()

    def enterEvent(self, event: QEnterEvent | None) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self._hovered = False
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()

    def paintEvent(self, event: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(DISC_HOVERED if self._hovered else DISC)
        painter.drawEllipse(QRectF(self.rect()).adjusted(1, 1, -1, -1))
        r = DIAMETER_PX / 2
        centre = QPointF(r, r)
        if self._symbol is Symbol.PLAY:
            painter.setBrush(SYMBOL)
            size = r * 0.42
            # A triangle pointing right, moved a little right so that it looks in the middle.
            shift = QPointF(size * 0.18, 0)
            points = [QPointF(-size * 0.75, -size), QPointF(-size * 0.75, size), QPointF(size * 1.05, 0)]
            painter.drawPolygon(QPolygonF([centre + shift + p for p in points]))
        else:
            self._paint_replay(painter, centre, r * 0.4)
        painter.end()

    def _paint_replay(self, painter: QPainter, centre: QPointF, radius: float) -> None:
        """Most of a circle, clockwise from the top, with an arrow head where it ends."""
        width = radius * 0.32
        painter.setPen(QPen(SYMBOL, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(centre.x() - radius, centre.y() - radius, 2 * radius, 2 * radius)
        start, span = 60.0, -300.0  # degrees, Qt's: counterclockwise from three o'clock; negative is clockwise
        arc = QPainterPath()
        arc.arcMoveTo(rect, start)
        arc.arcTo(rect, start, span)
        painter.drawPath(arc)
        end = math.radians(start + span)
        tip = QPointF(centre.x() + radius * math.cos(end), centre.y() - radius * math.sin(end))
        # The head points along the arc's direction at its end (clockwise: the tangent turned to the right).
        forward = QPointF(math.sin(end), math.cos(end))
        side = QPointF(-forward.y(), forward.x())
        head = width * 1.9
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(SYMBOL)
        painter.drawPolygon(QPolygonF([tip + forward * head * 0.9, tip + side * head * 0.8, tip - side * head * 0.8]))
