from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QImage, QPainter, QTransform

from cube_net.core.geometry import Vec
from cube_net.ui import palette
from cube_net.ui.sheet.bounding_item import BoundingItem

SCALE = 50.0
CORNERS = (Vec(2, 2), Vec(8, 2), Vec(8, 6), Vec(2, 6))


def render(item: BoundingItem) -> tuple[QImage, QTransform]:
    image = QImage(500, 500, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    world = QTransform().scale(SCALE, -SCALE).translate(0, -10)
    painter = QPainter(image)
    painter.setTransform(world)
    item.paint(painter, None)
    painter.end()
    return image, world


def on_bottom_side(world: QTransform) -> QPointF:
    return world.map(QPointF(5, 2))


def darkest_near(image: QImage, p: QPointF) -> QColor:
    """The line is thin and antialiased: look at the pixels across it and take the most saturated / darkest one."""
    column = [image.pixelColor(int(p.x()), int(p.y()) + dy) for dy in (-1, 0, 1)]
    return min(column, key=lambda c: c.red() + c.green() + c.blue() - 2 * c.saturation())


def close(a: QColor, b: QColor, tolerance: int = 90) -> bool:
    return all(abs(x - y) <= tolerance for x, y in zip(a.getRgb()[:3], b.getRgb()[:3], strict=True))


def test_nothing_without_rectangle() -> None:
    item = BoundingItem()
    assert item.boundingRect() == QRectF()
    image, world = render(item)
    assert image.pixelColor(on_bottom_side(world).toPoint()) == QColor("white")


def test_thin_line_black_or_green() -> None:
    item = BoundingItem()
    item.set_rectangle(CORNERS, success=False)
    image, world = render(item)
    assert close(darkest_near(image, on_bottom_side(world)), palette.BOUNDING_RECTANGLE)
    assert image.pixelColor(world.map(QPointF(5, 4)).toPoint()) == QColor("white")  # not filled
    item.set_rectangle(CORNERS, success=True)
    image, world = render(item)
    assert close(darkest_near(image, on_bottom_side(world)), palette.SUCCESS)
    assert item.boundingRect().contains(QRectF(2, 2, 6, 4))
