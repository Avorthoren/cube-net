# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Vec
from cube_net.ui.sheet.move_origin_window import MoveOriginWindow


def make(qtbot: QtBot, shown: Vec) -> MoveOriginWindow:
    window = MoveOriginWindow(shown)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    return window


def texts(window: MoveOriginWindow) -> list[str]:
    return [f"{row.numerator.text()}/{row.denominator.text()} {row.worth.text()}" for row in (window.y, window.x)]


def test_starts_with_the_points_coordinates_y_selected(qtbot: QtBot) -> None:
    window = make(qtbot, Vec(11, F(-27, 2)))
    assert window.windowTitle() == "Move the origin"
    assert texts(window) == ["-27/2 = -13.500", "11/1 = 11.000"]
    assert all(row.numerator.isEnabled() and row.denominator.isEnabled() for row in (window.x, window.y))
    qtbot.waitUntil(window.y.numerator.hasFocus)
    assert window.y.numerator.selectedText() == "-27"
    assert window.move_button.isDefault()


def test_move_gives_the_typed_coordinates(qtbot: QtBot) -> None:
    window = make(qtbot, Vec(11, 13))
    window.x.numerator.setText("-1")
    window.x.denominator.setText("3")
    with qtbot.waitSignal(window.accepted):
        window.move_button.click()
    assert window.coordinates() == Vec(F(-1, 3), 13)


def test_not_numbers_says_so_and_stays(qtbot: QtBot) -> None:
    window = make(qtbot, Vec(11, 13))
    window.y.denominator.setText("0")
    window.move_button.click()
    assert window.isVisible() and window.coordinates() is None
    assert window.message.isVisible() and window.message.text() == "Enter whole numbers, with denominators above 0."


def test_cancel(qtbot: QtBot) -> None:
    window = make(qtbot, Vec(11, 13))
    with qtbot.waitSignal(window.rejected):
        window.cancel_button.click()
