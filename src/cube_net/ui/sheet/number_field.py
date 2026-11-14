# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fields for whole numbers in the windows of the cut line (Place a vertex, Set slope): `number_field` and its
`DigitsValidator`.

At most `MAX_DIGITS` digits can be typed; a longer number put there by the program (an exact coordinate, however long)
can only get shorter, and can always get a minus sign where one is allowed. A field shows a 10-digit number whole (a
signed one has room for its minus sign too); a longer one visibly doesn't fit, and is scrolled.
"""

import re
from enum import Enum

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QValidator
from PyQt6.QtWidgets import QLineEdit, QStyle, QWidget

from cube_net.ui.sheet.coordinates_text import MAX_DIGITS

# How many digits a field shows at once: a 10-digit number fits, a longer one visibly doesn't.
UNSIGNED_DIGITS_SHOWN = 10.5

# A signed field: room for the minus sign too.
SIGNED_DIGITS_SHOWN = 11.5

# Qt's line edit keeps this much space between its frame and its text, on each side (px).
FIELD_TEXT_MARGIN_PX = 2


class Numbers(Enum):
    # Any integer: a numerator, a slope's y and x.
    INTEGERS = "integers"

    # Above 0: a denominator.
    POSITIVE = "positive"


class DigitsValidator(QValidator):
    """A whole number of `numbers`, of at most `MAX_DIGITS` digits as typed (see the module's docstring)."""

    def __init__(self, field: QLineEdit, numbers: Numbers) -> None:
        super().__init__(field)
        self._numbers = numbers
        # The field's text before the edit being checked (while it's checked, the field already has the new one).
        self._before = field.text()
        field.textChanged.connect(self._remember)

    def _remember(self, text: str) -> None:
        self._before = text

    def allow(self, text: str) -> None:
        """`text` is about to be put in the field by the program (a coordinate, however long): it's fine as it is.
        (Qt checks it at once, and stops undoing invalid edits after a text it found invalid.)"""
        self._before = text

    def validate(self, a0: str | None, a1: int) -> tuple[QValidator.State, str, int]:
        text = a0 or ""
        signed = self._numbers is Numbers.INTEGERS
        match = re.fullmatch(r"(-?)(\d*)" if signed else r"()(\d*)", text)
        if match is None:
            return QValidator.State.Invalid, text, a1
        digits = len(match.group(2))
        before = sum(c.isdigit() for c in self._before)
        if digits > MAX_DIGITS and digits > before:
            return QValidator.State.Invalid, text, a1
        if digits == 0 or (self._numbers is Numbers.POSITIVE and int(match.group(2)) == 0):
            return QValidator.State.Intermediate, text, a1
        return QValidator.State.Acceptable, text, a1


def number_field(parent: QWidget, numbers: Numbers) -> QLineEdit:
    field = QLineEdit(parent)
    field.setValidator(DigitsValidator(field, numbers))
    field.setAlignment(Qt.AlignmentFlag.AlignRight)
    digits = SIGNED_DIGITS_SHOWN if numbers is Numbers.INTEGERS else UNSIGNED_DIGITS_SHOWN
    field.setFixedWidth(round(field.fontMetrics().horizontalAdvance("0") * digits) + _field_frame(field))
    return field


def set_number(field: QLineEdit, number: int) -> None:
    """Put `number` in the field, however long (the program's, not typed)."""
    validator = field.validator()
    assert isinstance(validator, DigitsValidator)
    validator.allow(str(number))
    field.setText(str(number))


def _field_frame(field: QLineEdit) -> int:
    """How much wider a field is than its text: its frame and margins, on both sides."""
    style = field.style()
    frame = style.pixelMetric(QStyle.PixelMetric.PM_DefaultFrameWidth) if style is not None else 2
    margins = field.textMargins()
    return 2 * (frame + FIELD_TEXT_MARGIN_PX) + margins.left() + margins.right()
