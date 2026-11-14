# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Vec
from cube_net.ui.sheet.set_slope_window import SetSlopeWindow


def make(qtbot: QtBot, y: int = -3, x: int = 2) -> SetSlopeWindow:
    window = SetSlopeWindow(y, x)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    return window


def test_starts_with_the_slope_y_first_selected(qtbot: QtBot) -> None:
    window = make(qtbot)
    assert window.windowTitle() == "Set slope"
    assert (window.y.text(), window.x.text()) == ("-3", "2")
    qtbot.waitUntil(window.y.hasFocus)
    assert window.y.selectedText() == "-3"


def test_set_gives_the_direction(qtbot: QtBot) -> None:
    window = make(qtbot)
    window.y.setText("5")
    window.x.setText("0")  # vertical
    window.set_button.click()
    assert window.result() == SetSlopeWindow.DialogCode.Accepted and window.direction() == Vec(0, 5)


def test_enter_sets(qtbot: QtBot) -> None:
    window = make(qtbot)
    qtbot.waitUntil(window.y.hasFocus)
    qtbot.keyClick(window.y, Qt.Key.Key_Return)
    assert window.result() == SetSlopeWindow.DialogCode.Accepted and window.direction() == Vec(2, -3)


def test_x_can_be_negative(qtbot: QtBot) -> None:
    window = make(qtbot)
    window.x.setFocus()
    window.x.selectAll()
    qtbot.keyClicks(window.x, "-7")
    assert window.x.text() == "-7"
    window.set_button.click()
    assert window.direction() == Vec(-7, -3)


def test_not_both_0(qtbot: QtBot) -> None:
    window = make(qtbot)
    window.y.setText("0")
    window.x.setText("0")
    window.set_button.click()
    assert window.isVisible() and window.message.isVisible() and window.direction() is None
    window.y.clear()
    window.set_button.click()
    assert window.isVisible()


def test_escape_and_cancel(qtbot: QtBot) -> None:
    window = make(qtbot)
    qtbot.waitUntil(window.y.hasFocus)
    qtbot.keyClick(window.y, Qt.Key.Key_Escape)
    assert window.result() == SetSlopeWindow.DialogCode.Rejected
    other = make(qtbot)
    other.cancel_button.click()
    assert other.result() == SetSlopeWindow.DialogCode.Rejected
