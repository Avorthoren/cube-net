import pytest
from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from cube_net.ui.sheet.cursors import CURSOR_PX, CursorKind, cursor_for

DRAWN = [CursorKind.SCISSORS, CursorKind.PENCIL, CursorKind.GLUE]


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
    assert images[0] != images[1] != images[2] != images[0]


def test_drawn_once(qtbot: QtBot) -> None:
    assert cursor_for(CursorKind.GLUE).pixmap().cacheKey() == cursor_for(CursorKind.GLUE).pixmap().cacheKey()


def test_standard_ones(qtbot: QtBot) -> None:
    assert cursor_for(CursorKind.ARROW).shape() == Qt.CursorShape.ArrowCursor
    assert cursor_for(CursorKind.BUTTON).shape() == Qt.CursorShape.PointingHandCursor
