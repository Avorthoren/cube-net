# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The key events go to the window (`QWindow`), as the system delivers them, and from there to the focused widget."""

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent, QWindow
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.key_release_shortcut import KeyReleaseShortcut

L = Qt.Key.Key_L


class Window(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.button = QPushButton("A button", self)
        self.text = QLineEdit(self)
        self.number = QSpinBox(self)
        layout = QVBoxLayout(self)
        for widget in (self.button, self.text, self.number):
            layout.addWidget(widget)
        self.shortcut = KeyReleaseShortcut(L, self)
        self.activated = 0
        self.shortcut.activated.connect(self._count)

    def _count(self) -> None:
        self.activated += 1

    def handle(self) -> QWindow:
        handle = self.windowHandle()
        assert handle is not None
        return handle


@pytest.fixture
def window(qtbot: QtBot) -> Window:
    window = Window()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.button.setFocus()
    return window


def test_it_acts_when_the_key_is_released(window: Window) -> None:
    QTest.keyPress(window.handle(), L)
    assert window.activated == 0
    QTest.keyRelease(window.handle(), L)
    assert window.activated == 1


def send(window: Window, kind: QEvent.Type, repeat: bool) -> None:
    QApplication.sendEvent(window.handle(), QKeyEvent(kind, L, Qt.KeyboardModifier.NoModifier, "l", repeat))


def test_held_it_acts_once(window: Window) -> None:
    send(window, QEvent.Type.KeyPress, repeat=False)
    for _ in range(3):  # the system's repeats, while it's held
        send(window, QEvent.Type.KeyRelease, repeat=True)
        send(window, QEvent.Type.KeyPress, repeat=True)
    assert window.activated == 0
    send(window, QEvent.Type.KeyRelease, repeat=False)
    assert window.activated == 1


@pytest.mark.parametrize(
    "modifier",
    [Qt.KeyboardModifier.ShiftModifier, Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.AltModifier],
)
def test_not_with_modifiers(window: Window, modifier: Qt.KeyboardModifier) -> None:
    QTest.keyClick(window.handle(), L, modifier)
    assert window.activated == 0


def test_another_key_in_between_cancels_it(window: Window) -> None:
    QTest.keyPress(window.handle(), L)
    QTest.keyClick(window.handle(), Qt.Key.Key_K)
    QTest.keyRelease(window.handle(), L)
    assert window.activated == 0


def test_a_release_without_its_press_does_nothing(window: Window) -> None:
    QTest.keyRelease(window.handle(), L)
    assert window.activated == 0


@pytest.mark.parametrize("field", ["text", "number"])
def test_typing_is_typing(qtbot: QtBot, window: Window, field: str) -> None:
    widget = getattr(window, field)
    widget.setFocus()
    qtbot.waitUntil(widget.hasFocus)
    QTest.keyClick(window.handle(), L)
    assert window.activated == 0


def test_only_in_its_window(qtbot: QtBot, window: Window) -> None:
    other = QWidget()
    qtbot.addWidget(other)
    other.show()
    qtbot.waitExposed(other)
    handle = other.windowHandle()
    assert handle is not None
    QTest.keyPress(window.handle(), L)
    QTest.keyPress(handle, L)  # pressed elsewhere: that's not ours any more
    QTest.keyRelease(window.handle(), L)
    QTest.keyClick(handle, L)
    assert window.activated == 0
