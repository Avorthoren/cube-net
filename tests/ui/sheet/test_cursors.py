import pytest
from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from cube_net.ui.sheet.cursors import CURSOR_PX, CursorKind, cursor_for

DRAWN = [CursorKind.SCISSORS, CursorKind.PENCIL, CursorKind.GLUE, CursorKind.PLUS, CursorKind.DELETE]


@pytest.mark.parametrize("kind", DRAWN, ids=[k.value for k in DRAWN])
def test_drawn_cursors(qtbot: QtBot, kind: CursorKind) -> None:
    cursor = cursor_for(kind)
    assert cursor.shape() == Qt.CursorShape.BitmapCursor
    image = cursor.pixmap().toImage()
    assert image.width() >= CURSOR_PX
    spot = cursor.hotSpot()
    assert 0 <= spot.x() < CURSOR_PX and 0 <= spot.y() < CURSOR_PX
    painted = sum(image.pixelColor(x, y).alpha() > 0 for x in range(image.width()) for y in range(image.height()))
    assert painted > image.width() * image.height() // 10  # there's a picture, not an empty square


def test_they_differ(qtbot: QtBot) -> None:
    images = [cursor_for(kind).pixmap().toImage() for kind in DRAWN]
    assert all(a != b for i, a in enumerate(images) for b in images[i + 1 :])


def test_drawn_once(qtbot: QtBot) -> None:
    assert cursor_for(CursorKind.GLUE).pixmap().cacheKey() == cursor_for(CursorKind.GLUE).pixmap().cacheKey()


def test_standard_ones(qtbot: QtBot) -> None:
    assert cursor_for(CursorKind.ARROW).shape() == Qt.CursorShape.ArrowCursor
    assert cursor_for(CursorKind.BUTTON).shape() == Qt.CursorShape.PointingHandCursor


def test_the_plus_clicks_at_its_upper_left_inner_corner(qtbot: QtBot) -> None:
    """Where the bars meet: green below it and to its right, nothing up and left of it."""
    cursor = cursor_for(CursorKind.PLUS)
    image = cursor.pixmap().toImage()
    ratio = cursor.pixmap().devicePixelRatio()
    x, y = round(cursor.hotSpot().x() * ratio), round(cursor.hotSpot().y() * ratio)
    step = round(3 * ratio)  # past the outline
    assert image.pixelColor(x - step, y - step).alpha() == 0
    assert image.pixelColor(x + step, y + step).green() > 120
    assert image.pixelColor(x - step, y + step).green() > 120  # the left bar
    assert image.pixelColor(x + step, y - step).green() > 120  # the top bar


def test_the_x_is_the_plus_turned(qtbot: QtBot) -> None:
    def coverage(kind: CursorKind) -> float:  # edges drawn smooth count by how much they're covered
        image = cursor_for(kind).pixmap().toImage()
        return sum(image.pixelColor(x, y).alphaF() for x in range(image.width()) for y in range(image.height()))

    plus, x = coverage(CursorKind.PLUS), coverage(CursorKind.DELETE)
    assert abs(plus - x) <= plus * 0.05  # the same size


def test_the_x_clicks_at_its_middle(qtbot: QtBot) -> None:
    cursor = cursor_for(CursorKind.DELETE)
    image = cursor.pixmap().toImage()
    ratio = cursor.pixmap().devicePixelRatio()
    spot = cursor.hotSpot()
    assert image.pixelColor(round(spot.x() * ratio), round(spot.y() * ratio)).red() > 150  # the red middle
