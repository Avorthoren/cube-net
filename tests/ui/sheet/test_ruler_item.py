from fractions import Fraction as F

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QImage, QPainter, QTransform
from PyQt6.QtWidgets import QApplication

from cube_net.core.geometry import Vec
from cube_net.ui import palette
from cube_net.ui.sheet.ruler_item import RulerItem, _shift_into, format_distance, format_point

SCALE = 50.0


def render(item: RulerItem) -> tuple[QImage, QTransform]:
    image = QImage(500, 500, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    world = QTransform().scale(SCALE, -SCALE).translate(0, -10)  # sheet (0, 10) at the top-left corner
    painter = QPainter(image)
    painter.setTransform(world)
    item.paint(painter, None)
    painter.end()
    return image, world


def test_formats() -> None:
    assert format_point(Vec(F(23, 2), 12)) == "(11.500, 12.000)"
    assert format_distance(Vec(0, 0), Vec(3, 4)) == "5.000"


def test_nothing_drawn_without_points(qapp: QApplication) -> None:
    item = RulerItem()
    item.set_rect(QRectF(0, 0, 10, 10), 0.0)
    item.set_state((), Vec(1, 1))
    image, _ = render(item)
    assert image.pixelColor(50, 450) == QColor("white")


def test_line_from_point_to_cursor(qapp: QApplication) -> None:
    item = RulerItem()
    item.set_rect(QRectF(0, 0, 10, 10), 0.0)
    item.set_state([Vec(1, 1)], Vec(8, 1))
    image, world = render(item)
    on_line = world.map(QPointF(4, 1)).toPoint()  # far from any label
    assert image.pixelColor(on_line) == palette.RULER


def test_bounding_rect_includes_label_margin() -> None:
    """Labels near the sheet's edge stick out of it; the item must claim that room, or Qt won't repaint it there."""
    item = RulerItem()
    item.set_rect(QRectF(0, 0, 10, 10), 2.0)
    assert item.boundingRect() == QRectF(-2, -2, 14, 14)


def test_labels_are_kept_inside_the_view() -> None:
    area = QRectF(0, 0, 100, 50)
    assert _shift_into(QRectF(10, 10, 20, 10), area) == QPointF(0, 0)  # already inside
    assert _shift_into(QRectF(90, 10, 20, 10), area) == QPointF(-10, 0)  # sticks out on the right
    assert _shift_into(QRectF(-5, 45, 20, 10), area) == QPointF(5, -5)  # bottom-left corner
    assert _shift_into(QRectF(0, 0, 200, 10), area) == QPointF(0, 0)  # can't fit: leave it


def test_cursor_label_near_view_edge_is_drawn_inside(qapp: QApplication) -> None:
    item = RulerItem()
    item.set_rect(QRectF(0, 0, 10, 10), 0.0)
    item.set_state([Vec(1, 9)], Vec(F(99, 10), F(1, 10)))  # mouse at the image's bottom-right corner
    image, _ = render(item)
    text = QColor(palette.RULER_TEXT)
    bottom_right = [image.pixelColor(x, y) for x in range(380, 500) for y in range(450, 500)]
    assert text in bottom_right  # the label was moved into the image instead of being cut off
