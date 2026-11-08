import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter, QTransform
from PyQt6.QtWidgets import QApplication

from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import default_net
from cube_net.ui import palette
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.net_item import NetItem, hatch_path

SCALE = 100.0  # px per unit
ORIGIN = QPointF(9, 15)  # sheet point drawn at the image's top-left corner


def render(
    with_labels: bool = False, background: str = "black", highlight_left_of_face_4: bool = False
) -> tuple[QImage, QTransform]:
    image = QImage(500, 600, QImage.Format.Format_RGB32)
    image.fill(QColor(background))
    world = QTransform().scale(SCALE, -SCALE).translate(-ORIGIN.x(), -ORIGIN.y())
    painter = QPainter(image)
    painter.setTransform(world)
    net = default_net()
    item = NetItem(net)
    if with_labels:
        item.set_labels(vertex_labels(net, PointLabels()))
    if highlight_left_of_face_4:
        cut = next(he for he in net.boundary_edges() if he.origin.position.x == he.destination.position.x == 10)
        item.set_highlight(cut)
    item.paint(painter, None)
    painter.end()
    return image, world


def colour_at(image: QImage, world: QTransform, x: float, y: float) -> QColor:
    p = world.map(QPointF(x, y))
    return image.pixelColor(int(p.x()), int(p.y()))


def test_hatch_covers_half_of_the_face() -> None:
    path = hatch_path()
    area = 0.0
    for i in range(path.elementCount() // 4):  # 4 elements per closed triangle
        a, b, c = (path.elementAt(4 * i + j) for j in range(3))
        area += abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) / 2
    assert area == pytest.approx(0.5)


def test_hatch_upper_triangle_coloured_lower_white() -> None:
    image, world = render()
    # Face 2 is [11, 12] x [12, 13]. Cell (11.5..11.6, 12.4..12.6): upper-left part coloured, lower-right white.
    assert colour_at(image, world, 11.52, 12.58) == palette.FACE_COLORS[2]
    assert colour_at(image, world, 11.58, 12.42) == palette.WHITE


@pytest.mark.parametrize(("face", "x", "y"), [(1, 11.52, 13.58), (4, 10.52, 12.58), (5, 11.52, 10.58)])
def test_every_face_has_its_colour(face: int, x: float, y: float) -> None:
    image, world = render()
    assert colour_at(image, world, x, y) == palette.FACE_COLORS[face]


def test_cut_drawn_inside_its_face() -> None:
    """Cut A_2 - E_2 (x = 10, faces 4 and 5) is drawn just to the right of x = 10, not to the left."""
    image, world = render()
    inside_px = net_style.EDGE_WIDTH_PX / 2 / SCALE
    inside = colour_at(image, world, 10 + inside_px, 12.525)  # second dash from E (pattern parity 1 -> face 5)
    assert inside in (palette.FACE_COLORS[4], palette.FACE_COLORS[5])
    assert colour_at(image, world, 10 - 3 / SCALE, 12.525) == QColor("black")  # outside: nothing drawn


def test_vertex_circle_drawn_on_perimeter_vertex() -> None:
    image, world = render()
    inside = net_style.VERTEX_RADIUS_PX / 2 / SCALE  # half the radius down-left of A_1 = (11, 14)
    colour = colour_at(image, world, 11 - inside, 14 - inside)
    assert colour in [palette.FACE_COLORS[f] for f in (1, 4, 5)]  # A is a vertex of faces 1, 4 and 5


def test_labels_drawn_outside_the_net(qapp: QApplication) -> None:
    """The label of A_1 (top-left corner of face 1) is drawn up-left of it, on the empty sheet; the faces stay as
    they were. (Fonts need a running QApplication, hence `qapp`.)"""
    plain, world = render(background="white")
    labelled, _ = render(with_labels=True, background="white")  # labels are black
    a1 = world.map(QPointF(11, 14))
    reach = round(net_style.VERTEX_RADIUS_PX + net_style.LABEL_GAP_PX + 4 * net_style.LABEL_FONT_PX)
    changed = sum(
        plain.pixelColor(x, y) != labelled.pixelColor(x, y)
        for x in range(int(a1.x()) - reach, int(a1.x()))
        for y in range(int(a1.y()) - reach, int(a1.y()))
    )
    assert changed > 10
    inside = world.map(QPointF(11.5, 13.5)).toPoint()
    assert plain.pixelColor(inside) == labelled.pixelColor(inside)


def test_highlighted_cut_drawn_with_highlight_width_inside() -> None:
    """A_2 - E_2 at x = 10: highlighted, it covers HIGHLIGHT_WIDTH_PX to the right of x = 10 (inside face 4)."""
    lit, world = render(highlight_left_of_face_4=True)
    y = 12.525
    near_inner_edge = 10 + max(net_style.HIGHLIGHT_WIDTH_PX - 1.5, 0.5) / SCALE
    assert colour_at(lit, world, near_inner_edge, y) in (palette.FACE_COLORS[4], palette.FACE_COLORS[5])
    assert colour_at(lit, world, 10 - 3 / SCALE, y) == QColor("black")  # nothing outside the net


def test_single_face_circle_has_no_radius_line() -> None:
    """A circle with one colour is drawn as a plain disc: no outline line from its center (a 360-degree pie had one)."""
    from cube_net.ui.sheet.net_painting import paint_vertex

    image = QImage(60, 60, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    paint_vertex(painter, QPointF(30, 30), {2}, 20)
    painter.end()
    for y in range(14, 29):  # straight up from the center: all face colour, no outline pixels
        assert image.pixelColor(30, y) == palette.FACE_COLORS[2], y


def test_highlighted_fold_is_centered_on_the_line() -> None:
    """Fold C_1-H_1 at x = 11, between faces 4 and 2: highlighted, it covers both sides, unlike a cut."""
    net = default_net()
    item = NetItem(net)
    fold = next(
        he for he in net.fold_edges() if {he.origin.position, he.destination.position} == {Vec(11, 13), Vec(11, 12)}
    )
    item.set_highlight_fold(fold)
    assert item.highlight_fold() is fold
    image = QImage(500, 600, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    world = QTransform().scale(SCALE, -SCALE).translate(-ORIGIN.x(), -ORIGIN.y())
    painter = QPainter(image)
    painter.setTransform(world)
    item.paint(painter, None)
    painter.end()
    off_center = max(net_style.HIGHLIGHT_WIDTH_PX / 2 - 1.5, 0.5) / SCALE
    expected = (palette.FACE_COLORS[2], palette.FACE_COLORS[4])
    for side in (-off_center, off_center):
        assert colour_at(image, world, 11 + side, 12.525) in expected


def test_glue_pair_is_shown_highlighted() -> None:
    net = default_net()
    item = NetItem(net)
    cut = next(he for he in net.boundary_edges() if he.origin.position.x == he.destination.position.x == 10)
    item.set_glue((cut,))
    assert item.glue() == (cut,)
    image = QImage(500, 600, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    world = QTransform().scale(SCALE, -SCALE).translate(-ORIGIN.x(), -ORIGIN.y())
    painter = QPainter(image)
    painter.setTransform(world)
    item.paint(painter, None)
    painter.end()
    near_inner_edge = 10 + max(net_style.HIGHLIGHT_WIDTH_PX - 1.5, 0.5) / SCALE
    assert colour_at(image, world, near_inner_edge, 12.525) in (palette.FACE_COLORS[4], palette.FACE_COLORS[5])
    item.set_net(net)
    assert item.glue() == ()
