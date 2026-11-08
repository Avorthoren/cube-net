from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QImage, QPainter, QTransform

from cube_net.core.geometry import Vec
from cube_net.ui import palette
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.approve_button_item import ApproveButtonItem

SCALE = 50.0


def render(item: ApproveButtonItem) -> tuple[QImage, QPointF]:
    image = QImage(200, 200, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    world = QTransform().scale(SCALE, -SCALE).translate(0, -4)
    painter = QPainter(image)
    painter.setTransform(world)
    item.paint(painter, None)
    painter.end()
    return image, world.map(QPointF(2, 2))


def colours(image: QImage, center: QPointF) -> list[QColor]:
    r = int(net_style.APPROVE_BUTTON_RADIUS_PX) + 2
    return [
        image.pixelColor(int(center.x()) + dx, int(center.y()) + dy)
        for dx in range(-r, r + 1)
        for dy in range(-r, r + 1)
    ]


def test_nothing_without_a_position() -> None:
    item = ApproveButtonItem()
    item.set_area(QRectF(0, 0, 4, 4))
    image, center = render(item)
    assert image.pixelColor(center.toPoint()) == QColor("black")


def test_green_when_enabled_grey_when_not() -> None:
    item = ApproveButtonItem()
    item.set_state(Vec(2, 2), True)
    image, center = render(item)
    assert palette.SUCCESS in colours(image, center)
    assert palette.APPROVE_BUTTON_FILL in colours(image, center)
    item.set_state(Vec(2, 2), False)
    image, center = render(item)
    assert palette.SUCCESS not in colours(image, center)
    assert palette.APPROVE_BUTTON_DISABLED in colours(image, center)


def test_constant_size_in_pixels() -> None:
    item = ApproveButtonItem()
    item.set_state(Vec(2, 2), True)
    image, center = render(item)
    just_outside = center + QPointF(net_style.APPROVE_BUTTON_RADIUS_PX + net_style.APPROVE_CHECK_WIDTH_PX + 1, 0)
    assert image.pixelColor(just_outside.toPoint()) == QColor("black")


def on_diagonals(image: QImage, center: QPointF) -> list[QColor]:
    """The pixels a quarter of the radius away from the centre, along both diagonals."""
    d = int(net_style.APPROVE_BUTTON_RADIUS_PX / 4)
    x, y = int(center.x()), int(center.y())
    return [image.pixelColor(x + dx, y + dy) for dx in (d, -d - 1) for dy in (d, -d - 1)]


def test_x_when_disabled() -> None:
    item = ApproveButtonItem()
    item.set_state(Vec(2, 2), False)
    image, center = render(item)
    assert palette.APPROVE_BUTTON_FILL not in on_diagonals(image, center)  # both strokes of the "x" go through them


def test_check_mark_when_enabled() -> None:
    item = ApproveButtonItem()
    item.set_state(Vec(2, 2), True)
    image, center = render(item)
    assert palette.APPROVE_BUTTON_FILL in on_diagonals(image, center)  # a check mark misses some of them
