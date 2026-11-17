# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtGui import QColor, QImage, QPainter, QTransform
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Vec
from cube_net.core.template import Template
from cube_net.ui.template.template_item import TemplateItem

SQUARE = [Vec(10, 10), Vec(12, 10), Vec(12, 12), Vec(10, 12)]


def coloured_square() -> Template:
    template = Template()
    for p in SQUARE:
        template = template.with_vertex_appended(p)
    return template.closed_loop().with_face_color(0, "#0000FF")


def render(item: TemplateItem) -> QImage:
    """The item at 100 pixels per unit, the square's corner (10, 10) at the image's bottom-left."""
    image = QImage(300, 300, QImage.Format.Format_ARGB32)
    image.fill(QColor("#808080"))
    painter = QPainter(image)
    world = QTransform(100, 0, 0, -100, -950, 1250)  # y up
    painter.setWorldTransform(world)
    item.paint(painter, None)
    painter.end()
    return image


def test_a_face_shows_its_colour_and_white(qtbot: QtBot) -> None:
    image = render(TemplateItem(coloured_square()))
    seen = set()
    for x in range(110, 190, 3):
        for y in range(110, 190, 3):
            seen.add(image.pixelColor(x, y).name())
    assert {"#0000ff", "#ffffff"} <= seen


def test_outside_the_loop_nothing(qtbot: QtBot) -> None:
    image = render(TemplateItem(coloured_square()))
    assert image.pixelColor(5, 5).name() == "#808080"


def test_a_dragged_vertex_is_shown_where_it_is() -> None:
    item = TemplateItem(coloured_square())
    item.set_moved((2, Vec(13, 13)))
    assert item.template().position(2) == Vec(13, 13)
    item.set_template(coloured_square())
    assert item.template().position(2) == Vec(12, 12)
