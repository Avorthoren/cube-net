# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.coordinates_hint import CoordinatesHint, hint_font, hint_place

AREA = QSize(800, 600)
SIZE = QSize(200, 40)


def test_above_and_to_the_right_of_the_mouse() -> None:
    offset, right = net_style.COORDINATES_OFFSET_PX, net_style.COORDINATES_RIGHT_OFFSET_PX
    assert hint_place(QPoint(300, 300), SIZE, AREA) == QPoint(300 + right, 300 - offset - SIZE.height())


def test_to_the_left_where_it_doesnt_fit_on_the_right() -> None:
    offset = net_style.COORDINATES_OFFSET_PX
    assert hint_place(QPoint(700, 300), SIZE, AREA) == QPoint(700 - offset - SIZE.width(), 300 - offset - SIZE.height())


def test_below_where_it_doesnt_fit_above() -> None:
    offset, right = net_style.COORDINATES_OFFSET_PX, net_style.COORDINATES_RIGHT_OFFSET_PX
    assert hint_place(QPoint(300, 20), SIZE, AREA) == QPoint(300 + right, 20 + offset)


def test_the_pencil_pointer_doesnt_cover_it(qtbot: QtBot) -> None:
    """Over a point of the cut line the pointer is a pencil, going up and to the right from its tip (the mouse): none
    of its pixels is over the hint."""
    from PyQt6.QtCore import QRect

    from cube_net.ui.sheet.cursors import CursorKind, cursor_for

    cursor = cursor_for(CursorKind.PENCIL)
    image = cursor.pixmap().toImage()
    ratio = cursor.pixmap().devicePixelRatio()
    hot = cursor.hotSpot()
    mouse = QPoint(300, 300)
    box = QRect(hint_place(mouse, SIZE, AREA), SIZE)
    covered = [
        (x, y)
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 0
        and box.contains(mouse + QPoint(round(x / ratio) - hot.x(), round(y / ratio) - hot.y()))
    ]
    assert covered == []


def test_in_the_corner_both() -> None:
    offset = net_style.COORDINATES_OFFSET_PX
    assert hint_place(QPoint(790, 5), SIZE, AREA) == QPoint(790 - offset - SIZE.width(), 5 + offset)


@pytest.fixture
def viewport(qtbot: QtBot) -> QWidget:
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.resize(AREA)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_shows_the_lines_in_a_box_that_fits_them(viewport: QWidget) -> None:
    hint = CoordinatesHint(viewport)
    assert not hint.isVisible() and hint.lines() == []
    lines = ["y: 38767/3000 ≈ 12.922", "x:    11"]
    hint.show_at(lines, QPoint(300, 300))
    assert hint.isVisible() and hint.lines() == lines
    metrics = QFontMetrics(hint_font())
    padding = net_style.COORDINATES_PADDING_PX
    assert hint.width() == metrics.horizontalAdvance(lines[0]) + 2 * padding
    assert hint.height() == 2 * metrics.lineSpacing() + 2 * padding
    assert hint.pos() == hint_place(QPoint(300, 300), hint.size(), AREA)
    hint.hide()
    assert hint.lines() == []


def test_monospace_and_never_in_the_mouses_way(viewport: QWidget) -> None:
    hint = CoordinatesHint(viewport)
    assert hint_font().fixedPitch() or QFontMetrics(hint_font()).horizontalAdvance("i") == QFontMetrics(
        hint_font()
    ).horizontalAdvance("W")
    assert hint.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert hint_font().pixelSize() == net_style.COORDINATES_FONT_PX
