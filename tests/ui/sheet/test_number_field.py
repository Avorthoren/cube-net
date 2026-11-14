# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.sheet.coordinates_text import MAX_DIGITS
from cube_net.ui.sheet.number_field import Numbers, number_field, set_number


@pytest.fixture
def parent(qtbot: QtBot) -> QWidget:
    widget = QWidget()
    qtbot.addWidget(widget)
    return widget


@pytest.mark.parametrize(
    ("numbers", "typed", "kept", "acceptable"),
    [
        (Numbers.INTEGERS, "-12", "-12", True),
        (Numbers.INTEGERS, "0", "0", True),
        (Numbers.POSITIVE, "-12", "12", True),  # no minus there
        (Numbers.POSITIVE, "0", "0", False),  # not above 0 (yet)
    ],
)
def test_what_can_be_typed(
    qtbot: QtBot, parent: QWidget, numbers: Numbers, typed: str, kept: str, acceptable: bool
) -> None:
    field = number_field(parent, numbers)
    qtbot.keyClicks(field, typed)
    assert field.text() == kept and field.hasAcceptableInput() is acceptable


def test_at_most_10_digits_typed_but_longer_ones_shown(qtbot: QtBot, parent: QWidget) -> None:
    field = number_field(parent, Numbers.INTEGERS)
    qtbot.keyClicks(field, "1" * (MAX_DIGITS + 1))
    assert field.text() == "1" * MAX_DIGITS
    set_number(field, 10**15)
    assert field.text() == str(10**15)


def test_a_10_digit_number_fits(parent: QWidget) -> None:
    for numbers in Numbers:
        field = number_field(parent, numbers)
        assert field.fontMetrics().horizontalAdvance("1234567890") < field.width() - 8
