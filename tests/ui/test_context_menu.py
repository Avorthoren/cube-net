# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The menu is answered from timers, as a user would: `choose` waits in its own event loop."""

from collections.abc import Callable

import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QWheelEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.context_menu import ContextMenu, MenuItem


class Window(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.resize(400, 300)
        self.button = QPushButton("Elsewhere", self)
        self.button.setGeometry(300, 250, 90, 30)
        self.clicks = 0
        self.button.clicked.connect(self._clicked)
        self.undo = QAction("Undo", self)
        self.undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.undos = 0
        self.undo.triggered.connect(self._undone)
        self.addAction(self.undo)
        self.moves = 0
        self.wheels = 0
        self.setMouseTracking(True)

    def _clicked(self) -> None:
        self.clicks += 1

    def _undone(self) -> None:
        self.undos += 1

    def mouseMoveEvent(self, a0: object) -> None:
        self.moves += 1

    def wheelEvent(self, a0: object) -> None:
        self.wheels += 1


@pytest.fixture
def window(qtbot: QtBot) -> Window:
    window = Window()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    return window


ITEMS = [MenuItem("Place a vertex"), MenuItem("Disabled", enabled=False), MenuItem("Third")]


def choose(window: Window, act: Callable[[ContextMenu], None], items: list[MenuItem] = ITEMS) -> int | None:
    menu = ContextMenu(window, items)
    QTimer.singleShot(0, lambda: act(menu))
    return menu.choose(QPoint(50, 40))


def click(menu: ContextMenu, i: int) -> None:
    QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.item_rect(i).center())


def keys(window: Window, *pressed: Qt.Key) -> None:
    handle = window.windowHandle()
    assert handle is not None
    for key in pressed:
        QTest.keyClick(handle, key)


def test_a_click_on_an_item_chooses_it(window: Window) -> None:
    assert choose(window, lambda menu: click(menu, 2)) == 2


def test_at_the_mouse_inside_the_window(window: Window) -> None:
    def look(menu: ContextMenu) -> None:
        assert menu.isVisible() and menu.pos() == QPoint(50, 40) and menu.size() == menu.sizeHint()
        menu.close_with(None)

    choose(window, look)
    menu = ContextMenu(window, ITEMS)
    size = menu.sizeHint()
    menu.resize(size)
    corner = QPoint(window.width() - 5, window.height() - 5)
    assert menu.place(corner) == QPoint(window.width() - size.width(), window.height() - size.height())


def test_a_disabled_item_isnt_chosen(window: Window) -> None:
    def act(menu: ContextMenu) -> None:
        click(menu, 1)
        assert menu.is_open()
        keys(window, Qt.Key.Key_Escape)

    assert choose(window, act) is None


def test_a_release_alone_doesnt_choose(window: Window) -> None:
    """A button held before the menu opened (a drag's), released over an item."""

    def act(menu: ContextMenu) -> None:
        QTest.mouseRelease(menu, Qt.MouseButton.LeftButton, pos=menu.item_rect(0).center())
        assert menu.is_open()
        click(menu, 0)

    assert choose(window, act) == 0


def test_the_keys(window: Window) -> None:
    def act(menu: ContextMenu) -> None:
        keys(window, Qt.Key.Key_Down)
        assert menu.current() == 0
        keys(window, Qt.Key.Key_Down)
        assert menu.current() == 2  # the disabled one is skipped
        keys(window, Qt.Key.Key_Down)
        assert menu.current() == 0  # round again
        keys(window, Qt.Key.Key_Up, Qt.Key.Key_Return)

    assert choose(window, act) == 2


def test_a_press_elsewhere_closes_it_and_is_used_up(window: Window) -> None:
    assert choose(window, lambda menu: QTest.mouseClick(window.button, Qt.MouseButton.LeftButton)) is None
    assert window.clicks == 0


def test_losing_the_focus_closes_it(window: Window) -> None:
    assert choose(window, lambda menu: QApplication.sendEvent(window, QEvent(QEvent.Type.WindowDeactivate))) is None


def test_meanwhile_no_shortcuts_no_wheel_but_moves(window: Window) -> None:
    def act(menu: ContextMenu) -> None:
        handle = window.windowHandle()
        assert handle is not None
        QTest.keyClick(handle, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        wheel = QWheelEvent(
            QPointF(10, 10),
            QPointF(window.mapToGlobal(QPoint(10, 10))),
            QPoint(),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.sendEvent(window, wheel)
        QTest.mouseMove(window, QPoint(200, 200))
        assert menu.is_open()
        menu.close_with(None)

    choose(window, act)
    assert window.undos == 0 and window.wheels == 0
    assert window.moves > 0
    handle = window.windowHandle()
    assert handle is not None
    QTest.keyClick(handle, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert window.undos == 1  # closed: the shortcut works again
