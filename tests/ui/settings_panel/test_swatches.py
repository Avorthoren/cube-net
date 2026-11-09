from PyQt6.QtGui import QColor
from pytestqt.qtbot import QtBot

from cube_net.ui import palette
from cube_net.ui.settings_panel.swatches import SWATCH_PX, ColorSwatch, GridSwatch


def test_colour_swatch(qtbot: QtBot) -> None:
    swatch = ColorSwatch("#123456")
    qtbot.addWidget(swatch)
    assert (swatch.width(), swatch.height()) == (SWATCH_PX, SWATCH_PX) == (20, 20)
    assert swatch.grab().toImage().pixelColor(2, 2) == QColor("#123456")


def test_grid_swatch_is_white_crossed_in_the_middle(qtbot: QtBot) -> None:
    swatch = GridSwatch("#000000", 2.0)
    qtbot.addWidget(swatch)
    image = swatch.grab().toImage()
    assert image.pixelColor(1, 1) == palette.SHEET
    assert image.pixelColor(SWATCH_PX // 2, 1) != palette.SHEET
    assert image.pixelColor(1, SWATCH_PX // 2) != palette.SHEET


def test_no_lines_at_zero(qtbot: QtBot) -> None:
    swatch = GridSwatch("#000000", 0.0)
    qtbot.addWidget(swatch)
    image = swatch.grab().toImage()
    inside = range(1, SWATCH_PX - 1)  # the outline is around it
    assert all(image.pixelColor(x, y) == palette.SHEET for x in inside for y in inside)


def test_grid_swatch_has_a_black_outline(qtbot: QtBot) -> None:
    swatch = GridSwatch("#D3D3D3", 0.0)
    qtbot.addWidget(swatch)
    image = swatch.grab().toImage()
    last = SWATCH_PX - 1
    for x, y in ((0, 0), (last, 0), (0, last), (last, last), (SWATCH_PX // 3, 0), (0, SWATCH_PX // 3)):
        assert image.pixelColor(x, y) == palette.SWATCH_OUTLINE
    assert image.pixelColor(3, 3) == palette.SHEET
