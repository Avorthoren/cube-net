# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable

import pytest
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.settings_panel.color_field import ColorField, place_at_right_edge


def make(qtbot: QtBot) -> ColorField:
    field = ColorField("#0057B8")
    qtbot.addWidget(field)
    return field


def test_shows_the_digits_after_a_hash(qtbot: QtBot) -> None:
    field = make(qtbot)
    assert field.edit.text() == "0057B8"
    assert field.color() == "#0057B8"


def test_a_complete_colour_is_taken_at_once(qtbot: QtBot) -> None:
    field = make(qtbot)
    field.edit.clear()
    with qtbot.waitSignal(field.changed) as blocker:
        qtbot.keyClicks(field.edit, "a1b2c3")
    assert blocker.args == ["#A1B2C3"]
    assert field.color() == "#A1B2C3"


def test_only_hex_digits_and_at_most_six(qtbot: QtBot) -> None:
    field = make(qtbot)
    field.edit.clear()
    qtbot.keyClicks(field.edit, "#zz12345678")
    assert field.edit.text() == "123456"


def test_an_unfinished_colour_goes_back(qtbot: QtBot) -> None:
    field = make(qtbot)
    field.edit.clear()
    with qtbot.assertNotEmitted(field.changed):
        qtbot.keyClicks(field.edit, "12")
    field.edit.editingFinished.emit()
    assert field.edit.text() == "0057B8"


def test_set_color_tells_nobody(qtbot: QtBot) -> None:
    field = make(qtbot)
    with qtbot.assertNotEmitted(field.changed):
        field.set_color("#FFFFFF")
    assert field.edit.text() == "FFFFFF"


def answer_picker(field: ColorField, act: Callable[[QColorDialog], None]) -> None:
    """Once the field's colour picker is open, do this to it."""

    def answer() -> None:
        assert field.picker is not None
        act(field.picker)

    QTimer.singleShot(50, answer)


class TestPicker:
    """The button after the digits, and the colour picker it opens (answered from a timer: it waits in its own loop)."""

    @staticmethod
    def make(qtbot: QtBot) -> ColorField:
        field = ColorField("#0057B8", picker_title=lambda: "Face 1 color")
        qtbot.addWidget(field)
        return field

    def test_only_where_asked_for(self, qtbot: QtBot) -> None:
        assert make(qtbot).pick_button is None
        field = self.make(qtbot)
        assert field.pick_button is not None and field.pick_button.toolTip() == "Choose the color"

    def test_starts_with_the_colour_and_ok_keeps_the_new_one(self, qtbot: QtBot) -> None:
        field = self.make(qtbot)
        seen: list[str] = []
        told: list[str] = []
        field.changed.connect(told.append)

        def act(picker: QColorDialog) -> None:
            seen.extend([picker.currentColor().name().upper(), picker.windowTitle()])
            assert picker.testOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)  # Qt's own, everywhere
            picker.setCurrentColor(QColor("#a1b2c3"))
            picker.accept()

        answer_picker(field, act)
        assert field.pick_button is not None
        field.pick_button.click()
        assert seen == ["#0057B8", "Face 1 color"]
        assert field.color() == "#A1B2C3" and field.edit.text() == "A1B2C3"
        assert told == ["#A1B2C3"]  # once: at once, while the picker showed it
        assert field.picker is None

    def test_cancel_goes_back(self, qtbot: QtBot) -> None:
        field = self.make(qtbot)
        told: list[str] = []
        field.changed.connect(told.append)

        def act(picker: QColorDialog) -> None:
            picker.setCurrentColor(QColor("#a1b2c3"))
            assert field.color() == "#A1B2C3"  # shown while the picker is open
            picker.reject()

        answer_picker(field, act)
        field.pick()
        assert field.color() == "#0057B8" and field.edit.text() == "0057B8"
        assert told == ["#A1B2C3", "#0057B8"]


class TestPlace:
    """The picker opens with its right edge on the application's (where the system lets the application place it)."""

    @staticmethod
    def window(qtbot: QtBot) -> QWidget:
        window = QWidget()
        qtbot.addWidget(window)
        window.setGeometry(20, 20, 700, 560)  # on the tests' screen (800 x 600), with room for the picker
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_its_right_edge_on_the_windows(self, qtbot: QtBot) -> None:
        window = self.window(qtbot)
        dialog = QColorDialog(window)
        place_at_right_edge(dialog, window)
        assert dialog.frameGeometry().right() == window.frameGeometry().right()

    def test_when_the_picker_opens(self, qtbot: QtBot) -> None:
        window = self.window(qtbot)
        field = ColorField("#0057B8", window, picker_title=lambda: "Face 1 color")
        rights: list[int] = []

        def act(picker: QColorDialog) -> None:
            rights.append(picker.frameGeometry().right())
            picker.reject()

        answer_picker(field, act)
        field.pick()
        assert rights == [window.frameGeometry().right()]

    def test_all_of_it_on_the_screen(self, qtbot: QtBot) -> None:
        window = self.window(qtbot)
        window.move(400, 20)  # its right edge is off the screen
        dialog = QColorDialog(window)
        place_at_right_edge(dialog, window)
        screen = window.screen()
        assert screen is not None
        assert dialog.frameGeometry().right() == screen.availableGeometry().right()

    def test_not_on_wayland(self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
        window = self.window(qtbot)
        dialog = QColorDialog(window)
        before = dialog.pos()
        monkeypatch.setattr("cube_net.ui.settings_panel.color_field.QGuiApplication.platformName", lambda: "wayland")
        place_at_right_edge(dialog, window)
        assert dialog.pos() == before
