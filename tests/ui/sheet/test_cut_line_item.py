from fractions import Fraction as F

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QImage, QPainter, QTransform

from cube_net.core.cutting import CutPoint
from cube_net.core.geometry import Vec
from cube_net.core.net import default_net
from cube_net.ui import palette
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.cut_line_item import CutLineItem

SCALE = 100.0


def render(item: CutLineItem) -> tuple[QImage, QTransform]:
    image = QImage(400, 500, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    world = QTransform().scale(SCALE, -SCALE).translate(-9, -15)
    painter = QPainter(image)
    painter.setTransform(world)
    item.paint(painter, None)
    painter.end()
    return image, world


def item_with_line() -> CutLineItem:
    item = CutLineItem(default_net())
    item.set_area(QRectF(5, 5, 13, 14))
    item.set_points([CutPoint(Vec(F(23, 2), 14)), CutPoint(Vec(F(23, 2), F(25, 2)))])  # down through faces 1 and 2
    return item


def test_nothing_drawn_without_points() -> None:
    item = CutLineItem(default_net())
    image, world = render(item)
    assert image.pixelColor(world.map(QPointF(11.5, 13.5)).toPoint()) == QColor("white")


def test_segment_has_face_colours_and_halo() -> None:
    image, world = render(item_with_line())
    on_line = world.map(QPointF(11.5, 13.52)).toPoint()  # inside face 1
    assert image.pixelColor(on_line) in (palette.FACE_COLORS[1], palette.WHITE)
    beside = world.map(QPointF(11.5 + (net_style.EDGE_WIDTH_PX / 2 + 1) / SCALE, 13.52)).toPoint()  # in the halo
    colour = image.pixelColor(beside)
    assert colour.red() > 200 and colour.green() > 150 and colour.blue() < 150  # yellowish halo over white


def test_flash_is_black_on_top() -> None:
    item = item_with_line()
    item.set_flash((Vec(F(23, 2), F(27, 2)), Vec(12, F(27, 2))))
    image, world = render(item)
    assert image.pixelColor(world.map(QPointF(11.75, 13.5)).toPoint()) == palette.REJECTED
    item.set_flash(None)
    assert item.flash() is None


def test_rubber_band_state() -> None:
    item = item_with_line()
    segment = (Vec(F(23, 2), F(25, 2)), Vec(12, 12))
    item.set_rubber_band(segment)
    assert item.rubber_band() == segment
