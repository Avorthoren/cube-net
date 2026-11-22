# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`CoordinateRow`: one coordinate typed as a fraction, in the windows that take exact coordinates (Place a vertex,
Move the origin): its numerator, its denominator, and what it's worth.

    y: [numerator] / [denominator]  ≈ 12.922

Every edit of the numerator sets the denominator to 1: a whole number typed is the coordinate.
"""

from fractions import Fraction

from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget

from cube_net.ui.sheet.coordinates_text import decimal_text, is_exact
from cube_net.ui.sheet.number_field import Numbers, number_field, set_number


class CoordinateRow:
    """One coordinate's fields and what it's worth, in a row of the window's grid."""

    def __init__(self, name: str, value: Fraction, grid: QGridLayout, row: int, parent: QWidget) -> None:
        self.numerator = number_field(parent, Numbers.INTEGERS)
        self.denominator = number_field(parent, Numbers.POSITIVE)
        self.worth = QLabel(parent)
        grid.addWidget(QLabel(f"{name}:", parent), row, 0)
        grid.addWidget(self.numerator, row, 1)
        grid.addWidget(QLabel("/", parent), row, 2)
        grid.addWidget(self.denominator, row, 3)
        grid.addWidget(self.worth, row, 4)
        self.numerator.textEdited.connect(self._whole)
        self.numerator.textChanged.connect(self.show_worth)
        self.denominator.textChanged.connect(self.show_worth)
        self.set_value(value)

    def value(self) -> Fraction | None:
        """The typed fraction, or None if it isn't one yet."""
        try:
            numerator, denominator = int(self.numerator.text()), int(self.denominator.text())
        except ValueError:
            return None
        return Fraction(numerator, denominator) if denominator > 0 else None

    def set_value(self, value: Fraction) -> None:
        set_number(self.numerator, value.numerator)
        set_number(self.denominator, value.denominator)

    def set_typed(self, typed: bool) -> None:
        for field in (self.numerator, self.denominator):
            field.setEnabled(typed)

    def _whole(self) -> None:
        """The numerator was edited (typed, deleted, pasted, undone: anything but the program's setting it): the
        denominator becomes 1, so what's typed is the coordinate as it is (asked for on 2026-11-20)."""
        if self.denominator.text() != "1":
            set_number(self.denominator, 1)

    def show_worth(self) -> None:
        value = self.value()
        self.worth.setText("" if value is None else f"{'=' if is_exact(value) else '≈'} {decimal_text(value)}")
