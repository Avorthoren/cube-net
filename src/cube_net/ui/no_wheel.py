# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fields that ignore the mouse wheel (numbers, drop-down lists): scrolling over one must not change it by accident.
The wheel goes on to what's behind the field (a tab of the settings scrolls as if the field weren't there)."""

from collections.abc import Iterable

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtWidgets import QAbstractSpinBox, QApplication, QComboBox, QWidget


class _WheelPasser(QObject):
    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if event is not None and event.type() == QEvent.Type.Wheel and isinstance(watched, QWidget):
            # Up the parents until one takes it (a scroll area's viewport does), the way Qt passes on an ignored wheel.
            parent = watched.parentWidget()
            while parent is not None:
                event.ignore()
                QApplication.sendEvent(parent, event)
                if event.isAccepted():
                    break
                parent = parent.parentWidget()
            return True  # the field itself never gets it
        return False


def ignore_wheel(fields: Iterable[QAbstractSpinBox | QComboBox], owner: QObject) -> None:
    """Make these fields ignore the mouse wheel (`owner` keeps what that takes alive)."""
    passer = _WheelPasser(owner)
    for field in fields:
        field.installEventFilter(passer)
        line = field.lineEdit() if isinstance(field, QAbstractSpinBox) else None
        if line is not None:
            line.installEventFilter(passer)  # it gets the wheel first when the mouse is over the text
