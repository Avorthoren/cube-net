# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`PlaceVertexWindow`: a point of the cut line placed at typed coordinates (docs/idea.txt: right click -> Place a
vertex). Two lines, y first, each a fraction and what it's worth:

    y: [numerator] / [denominator]  ≈ 12.922
    x: [numerator] / [denominator]  = 11.000

The fields start with the coordinates of where the point would have gone by a click (or where the drag has brought
it), in full however long. A numerator is an integer, a denominator a positive one; no more than `MAX_DIGITS` digits can
be typed (a longer number there can still be shortened, and given a minus sign). A point snapped to a line has its
coordinates tied by the line's equation (`Constraint`): as one is typed, the other follows at once (while the typed one
is a number). On a slanted line either can be typed; on a vertical or a horizontal one, the fixed coordinate's fields
are disabled. A point fixed by a locked slope (where its line meets what the point snaps to) has all fields disabled,
and Place has the focus. The y numerator has the focus at first (x's, if y is fixed), with its text selected.

Place (the default button: Enter) places the point; if it can't go there, the window stays and says why. Cancel, Escape
and the close button change nothing.
"""

from collections.abc import Callable
from fractions import Fraction

from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cube_net.core.cutting.placement import Axis, Placement, Problem
from cube_net.core.geometry import Vec
from cube_net.ui import palette
from cube_net.ui.dialogs.small_window import SmallWindow
from cube_net.ui.i18n import tr
from cube_net.ui.sheet.coordinates_text import decimal_text, is_exact
from cube_net.ui.sheet.number_field import Numbers, number_field, set_number


def problem_text(problem: Problem) -> str:
    """What the window says when the point can't go there."""
    match problem:
        case Problem.OUTSIDE_NET:
            return tr("The point is outside the net.")
        case Problem.ON_PERIMETER:
            return tr("The point is on the perimeter: only the line's ends can be there.")
        case Problem.OFF_EDGE:
            return tr("The point is beyond the ends of its edge.")
        case Problem.OFF_FOLD:
            return tr("The point is beyond the ends of its fold line.")
        case Problem.TOO_MANY_POINTS:
            return tr("The line already has as many points as it can have.")
        case Problem.BREAKS_LINE:
            return tr("From there, the line would leave the net, or touch or cross itself.")


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

    def show_worth(self) -> None:
        value = self.value()
        self.worth.setText("" if value is None else f"{'=' if is_exact(value) else '≈'} {decimal_text(value)}")


class PlaceVertexWindow(SmallWindow):
    def __init__(
        self, placement: Placement, place: Callable[[Vec], Problem | None], parent: QWidget | None = None
    ) -> None:
        """`place`: puts the point there, or tells why it can't."""
        super().__init__(tr("Place a vertex"), parent)
        self._placement = placement
        self._place = place
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        self.y = CoordinateRow("y", placement.position.y, grid, 0, self)
        self.x = CoordinateRow("x", placement.position.x, grid, 1, self)
        axis = placement.constraint.axis
        self.x.set_typed(axis in (Axis.BOTH, Axis.X))
        self.y.set_typed(axis in (Axis.BOTH, Axis.Y))
        # The coordinate typed last: on a line, the other one follows it.
        self._source = Axis.X if axis is Axis.X else Axis.Y
        for row, source in ((self.x, Axis.X), (self.y, Axis.Y)):
            for field in (row.numerator, row.denominator):
                field.textEdited.connect(lambda _text, source=source: self._typed(source))
        self.message = QLabel(self)
        self.message.setWordWrap(True)
        self.message.setStyleSheet(f"color: {palette.ERROR_TEXT.name()};")
        self.message.hide()
        buttons = QDialogButtonBox(self)
        self.place_button = QPushButton(tr("Place"), self)
        buttons.addButton(self.place_button, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        assert cancel is not None
        self.cancel_button = cancel
        self.place_button.clicked.connect(self._on_place)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addLayout(grid)
        layout.addWidget(self.message)
        layout.addWidget(buttons)
        self.body.addLayout(layout)
        self.place_button.setDefault(True)
        if axis is Axis.NONE:  # fixed (a locked slope's line where it meets what the point snaps to)
            self.place_button.setFocus()
        else:
            first = self.x.numerator if axis is Axis.X else self.y.numerator
            first.setFocus()
            first.selectAll()

    def point(self) -> Vec | None:
        """The typed point (on a line: from the coordinate typed last), or None if a field it needs isn't a number."""
        constraint = self._placement.constraint
        x, y = self.x.value(), self.y.value()
        if constraint.bound:
            source = (self.x if self._source is Axis.X else self.y).value()
            if source is None:
                return None
            return constraint.point_from(self._source, source, source)
        if x is None or y is None:
            return None
        return constraint.point_from(Axis.BOTH, x, y)

    def _typed(self, source: Axis) -> None:
        """A coordinate's field was edited by the user: on a line, the other coordinate follows at once."""
        if not self._placement.constraint.bound:
            return
        self._source = source
        point = self.point()
        if point is None:
            return  # not a number yet: the other keeps its value
        follower = self.y if source is Axis.X else self.x
        follower.set_value(point.y if source is Axis.X else point.x)

    def _on_place(self) -> None:
        point = self.point()
        if point is None:
            self._say(tr("Enter whole numbers, with denominators above 0."))
            return
        problem = self._place(point)
        if problem is not None:
            self._say(problem_text(problem))
            return
        self.accept()

    def _say(self, text: str) -> None:
        self.message.setText(text)
        self.message.show()
        self.adjustSize()
