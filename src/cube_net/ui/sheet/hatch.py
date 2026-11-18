# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The hatch of the faces (docs/template_plan.md, §6.3): the same everywhere, tied to the grid, as if the whole sheet
were hatched and only the faces showed it. Every unit cell is tiled into `HATCH_COLUMNS` x `HATCH_ROWS` rectangles
(any positive numbers: below 1, a rectangle spans several cells), and the triangle above each one's diagonal from its
bottom-left corner up has the face's colour. A project's face shows it in its own frame (a unit square for the cube,
the template's grid for a body made from a template). A template's face with no colour yet is a white and grey
chessboard instead (`tiled_chessboard`)."""

import math
from collections.abc import Iterable

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainterPath, QPolygonF

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
