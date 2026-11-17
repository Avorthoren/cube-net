# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The hatch of the faces (docs/template_plan.md, §6.3): the same everywhere, tied to the grid, as if the whole sheet
were hatched and only the faces showed it. Every unit cell is tiled into `HATCH_COLUMNS` x `HATCH_ROWS` rectangles,
and the triangle above each one's diagonal from its bottom-left corner up has the face's colour. A project's face
shows it in its own frame (a unit square for the cube, the template's grid for a body made from a template)."""

import math
from collections.abc import Iterable

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainterPath, QPolygonF

from cube_net.core.geometry import Vec
from cube_net.ui.sheet import net_style


def tiled_hatch(left: int, bottom: int, right: int, top: int) -> QPainterPath:
    """The hatch's coloured triangles over the unit cells from (left, bottom) to (right, top)."""
    path = QPainterPath()
    w, h = 1 / net_style.HATCH_COLUMNS, 1 / net_style.HATCH_ROWS
    for i in range((right - left) * net_style.HATCH_COLUMNS):
        for j in range((top - bottom) * net_style.HATCH_ROWS):
            x0, y0 = left + i * w, bottom + j * h
            path.addPolygon(QPolygonF([QPointF(x0, y0), QPointF(x0 + w, y0 + h), QPointF(x0, y0 + h)]))
            path.closeSubpath()
    return path


def cells_around(points: Iterable[Vec]) -> tuple[int, int, int, int]:
    """The unit cells that cover the points: (left, bottom, right, top), whole numbers."""
    xs, ys = zip(*((p.x, p.y) for p in points), strict=True)
    return math.floor(min(xs)), math.floor(min(ys)), math.ceil(max(xs)), math.ceil(max(ys))
