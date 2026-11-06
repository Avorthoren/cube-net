import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter, QTransform

from cube_net.core.net import default_net
from cube_net.ui import palette
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.net_item import NetItem, hatch_path

SCALE = 100.0  # px per unit
ORIGIN = QPointF(9, 15)  # sheet point drawn at the image's top-left corner


def render() -> tuple[QImage, QTransform]:
    image = QImage(500, 600, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    world = QTransform().scale(SCALE, -SCALE).translate(-ORIGIN.x(), -ORIGIN.y())
    painter = QPainter(image)
    painter.setTransform(world)
    NetItem(default_net()).paint(painter, None)
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
    colour = colour_at(image, world, 11 - 2 / SCALE, 14 - 2 / SCALE)  # A_1 at (11, 14): a pixel inside its circle
    assert colour in [palette.FACE_COLORS[f] for f in (1, 4, 5)]  # A is a vertex of faces 1, 4 and 5
