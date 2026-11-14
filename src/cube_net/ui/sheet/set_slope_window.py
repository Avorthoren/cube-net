# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`SetSlopeWindow`: the slope of the current segment of the cut line, typed (docs/idea.txt: right click -> Set slope).

    y: [integer]
    x: [integer]

The segment rises y while it goes x: x = 0 is vertical (a line's slope is the same with both signs turned). The fields
start with the slope the segment has now (the smallest such integers, x not below 0), y's selected and with the focus;
at most `MAX_DIGITS` digits can be typed. Set (the default button: Enter) gives the slope, unless both are 0; Cancel,
Escape and the close button don't.
"""

from PyQt6.QtWidgets import QDialogButtonBox, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from cube_net.core.geometry import Vec
from cube_net.ui import palette
from cube_net.ui.dialogs.small_window import SmallWindow
from cube_net.ui.i18n import tr
from cube_net.ui.sheet.number_field import Numbers, number_field, set_number


class SetSlopeWindow(SmallWindow):
    def __init__(self, y: int, x: int, parent: QWidget | None = None) -> None:
        """The slope shown at first: y over x."""
        super().__init__(tr("Set slope"), parent)
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        self.y = number_field(self, Numbers.INTEGERS)
        self.x = number_field(self, Numbers.INTEGERS)
        for row, (name, field, value) in enumerate((("y", self.y, y), ("x", self.x, x))):
            grid.addWidget(QLabel(f"{name}:", self), row, 0)
            grid.addWidget(field, row, 1)
            set_number(field, value)
        self.message = QLabel(self)
        self.message.setWordWrap(True)
        self.message.setStyleSheet(f"color: {palette.ERROR_TEXT.name()};")
        self.message.hide()
        buttons = QDialogButtonBox(self)
        self.set_button = QPushButton(tr("Set"), self)
        buttons.addButton(self.set_button, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        assert cancel is not None
        self.cancel_button = cancel
        self.set_button.clicked.connect(self._on_set)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addLayout(grid)
        layout.addWidget(self.message)
        layout.addWidget(buttons)
        self.body.addLayout(layout)
        self.set_button.setDefault(True)
        self.y.setFocus()
        self.y.selectAll()

    def direction(self) -> Vec | None:
        """The typed slope as a direction (x, y), or None if it isn't one (not numbers, or both 0)."""
        try:
            y, x = int(self.y.text()), int(self.x.text())
        except ValueError:
            return None
        return None if x == y == 0 else Vec(x, y)

    def _on_set(self) -> None:
        if self.direction() is None:
            self.message.setText(tr("Enter a slope: whole numbers, not both 0 (x = 0 is vertical)."))
            self.message.show()
            self.adjustSize()
            return
        self.accept()
