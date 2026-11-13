# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`KeyReleaseShortcut`: a key that acts when it's released, in one window (Qt's shortcuts act when it's pressed)."""

from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QWindow
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)

# The modifiers that make it another key (Shift+L isn't L).
MODIFIERS = (
    Qt.KeyboardModifier.ShiftModifier
    | Qt.KeyboardModifier.ControlModifier
    | Qt.KeyboardModifier.AltModifier
    | Qt.KeyboardModifier.MetaModifier
)


class KeyReleaseShortcut(QObject):
    """`key`, without modifiers, pressed and released in `window`, whichever of its widgets has the focus, except one
    that takes text (typing an "L" there is typing). Not in another window (a menu, a dialog), not when another key
    was pressed in between, and a held key's repeats don't count: one press, one release, one `activated`."""

    activated = pyqtSignal()

    def __init__(self, key: Qt.Key, window: QWidget) -> None:
        super().__init__(window)
        self._key = key
        self._window = window
        self._pressed = False
        app = QApplication.instance()
        assert app is not None
        app.installEventFilter(self)  # every key event reaches the window (QWindow) first, once

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if (
            isinstance(watched, QWindow)
            and isinstance(event, QKeyEvent)
            and event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease)
            and not event.isAutoRepeat()
        ):
            if watched is self._window.windowHandle():
                self._on_key(event)
            elif event.type() == QEvent.Type.KeyPress:
                self._pressed = False  # pressed in another window
        return False

    def _on_key(self, event: QKeyEvent) -> None:
        ours = event.key() == self._key and not event.modifiers() & MODIFIERS and not _typing()
        if event.type() == QEvent.Type.KeyPress:
            self._pressed = ours  # any other key in between cancels it
        elif ours and self._pressed:
            self._pressed = False
            self.activated.emit()


def _typing() -> bool:
    """The focus is on a widget that takes text."""
    focus = QApplication.focusWidget()
    if isinstance(focus, QComboBox):
        return focus.isEditable()
    return isinstance(focus, QLineEdit | QAbstractSpinBox | QTextEdit | QPlainTextEdit)
