# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`DecimalBox`: a field for a number with decimals that doesn't get in the way of typing it. While it has the
keyboard focus, its number is written without trailing zeros (10, 2.5); the zeros come back, to all its decimals,
once the focus leaves it (10.00, 2.50). Always with a dot, never a comma."""

from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QFocusEvent
from PyQt6.QtWidgets import QDoubleSpinBox, QWidget


class DecimalBox(QDoubleSpinBox):
    def __init__(self, decimals: int, allowed: tuple[float, float], step: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Being edited: it had the focus last (`hasFocus` may say otherwise while the window isn't active).
        self._editing = False
        self.setLocale(QLocale.c())  # 1.5, never 1,5
        self.setDecimals(decimals)
        self.setRange(*allowed)
        self.setSingleStep(step)

    def textFromValue(self, value: float) -> str:
        text = super().textFromValue(value)
        if self._editing and "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def focusInEvent(self, event: QFocusEvent | None) -> None:
        super().focusInEvent(event)
        self._editing = True
        self._show_value()

    def focusOutEvent(self, event: QFocusEvent | None) -> None:
        super().focusOutEvent(event)  # takes what was typed
        self._editing = False
        self._show_value()

    def _show_value(self) -> None:
        """The value written anew (with or without the zeros), keeping a whole selection or the cursor where it was."""
        line = self.lineEdit()
        if line is None:
            return
        everything = line.hasSelectedText() and line.selectedText() == line.text()
        cursor = line.cursorPosition()
        text = self.textFromValue(self.value())
        if text == line.text():
            return
        line.setText(text)
        if everything:
            line.selectAll()
        else:
            line.setCursorPosition(min(cursor, len(text)))
