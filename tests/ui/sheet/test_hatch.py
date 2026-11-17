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


def test_the_cells_around_points() -> None:
    assert cells_around([Vec(0, 0), Vec(1, 0), Vec(1, 1)]) == (0, 0, 1, 1)  # a cube's face
    assert cells_around([Vec(44, 50), Vec(Fraction(97, 2), 53)]) == (44, 50, 49, 53)  # a template's, on its grid
    assert cells_around([Vec(Fraction(-1, 3), 2)]) == (-1, 2, 0, 2)
