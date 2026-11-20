# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

from PyQt6.QtWidgets import QGridLayout, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.sheet.coordinate_row import CoordinateRow

# The rows' parents: kept, or their fields would go with them.
_PARENTS: list[QWidget] = []


def make(qtbot: QtBot, value: F) -> CoordinateRow:
    parent = QWidget()
    qtbot.addWidget(parent)
    _PARENTS.append(parent)
    return CoordinateRow("y", value, QGridLayout(parent), 0, parent)


def test_the_fraction_and_what_its_worth(qtbot: QtBot) -> None:
    row = make(qtbot, F(-1, 3))
    assert (row.numerator.text(), row.denominator.text(), row.worth.text()) == ("-1", "3", "≈ -0.333")
    assert row.value() == F(-1, 3)


def test_typed_and_half_typed(qtbot: QtBot) -> None:
    row = make(qtbot, F(1))
    row.denominator.setText("8")
    assert row.value() == F(1, 8) and row.worth.text() == "= 0.125"
    row.numerator.setText("")
    assert row.value() is None and row.worth.text() == ""


def test_typed_or_not(qtbot: QtBot) -> None:
    row = make(qtbot, F(1))
    row.set_typed(False)
    assert not row.numerator.isEnabled() and not row.denominator.isEnabled()


def test_every_edit_of_the_numerator_makes_the_denominator_1(qtbot: QtBot) -> None:
    row = make(qtbot, F(-1, 3))
    row.numerator.setFocus()
    qtbot.keyClick(row.numerator, "5")
    assert (row.numerator.text(), row.denominator.text()) == ("-15", "1") and row.value() == -15
    row.denominator.setText("4")
    qtbot.keyClick(row.numerator, "\b")  # Backspace
    assert (row.numerator.text(), row.denominator.text()) == ("-1", "1")


def test_the_program_setting_it_or_the_denominator_edited_dont(qtbot: QtBot) -> None:
    row = make(qtbot, F(1))
    row.set_value(F(7, 2))
    assert row.denominator.text() == "2"
    qtbot.keyClick(row.denominator, "0")
    assert (row.numerator.text(), row.denominator.text()) == ("7", "20")
