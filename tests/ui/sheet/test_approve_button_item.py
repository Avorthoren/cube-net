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


def is_fill(colour: QColor) -> bool:
    """Part of the button's inside: from its light top to its shaded bottom (not the symbol, not the rim)."""
    low, high = palette.APPROVE_BUTTON_SHADE.lightness(), palette.APPROVE_BUTTON_FILL.lightness()
    return colour.saturation() < 20 and low - 5 <= colour.lightness() <= high


def on_diagonals(image: QImage, center: QPointF) -> list[QColor]:
    """The pixels a quarter of the radius away from the centre, along both diagonals."""
    d = int(net_style.APPROVE_BUTTON_RADIUS_PX / 4)
    x, y = int(center.x()), int(center.y())
    return [image.pixelColor(x + dx, y + dy) for dx in (d, -d - 1) for dy in (d, -d - 1)]


def test_x_when_disabled() -> None:
    item = ApproveButtonItem()
    item.set_state(Vec(2, 2), False)
    image, center = render(item)
    assert not any(is_fill(c) for c in on_diagonals(image, center))  # both strokes of the "x" go through them


def test_check_mark_when_enabled() -> None:
    item = ApproveButtonItem()
    item.set_state(Vec(2, 2), True)
    image, center = render(item)
    assert any(is_fill(c) for c in on_diagonals(image, center))  # a check mark misses some of them


class TestLooksLikeAButton:
    def render_enabled(self) -> tuple[QImage, QPointF]:
        item = ApproveButtonItem()
        item.set_state(Vec(2, 2), True)
        return render(item)

    def test_lit_from_above(self) -> None:
        image, center = self.render_enabled()
        r = int(net_style.APPROVE_BUTTON_RADIUS_PX)
        x = int(center.x()) - r // 2  # left of the check mark
        top, bottom = image.pixelColor(x, int(center.y()) - r // 2), image.pixelColor(x, int(center.y()) + r // 2)
        assert is_fill(top) and is_fill(bottom)
        assert top.lightness() > bottom.lightness()

    def test_casts_a_shadow_below(self) -> None:
        """On white, so that the shadow shows: darker below the button than above it."""
        item = ApproveButtonItem()
        item.set_state(Vec(2, 2), True)
        image = QImage(200, 200, QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        world = QTransform().scale(SCALE, -SCALE).translate(0, -4)
        painter = QPainter(image)
        painter.setTransform(world)
        item.paint(painter, None)
        painter.end()
        center = world.map(QPointF(2, 2))
        reach = net_style.APPROVE_BUTTON_RADIUS_PX + net_style.APPROVE_CHECK_WIDTH_PX / 2 + 1
        below = image.pixelColor(int(center.x()), int(center.y() + reach))
        above = image.pixelColor(int(center.x()), int(center.y() - reach - 1))
        assert above == QColor("white")
        assert below.lightness() < above.lightness()


class TestPressed:
    def test_pushed_in_and_darker(self) -> None:
        item = ApproveButtonItem()
        item.set_state(Vec(2, 2), True)
        raised, center = render(item)
        item.set_pressed(True)
        assert item.pressed()
        pressed, _ = render(item)
        assert raised != pressed
        r = int(net_style.APPROVE_BUTTON_RADIUS_PX)
        x = int(center.x()) - r // 2
        top = pressed.pixelColor(x, int(center.y()) - r // 2 + 1)
        bottom = pressed.pixelColor(x, int(center.y()) + r // 2 + 1)
        raised_top = raised.pixelColor(x, int(center.y()) - r // 2)
        assert top.saturation() < 20 and bottom.saturation() < 20  # its grey inside, not the symbol
        assert top.lightness() < bottom.lightness()  # the other way round than raised: in its own shadow
        assert top.lightness() < raised_top.lightness()  # darker than raised

    def test_no_shadow_while_pressed(self) -> None:
        item = ApproveButtonItem()
        item.set_state(Vec(2, 2), True)
        item.set_pressed(True)
        image = QImage(200, 200, QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        world = QTransform().scale(SCALE, -SCALE).translate(0, -4)
        painter = QPainter(image)
        painter.setTransform(world)
        item.paint(painter, None)
        painter.end()
        center = world.map(QPointF(2, 2))
        shadow = net_style.APPROVE_BUTTON_SHADOW_PX
        reach = net_style.APPROVE_BUTTON_RADIUS_PX + net_style.APPROVE_CHECK_WIDTH_PX / 2 + shadow / 2 + 2
        assert image.pixelColor(int(center.x()), int(center.y() + reach)) == QColor("white")

    def test_the_same_size(self) -> None:
        item = ApproveButtonItem()
        item.set_state(Vec(2, 2), True)
        item.set_pressed(True)
        image, center = render(item)
        just_outside = center + QPointF(net_style.APPROVE_BUTTON_RADIUS_PX + net_style.APPROVE_CHECK_WIDTH_PX + 1, 0)
        assert image.pixelColor(just_outside.toPoint()) == QColor("black")
