# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace

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


def test_a_face_without_a_colour_is_a_chessboard(qtbot: QtBot) -> None:
    from cube_net.ui import palette

    template = coloured_square()
    template = replace(template, faces=(replace(template.faces[0], color=None),))
    image = render(TemplateItem(template))
    seen = set()
    for x in range(110, 190, 3):
        for y in range(110, 190, 3):
            seen.add(image.pixelColor(x, y).name())
    assert {palette.UNCOLORED_FACE.name(), "#ffffff"} <= seen
    assert "#0000ff" not in seen


def test_fold_dashes_are_per_unit(qtbot: QtBot) -> None:
    """With 1 dash per unit, a fold is drawn for half a unit, then left out for half a unit, from its start."""
    import math

    from cube_net.ui import palette
    from cube_net.ui.sheet import net_style

    net_style.set_sizes(net_style.EDGE_WIDTH_PX, net_style.VERTEX_RADIUS_PX, 1.0, 1.0, 1.0, 1.0)
    template = coloured_square()
    template = template.with_fold(template.vertices[0].id, template.vertices[2].id)  # (10, 10) to (12, 12)

    image = render(TemplateItem(template))

    def on_the_fold(s: float) -> bool:  # at distance s along it, in units (the image has 100 px per unit)
        x = 10 + s / math.sqrt(2)
        colour = image.pixelColor(round((x - 9.5) * 100), round((12.5 - x) * 100))
        fold = palette.TEMPLATE_FOLD
        return (
            max(abs(colour.red() - fold.red()), abs(colour.green() - fold.green()), abs(colour.blue() - fold.blue()))
            < 48
        )

    assert on_the_fold(0.25) and on_the_fold(1.25)
    assert not on_the_fold(0.75) and not on_the_fold(1.75)


def test_outside_the_loop_nothing(qtbot: QtBot) -> None:
    image = render(TemplateItem(coloured_square()))
    assert image.pixelColor(5, 5).name() == "#808080"


def test_a_dragged_vertex_is_shown_where_it_is() -> None:
    item = TemplateItem(coloured_square())
    item.set_moved((2, Vec(13, 13)))
    assert item.template().position(2) == Vec(13, 13)
    item.set_template(coloured_square())
    assert item.template().position(2) == Vec(12, 12)
