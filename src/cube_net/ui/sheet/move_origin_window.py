# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`MoveOriginWindow`: the coordinates a point should have, typed; the origin moves so that it has them (docs/idea.txt:
right click -> Move the origin). Two lines, y first, like Place a vertex's:

    y: [numerator] / [denominator]  ≈ 12.922
    x: [numerator] / [denominator]  = 11.000

The fields start with the point's coordinates now (the hint's), in full however long; both can be typed. The y numerator
has the focus, with its text selected. Move (the default button: Enter) gives the coordinates, unless a field isn't a
number; Cancel, Escape and the close button don't.
"""

from PyQt6.QtWidgets import QDialogButtonBox, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from cube_net.core.geometry import Vec
from cube_net.ui import palette
from cube_net.ui.dialogs.small_window import SmallWindow
from cube_net.ui.i18n import tr
from cube_net.ui.sheet.coordinate_row import CoordinateRow


class MoveOriginWindow(SmallWindow):
    def __init__(self, shown: Vec, parent: QWidget | None = None) -> None:
        """`shown`: the point's coordinates now."""
        super().__init__(tr("Move the origin"), parent)
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        self.y = CoordinateRow("y", shown.y, grid, 0, self)
        self.x = CoordinateRow("x", shown.x, grid, 1, self)
        self.message = QLabel(self)
        self.message.setWordWrap(True)
        self.message.setStyleSheet(f"color: {palette.ERROR_TEXT.name()};")
        self.message.hide()
        buttons = QDialogButtonBox(self)
        self.move_button = QPushButton(tr("Move"), self)
        buttons.addButton(self.move_button, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        assert cancel is not None
        self.cancel_button = cancel
        self.move_button.clicked.connect(self._on_move)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addLayout(grid)
        layout.addWidget(self.message)
        layout.addWidget(buttons)
        self.body.addLayout(layout)
        self.move_button.setDefault(True)
        self.y.numerator.setFocus()
        self.y.numerator.selectAll()

    def coordinates(self) -> Vec | None:
        """The typed coordinates, or None if a field isn't a number (or a denominator is 0)."""
        x, y = self.x.value(), self.y.value()
        return None if x is None or y is None else Vec(x, y)

    def _on_move(self) -> None:
        if self.coordinates() is None:
            self.message.setText(tr("Enter whole numbers, with denominators above 0."))
            self.message.show()
            self.adjustSize()
            return
        self.accept()
