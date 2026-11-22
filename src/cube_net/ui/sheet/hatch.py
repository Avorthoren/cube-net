# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The hatch of the faces (docs/template_plan.md, §6.3): the same everywhere, tied to the grid, as if the whole sheet
were hatched and only the faces showed it. Every unit cell is tiled into `HATCH_COLUMNS` x `HATCH_ROWS` rectangles
(any positive numbers: below 1, a rectangle spans several cells), and the triangle above each one's diagonal from its
bottom-left corner up has the face's colour. A project's face shows it in its own frame (a unit square for the cube,
the template's grid for a body made from a template). A template's face with no colour yet is a white and grey
chessboard instead (`tiled_chessboard`).

Painted as paths, a face of many rectangles takes long (every triangle, every frame: dragging the sheet stutters). So
it's painted with a brush instead (`hatch_brush`, `chessboard_brush`): one rectangle of the pattern drawn once into a
small image, as large as it is on the screen at this zoom, which the brush repeats from the origin of the frame it's
painted in. Only where a rectangle would be too large for an image (zoomed in very far) are the paths used."""

import math
from collections.abc import Callable, Iterable

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPolygonF, QTransform

from cube_net.core.geometry import Vec
from cube_net.ui.sheet import net_style


def tiled_hatch(left: int, bottom: int, right: int, top: int) -> QPainterPath:
    """The hatch's coloured triangles over the unit cells from (left, bottom) to (right, top): every rectangle of the
    grid's tiling that reaches into them (the tiling starts at the sheet's origin, so its rectangles line up across
    faces whatever their size)."""
    path = QPainterPath()
    w, h = 1 / net_style.HATCH_COLUMNS, 1 / net_style.HATCH_ROWS
    for i in _indices(left, right, w):
        for j in _indices(bottom, top, h):
            x0, y0 = i * w, j * h
            path.addPolygon(QPolygonF([QPointF(x0, y0), QPointF(x0 + w, y0 + h), QPointF(x0, y0 + h)]))
            path.closeSubpath()
    return path


def tiled_chessboard(left: int, bottom: int, right: int, top: int) -> QPainterPath:
    """The grey squares of a template's face that has no colour yet, over the unit cells from (left, bottom) to (right,
    top): every rectangle of the hatch is halved across its longer side (a 1 x 1/2 one into two 1/2 x 1/2 squares), and
    the halves are white and grey in turns, like a chessboard."""
    path = QPainterPath()
    w, h = 1 / net_style.HATCH_COLUMNS, 1 / net_style.HATCH_ROWS
    if w >= h:
        w /= 2
    else:
        h /= 2
    for i in _indices(left, right, w):
        for j in _indices(bottom, top, h):
            if (i + j) % 2:
                path.addRect(QRectF(i * w, j * h, w, h))
    return path


def _indices(low: int, high: int, size: float) -> range:
    """Which rectangles of `size` (counted from 0) reach into [low, high]."""
    return range(math.floor(low / size), math.ceil(high / size))


def cells_around(points: Iterable[Vec]) -> tuple[int, int, int, int]:
    """The unit cells that cover the points: (left, bottom, right, top), whole numbers."""
    xs, ys = zip(*((p.x, p.y) for p in points), strict=True)
    return math.floor(min(xs)), math.floor(min(ys)), math.ceil(max(xs)), math.ceil(max(ys))


# The largest image of a brush's rectangle, in pixels across: beyond that the paths are painted instead.
MAX_TILE_PX = 512

# The brushes made, by what they look like and how large their image is (few: a zoom, a style, some colours).
_BRUSHES: dict[tuple[object, ...], QBrush] = {}

# More than this many brushes, and the older ones are forgotten (after zooming a lot, say).
MAX_BRUSHES = 256


def hatch_brush(color: QColor, transform: QTransform) -> QBrush | None:
    """The hatch in `color`, for a painter with this transform (from the frame the brush is used in to device pixels);
    None if a rectangle of it would be too large: then `tiled_hatch` it is."""
    w, h = 1 / net_style.HATCH_COLUMNS, 1 / net_style.HATCH_ROWS

    def draw(painter: QPainter, width: int, height: int) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(width, height), QPointF(0, height)]))

    return _tile_brush(("hatch", color.rgba()), w, h, 1, 1, transform, draw)


def chessboard_brush(color: QColor, transform: QTransform) -> QBrush | None:
    """The chessboard's grey squares in `color`, like `hatch_brush` (a brush of 2 x 2 halves of a rectangle)."""
    w, h = 1 / net_style.HATCH_COLUMNS, 1 / net_style.HATCH_ROWS
    if w >= h:
        w /= 2
    else:
        h /= 2

    def draw(painter: QPainter, width: int, height: int) -> None:
        half_w, half_h = width // 2, height // 2
        painter.fillRect(half_w, 0, width - half_w, half_h, color)  # the halves (1, 0) and (0, 1) are grey
        painter.fillRect(0, half_h, half_w, height - half_h, color)

    return _tile_brush(("chessboard", color.rgba()), 2 * w, 2 * h, 2, 2, transform, draw)


def _tile_brush(
    kind: tuple[object, ...],
    w: float,
    h: float,
    multiple: int,
    multiple_h: int,
    transform: QTransform,
    draw: Callable[[QPainter, int, int], None],
) -> QBrush | None:
    """A brush repeating a w x h rectangle (in the painter's units) from the origin: drawn by `draw` into an image of
    the size it has on the device (its sides whole multiples of `multiple` and `multiple_h` pixels)."""
    x_px = math.hypot(transform.m11(), transform.m12())  # a unit along x, on the device (the frame may be turned)
    y_px = math.hypot(transform.m21(), transform.m22())
    width = multiple * max(1, round(w * x_px / multiple))
    height = multiple_h * max(1, round(h * y_px / multiple_h))
    if width > MAX_TILE_PX or height > MAX_TILE_PX:
        return None
    key = (*kind, width, height, w, h)
    brush = _BRUSHES.get(key)
    if brush is None:
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw(painter, width, height)
        painter.end()
        brush = QBrush(image)
        brush.setTransform(QTransform.fromScale(w / width, h / height))  # the image's pixels onto the rectangle
        if len(_BRUSHES) >= MAX_BRUSHES:
            _BRUSHES.clear()
        _BRUSHES[key] = brush
    return brush
