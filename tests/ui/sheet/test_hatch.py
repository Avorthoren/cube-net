# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction

import pytest
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QImage

from cube_net.core.geometry import Vec
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.hatch import cells_around, tiled_chessboard, tiled_hatch


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
        net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX, columns, rows, net_style.DASHES_PER_UNIT, 1.0
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


@pytest.mark.parametrize("columns", [0.5, 2.5])
def test_any_positive_tiling_lines_up_on_the_grid(columns: float) -> None:
    """Below 1 a rectangle spans several units; the tiling always starts at the sheet's origin."""
    net_style.set_sizes(
        net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX, columns, 1.0, net_style.DASHES_PER_UNIT, 1.0
    )
    path = tiled_hatch(3, 0, 4, 1)
    w = 1 / columns
    lefts = {round(path.elementAt(i).x / w, 9) for i in range(0, path.elementCount(), 4)}
    assert all(x == int(x) for x in lefts)  # every triangle starts at a multiple of its width
    assert path.boundingRect().left() <= 3 and path.boundingRect().right() >= 4  # it covers the unit cell


def test_the_cells_around_points() -> None:
    assert cells_around([Vec(0, 0), Vec(1, 0), Vec(1, 1)]) == (0, 0, 1, 1)  # a cube's face
    assert cells_around([Vec(44, 50), Vec(Fraction(97, 2), 53)]) == (44, 50, 49, 53)  # a template's, on its grid
    assert cells_around([Vec(Fraction(-1, 3), 2)]) == (-1, 2, 0, 2)


class TestBrushes:
    """A face is painted with a brush repeating one rectangle of the pattern: it must look like the paths."""

    def render(self, kind: str, brush: bool) -> QImage:
        from PyQt6.QtGui import QColor, QPainter, QPainterPath, QTransform

        from cube_net.ui.sheet import hatch

        image = QImage(400, 300, QImage.Format.Format_ARGB32)
        image.fill(QColor("#FFFFFF"))
        painter = QPainter(image)
        painter.setWorldTransform(QTransform(100, 0, 0, -100, -950, 1250))  # 100 px per unit, y up
        colour = QColor("#0000FF")
        if brush:
            make = hatch.hatch_brush if kind == "hatch" else hatch.chessboard_brush
            found = make(colour, painter.worldTransform())
            assert found is not None
            area = QPainterPath()
            area.addRect(QRectF(10, 10, 3, 2))
            painter.fillPath(area, found)
        else:
            painter.fillPath((tiled_hatch if kind == "hatch" else tiled_chessboard)(10, 10, 13, 12), colour)
        painter.end()
        return image

    @pytest.mark.parametrize("kind", ["hatch", "chessboard"])
    def test_it_looks_like_the_paths(self, kind: str) -> None:
        net_style.set_sizes(net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX, 3.0, 2.0, 1.0, 1.0)
        a, b = self.render(kind, brush=True), self.render(kind, brush=False)
        points = [(x, y) for x in range(60, 340, 7) for y in range(60, 240, 7)]
        different = [
            p
            for p in points
            if max(abs(c1 - c2) for c1, c2 in zip(a.pixelColor(*p).getRgb(), b.pixelColor(*p).getRgb(), strict=True))
            > 60
        ]
        assert len(different) < len(points) * 0.03  # only along the edges, where smoothing differs

    def test_none_for_rectangles_too_large(self) -> None:
        from PyQt6.QtGui import QColor, QTransform

        from cube_net.ui.sheet.hatch import MAX_TILE_PX, hatch_brush

        net_style.set_sizes(net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX, 1.0, 1.0, 1.0, 1.0)
        assert hatch_brush(QColor("#0000FF"), QTransform.fromScale(MAX_TILE_PX, MAX_TILE_PX)) is not None
        assert hatch_brush(QColor("#0000FF"), QTransform.fromScale(MAX_TILE_PX + 10, MAX_TILE_PX + 10)) is None

    def test_made_once_for_a_zoom(self) -> None:
        from PyQt6.QtGui import QColor, QTransform

        from cube_net.ui.sheet.hatch import hatch_brush

        first = hatch_brush(QColor("#0000FF"), QTransform.fromScale(40, 40))
        assert first is hatch_brush(QColor("#0000FF"), QTransform.fromScale(40, 40))
        assert first is not hatch_brush(QColor("#0000FF"), QTransform.fromScale(80, 80))
