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
    image = QImage(400, 700, QImage.Format.Format_RGB32)
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
    item.set_flash(((Vec(F(23, 2), F(27, 2)), Vec(12, F(27, 2))),))
    image, world = render(item)
    assert image.pixelColor(world.map(QPointF(11.75, 13.5)).toPoint()) == palette.REJECTED
    item.set_flash(None)
    assert item.flash() is None


def test_rubber_band_state() -> None:
    item = item_with_line()
    segment = (Vec(F(23, 2), F(25, 2)), Vec(12, 12))
    item.set_rubber_band(segment)
    assert item.rubber_band() == segment


def test_images_of_endpoints() -> None:
    net = default_net()
    top = next(
        he for he in net.boundary_edges() if {he.origin.position, he.destination.position} == {Vec(11, 14), Vec(12, 14)}
    )
    item = CutLineItem(net)
    item.set_points([CutPoint(Vec(F(23, 2), 14), top), CutPoint(Vec(F(23, 2), F(27, 2)))])
    assert item.images() == [Vec(F(23, 2), 10)]  # x_2 at the bottom of face 5


def test_crossings_of_placed_segments() -> None:
    item = CutLineItem(default_net())
    item.set_points([CutPoint(Vec(11, 13)), CutPoint(Vec(F(23, 2), F(23, 2)))])
    assert item.crossings() == [Vec(F(34, 3), 12)]
    item.set_rubber_band((Vec(F(23, 2), F(23, 2)), Vec(F(23, 2), F(21, 2))))  # the line to the mouse doesn't count
    assert item.crossings() == [Vec(F(34, 3), 12)]


def test_crossings_are_small_grey_dots_while_drawing() -> None:
    item = CutLineItem(default_net())
    item.set_area(QRectF(5, 5, 13, 14))
    item.set_points([CutPoint(Vec(11, 13)), CutPoint(Vec(F(23, 2), F(23, 2)))])
    image, world = render(item)
    center = world.map(QPointF(34 / 3, 12))
    assert image.pixelColor(center.toPoint()) == palette.DERIVED_POINT
    # Farther from the center than the small radius, but within a normal vertex radius: no grey any more.
    r = net_style.VERTEX_RADIUS_PX * net_style.DERIVED_POINT_RADIUS_FACTOR
    beside = (center + QPointF(0, -(r + 2))).toPoint()  # straight up, off the line (which goes down-left to up-right)
    assert image.pixelColor(beside) != palette.DERIVED_POINT


def test_counterpart_images_are_small_black_dots_while_drawing() -> None:
    net = default_net()
    top = next(
        he for he in net.boundary_edges() if {he.origin.position, he.destination.position} == {Vec(11, 14), Vec(12, 14)}
    )
    item = CutLineItem(net)
    item.set_area(QRectF(5, 5, 13, 14))
    item.set_points([CutPoint(Vec(F(23, 2), 14), top), CutPoint(Vec(F(23, 2), F(27, 2)))])
    image, world = render(item)
    center = world.map(QPointF(11.5, 10))  # x_2, the image of the start, at the bottom of face 5
    assert image.pixelColor(center.toPoint()) == palette.COUNTERPART_IMAGE
    r = net_style.VERTEX_RADIUS_PX * net_style.DERIVED_POINT_RADIUS_FACTOR
    assert image.pixelColor((center + QPointF(r + 2, -2)).toPoint()) != palette.COUNTERPART_IMAGE  # small dot only


def test_midpoints_only_when_switched_on() -> None:
    item = item_with_line()
    assert item.midpoints() == []
    item.set_show_midpoints(True)
    assert item.midpoints() == [Vec(F(23, 2), F(53, 4))]


def test_midpoint_circles_are_hollow() -> None:
    """Only a thin outline: what's under the circle stays visible, and just outside the line nothing else changes."""
    plain = item_with_line()
    circled = item_with_line()
    circled.set_show_midpoints(True)
    without, world = render(plain)
    with_circle, _ = render(circled)
    center = world.map(QPointF(11.5, 13.25))
    assert with_circle.pixelColor(center.toPoint()) == without.pixelColor(center.toPoint())
    r = net_style.VERTEX_RADIUS_PX * net_style.MIDPOINT_RADIUS_FACTOR
    across_the_outline = [(center + QPointF(dx, 0)).toPoint() for dx in range(1, round(r) + 3)]
    assert any(with_circle.pixelColor(q) != without.pixelColor(q) for q in across_the_outline)


def test_a_line_off_the_net_while_dragging_is_painted_without_colours() -> None:
    item = CutLineItem(default_net())
    item.set_area(QRectF(5, 5, 13, 14))
    item.set_points([CutPoint(Vec(F(23, 2), F(27, 2))), CutPoint(Vec(9, 14)), CutPoint(Vec(9, 14))])
    image, world = render(item)  # must not raise, even with a zero-length segment
    assert image.pixelColor(world.map(QPointF(9, 14)).toPoint()) == palette.DERIVED_POINT
    assert item.crossings() == []


def test_a_pressed_midpoint_is_all_black_and_the_same_size() -> None:
    item = item_with_line()
    item.set_show_midpoints(True)
    plain, world = render(item)
    item.set_pressed_midpoint(0)
    assert item.pressed_midpoint() == 0
    pressed, _ = render(item)
    centre = world.map(QPointF(11.5, 13.25)).toPoint()  # the middle of the line
    assert plain.pixelColor(centre) != palette.PRESSED_MIDPOINT
    assert pressed.pixelColor(centre) == palette.PRESSED_MIDPOINT
    r = net_style.VERTEX_RADIUS_PX * net_style.MIDPOINT_RADIUS_FACTOR
    for dx in (r - 2, -(r - 2)):  # inside its (smoothed) edge it is black...
        assert pressed.pixelColor(centre + QPointF(dx, 0).toPoint()) == palette.PRESSED_MIDPOINT
    outside = centre + QPointF(r + 3, 0).toPoint()  # ...and not beyond: the same size
    assert plain.pixelColor(outside) == pressed.pixelColor(outside)
