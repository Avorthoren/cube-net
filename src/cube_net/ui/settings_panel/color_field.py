# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`ColorField`: a colour as RGB hex digits, after a `#` that's already there."""

from PyQt6.QtCore import QRegularExpression, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QWidget


class ColorField(QWidget):
    # A complete colour was entered: "#RRGGBB".
    changed = pyqtSignal(str)

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.edit = QLineEdit(color[1:], self)
        self.edit.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9A-Fa-f]{0,6}"), self.edit))
        self.edit.setMaxLength(6)
        width = self.edit.fontMetrics().horizontalAdvance("DDDDDD") + 16
        self.edit.setFixedWidth(width)
        self.edit.textEdited.connect(self._on_edited)
        self.edit.editingFinished.connect(self._on_finished)
        self.hash = QLabel("#", self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.hash)
        layout.addWidget(self.edit)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # the # stays right next to the digits

    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        """Show this colour (without telling anyone)."""
        self._color = color
        self.edit.setText(color[1:])

    def _on_edited(self, text: str) -> None:
        if len(text) == 6:
            self._color = "#" + text.upper()
            self.changed.emit(self._color)

    def _on_finished(self) -> None:
        self.edit.setText(self._color[1:])  # an unfinished colour goes back to the one in use
