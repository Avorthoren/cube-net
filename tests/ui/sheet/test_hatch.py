# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction

import pytest
from PyQt6.QtCore import QRectF

from cube_net.core.geometry import Vec
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.hatch import cells_around, tiled_hatch


def test_the_hatch_is_tiled_over_whole_units() -> None:
    path = tiled_hatch(0, 0, 2, 1)
    assert path.boundingRect() == QRectF(0, 0, 2, 1)
    assert path.elementCount() == 2 * net_style.HATCH_COLUMNS * net_style.HATCH_ROWS * 4  # 3 corners, closed


def test_it_covers_half_of_a_unit() -> None:
    path = tiled_hatch(0, 0, 1, 1)
    area = 0.0
    for i in range(path.elementCount() // 4):  # 4 elements per closed triangle
        a, b, c = (path.elementAt(4 * i + j) for j in range(3))
        area += abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) / 2
    assert area == pytest.approx(0.5)


@pytest.mark.parametrize(("columns", "rows"), [(1, 2), (2, 1), (8, 2), (3, 3)])
def test_the_chessboard_halves_every_hatch_rectangle(columns: int, rows: int) -> None:
    """Grey halves alternate with white ones: a 1 x 1/2 rectangle of the hatch is two 1/2 x 1/2 squares, one grey."""
    from cube_net.ui.sheet.hatch import tiled_chessboard

    net_style.set_sizes(
        net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX, columns, rows, net_style.DASHES_PER_EDGE, 1.0
    )
    board = tiled_chessboard(0, 0, 2, 1)
    rects = [board.elementAt(i) for i in range(0, board.elementCount(), 5)]  # 5 elements per closed rectangle
    w, h = 1 / columns, 1 / rows
    small = (w / 2, h) if w >= h else (w, h / 2)
    assert len(rects) == 2 * columns * rows  # half of the 2 * 2 * columns * rows halves
    assert board.boundingRect().width() * board.boundingRect().height() <= 2
    cell = board.toFillPolygons()[0].boundingRect()
    assert (cell.width(), cell.height()) == pytest.approx(small)
    corners = {(round(r.x / small[0]), round(r.y / small[1])) for r in rects}
    assert all((i + j) % 2 == 1 for i, j in corners)  # never two grey ones side by side


def test_the_cells_around_points() -> None:
    assert cells_around([Vec(0, 0), Vec(1, 0), Vec(1, 1)]) == (0, 0, 1, 1)  # a cube's face
    assert cells_around([Vec(44, 50), Vec(Fraction(97, 2), 53)]) == (44, 50, 49, 53)  # a template's, on its grid
    assert cells_around([Vec(Fraction(-1, 3), 2)]) == (-1, 2, 0, 2)
