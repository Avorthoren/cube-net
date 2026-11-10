# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QImage, QPainter

from cube_net.ui import palette
from cube_net.ui.sheet.sheet_item import SheetItem


def render(item: SheetItem, scale: float) -> QImage:
    r = item.boundingRect()
    image = QImage(int(r.width() * scale) + 1, int(r.height() * scale) + 1, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    painter = QPainter(image)
    painter.scale(scale, scale)
    painter.translate(-r.left(), -r.top())
    item.paint(painter, None)
    painter.end()
    return image


def test_bounding_rect_is_sheet_rect() -> None:
    item = SheetItem(QRectF(5, 5, 13, 14))
    assert item.boundingRect() == QRectF(5, 5, 13, 14)
    item.set_rect(QRectF(0, 0, 2, 3))
    assert item.rect() == QRectF(0, 0, 2, 3)


def test_white_sheet_with_grid_on_integer_lines() -> None:
    item = SheetItem(QRectF(5, 5, 13, 14))
    image = render(item, 20)  # 20 px per unit; sheet x=5 is pixel 0
    assert image.pixelColor(30, 30) == palette.SHEET  # (6.5, 6.5): middle of a grid cell
    assert image.pixelColor(40, 30) == palette.GRID  # x = 7: a grid line


def test_empty_sheet_paints_nothing() -> None:
    SheetItem().paint(None, None)


def test_grid_width_and_colour_follow_the_style() -> None:
    from dataclasses import replace

    from cube_net.ui.style import DEFAULT_STYLE, apply_style

    item = SheetItem(QRectF(5, 5, 13, 14))
    apply_style(replace(DEFAULT_STYLE, grid_color="#FF0000", grid_width=3.0))
    image = render(item, 20)
    assert image.pixelColor(40, 30) == QColor("#FF0000")
    assert image.pixelColor(41, 30) == QColor("#FF0000")  # 3 px wide
    apply_style(replace(DEFAULT_STYLE, grid_width=0.0))
    image = render(item, 20)
    assert image.pixelColor(40, 30) == palette.SHEET  # no grid
