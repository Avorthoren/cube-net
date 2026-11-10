# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Mouse cursors that tell what a click on the sheet would do (docs/idea.txt): scissors (start or go on cutting), a
pencil (edit the cut line), a glue tube (glue the halves onto this cut), a plus (add a point), an x (delete one). Qt
has none of them, so they're drawn here:
white shapes with a dark outline, visible on every colour of the net and the sheet."""

from enum import Enum
from functools import cache

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QTransform

# The size of a cursor image, in logical pixels.
CURSOR_PX = 32

OUTLINE = QColor("#202124")
FILL = QColor("#FFFFFF")

# The plus (adding a point) and the x (deleting one).
PLUS_FILL = QColor("#34A853")
DELETE_FILL = QColor("#D93025")

# The pencil's wood, its eraser and the glue tube's nozzle and drop.
PENCIL_BODY = QColor("#FFD54F")
PENCIL_ERASER = QColor("#F48FB1")
GLUE_NOZZLE = QColor("#FF8A65")
GLUE_DROP = QColor("#E3F2FD")


class CursorKind(Enum):
    # The usual arrow: a click means nothing special here.
    ARROW = "arrow"

    # A click starts the cut line, or adds a point to it.
    SCISSORS = "scissors"

    # A point of the cut line can be dragged here, or a new one made.
    PENCIL = "pencil"

    # A click glues the halves onto this cut (the rearrangement).
    GLUE = "glue"

    # A click adds a point to the cut line here (the circle in the middle of a segment).
    PLUS = "plus"

    # A click deletes this point of the cut line (CTRL is held).
    DELETE = "delete"

    # Over a button.
    BUTTON = "button"


def cursor_for(kind: CursorKind) -> QCursor:
    if kind is CursorKind.ARROW:
        return QCursor(Qt.CursorShape.ArrowCursor)
    if kind is CursorKind.BUTTON:
        return QCursor(Qt.CursorShape.PointingHandCursor)
    return _drawn(kind)


@cache
def _drawn(kind: CursorKind) -> QCursor:
    ratio = _device_pixel_ratio()
    pixmap = QPixmap(round(CURSOR_PX * ratio), round(CURSOR_PX * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(OUTLINE, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    draw = {
        CursorKind.SCISSORS: _scissors,
        CursorKind.PENCIL: _pencil,
        CursorKind.GLUE: _glue,
        CursorKind.PLUS: _plus,
        CursorKind.DELETE: _delete,
    }[kind]
    hotspot = draw(painter)
    painter.end()
    return QCursor(pixmap, round(hotspot.x()), round(hotspot.y()))


def _device_pixel_ratio() -> float:
    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 1.0


def _scissors(painter: QPainter) -> QPointF:
    """Two halves crossing at a pivot: open blades pointing up-left, rings at the bottom right. The hot spot is where
    the blades' tips are."""
    pivot = QPointF(15, 15)
    painter.setBrush(FILL)
    for tip, ring in ((QPointF(9, 2), QPointF(21, 27)), (QPointF(2, 9), QPointF(27, 21))):
        along = pivot - tip
        length = (along.x() ** 2 + along.y() ** 2) ** 0.5
        across = QPointF(-along.y(), along.x()) / length * 2.6
        painter.drawPolygon(QPolygonF([tip, pivot + across, pivot - across]))  # the blade, widening to the pivot
        painter.drawLine(pivot, ring)  # the shank
    for ring in (QPointF(21, 27), QPointF(27, 21)):
        painter.setBrush(FILL)
        painter.drawEllipse(ring, 4.2, 4.2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(ring, 1.8, 1.8)
    painter.setBrush(OUTLINE)
    painter.drawEllipse(pivot, 1.3, 1.3)
    return QPointF(5, 5)


def _pencil(painter: QPainter) -> QPointF:
    """A pencil pointing down-left; the hot spot is its tip."""
    tip = QPointF(3, 29)
    painter.save()
    painter.translate(tip)
    painter.rotate(-45)
    painter.setBrush(FILL)
    painter.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(8, -4), QPointF(8, 4)]))
    painter.setBrush(OUTLINE)
    painter.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(3, -1.5), QPointF(3, 1.5)]))
    painter.setBrush(PENCIL_BODY)
    painter.drawRect(QRectF(8, -4, 22, 8))
    painter.setBrush(PENCIL_ERASER)
    painter.drawRect(QRectF(30, -4, 5, 8))
    painter.restore()
    return tip


def _glue(painter: QPainter) -> QPointF:
    """A tube of glue pointing up-left, with a drop coming out of its nozzle; the hot spot is the drop."""
    painter.save()
    painter.translate(17, 17)
    painter.rotate(-45)  # drawn pointing up, so it points up-left
    drop = painter.transform().map(QPointF(0, -16))
    painter.setBrush(GLUE_DROP)
    path = QPainterPath(QPointF(0, -19))
    path.cubicTo(QPointF(2.5, -16.5), QPointF(2.5, -14), QPointF(0, -14))
    path.cubicTo(QPointF(-2.5, -14), QPointF(-2.5, -16.5), QPointF(0, -19))
    painter.drawPath(path)
    painter.setBrush(GLUE_NOZZLE)
    painter.drawPolygon(QPolygonF([QPointF(-1.5, -12), QPointF(1.5, -12), QPointF(3, -7), QPointF(-3, -7)]))
    painter.setBrush(FILL)
    painter.drawPolygon(QPolygonF([QPointF(-3, -7), QPointF(3, -7), QPointF(5.5, -4), QPointF(-5.5, -4)]))
    painter.drawRoundedRect(QRectF(-5.5, -4, 11, 16), 1.5, 1.5)
    painter.setBrush(OUTLINE)
    painter.drawRect(QRectF(-6.5, 12, 13, 2.5))
    painter.restore()
    return drop


def _thick_shape(painter: QPainter, path: QPainterPath, fill: QColor) -> None:
    painter.save()
    painter.setPen(QPen(OUTLINE, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin))
    painter.setBrush(fill)
    path.setFillRule(Qt.FillRule.WindingFill)  # the bars overlap: fill where they cross too
    painter.drawPath(path.simplified())
    painter.restore()


# The plus's bounding square, its top left corner and the width of its bars.
PLUS_SIZE = 20.0
PLUS_CORNER = QPointF(2, 2)
PLUS_BAR = 6.0


def _plus_path() -> QPainterPath:
    middle = (PLUS_SIZE - PLUS_BAR) / 2
    left, top = PLUS_CORNER.x(), PLUS_CORNER.y()
    path = QPainterPath()
    path.addRect(QRectF(left + middle, top, PLUS_BAR, PLUS_SIZE))
    path.addRect(QRectF(left, top + middle, PLUS_SIZE, PLUS_BAR))
    return path


def _plus(painter: QPainter) -> QPointF:
    """A thick green plus with a black outline; the hot spot is its upper left inner corner, where the bars meet."""
    _thick_shape(painter, _plus_path(), PLUS_FILL)
    middle = (PLUS_SIZE - PLUS_BAR) / 2
    return PLUS_CORNER + QPointF(middle, middle)


def _delete(painter: QPainter) -> QPointF:
    """The plus turned by 45 degrees, red: an x of the same size. The hot spot is its middle."""
    centre = PLUS_CORNER + QPointF(PLUS_SIZE / 2, PLUS_SIZE / 2)
    turn = QTransform().translate(centre.x(), centre.y()).rotate(45).translate(-centre.x(), -centre.y())
    _thick_shape(painter, turn.map(_plus_path()), DELETE_FILL)
    return centre
