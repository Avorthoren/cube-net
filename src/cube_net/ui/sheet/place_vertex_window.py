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

The coordinates are shown and typed from the origin (right click -> Move the origin: `Origin`), the point is placed at
the sheet point they stand for.

Place (the default button: Enter) places the point; if it can't go there, the window stays and says why. Cancel, Escape
and the close button change nothing.
"""

from collections.abc import Callable

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
from cube_net.core.origin import DEFAULT_ORIGIN, Origin
from cube_net.ui import palette
from cube_net.ui.dialogs.small_window import SmallWindow
from cube_net.ui.i18n import tr
from cube_net.ui.sheet.coordinate_row import CoordinateRow


def problem_text(problem: Problem) -> str:
    """What the window says when the point can't go there."""
    match problem:
        case Problem.ON_PERIMETER:
            return tr("The point is on the perimeter: only a point put on a cut can be there.")
        case Problem.OFF_EDGE:
            return tr("The point is beyond the ends of its edge.")
        case Problem.OFF_FOLD:
            return tr("The point is beyond the ends of its fold line.")
        case Problem.TOO_MANY_POINTS:
            return tr("The line already has as many points as it can have.")
        case Problem.BREAKS_LINE:
            return tr("From there, the line would touch the perimeter, or touch or cross itself.")


class PlaceVertexWindow(SmallWindow):
    def __init__(
        self,
        placement: Placement,
        place: Callable[[Vec], Problem | str | None],
        parent: QWidget | None = None,
        origin: Origin = DEFAULT_ORIGIN,
    ) -> None:
        """`place`: puts the point at a sheet point, or tells why it can't (a `Problem`, or what to say)."""
        super().__init__(tr("Place a vertex"), parent)
        self._placement = placement
        self._place = place
        self._origin = origin
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        shown = origin.shown(placement.position)
        self.y = CoordinateRow("y", shown.y, grid, 0, self)
        self.x = CoordinateRow("x", shown.x, grid, 1, self)
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
        """The sheet point typed (on a line: from the coordinate typed last), or None if a field it needs isn't a
        number."""
        constraint = self._placement.constraint
        x, y = self.x.value(), self.y.value()
        at = self._origin.position
        if constraint.bound:
            source = (self.x if self._source is Axis.X else self.y).value()
            if source is None:
                return None
            return constraint.point_from(self._source, source + at.x, source + at.y)
        if x is None or y is None:
            return None
        return constraint.point_from(Axis.BOTH, x + at.x, y + at.y)

    def _typed(self, source: Axis) -> None:
        """A coordinate's field was edited by the user: on a line, the other coordinate follows at once."""
        if not self._placement.constraint.bound:
            return
        self._source = source
        point = self.point()
        if point is None:
            return  # not a number yet: the other keeps its value
        follower = self.y if source is Axis.X else self.x
        shown = self._origin.shown(point)
        follower.set_value(shown.y if source is Axis.X else shown.x)

    def _on_place(self) -> None:
        point = self.point()
        if point is None:
            self._say(tr("Enter whole numbers, with denominators above 0."))
            return
        problem = self._place(point)
        if problem is not None:
            self._say(problem if isinstance(problem, str) else problem_text(problem))
            return
        self.accept()

    def _say(self, text: str) -> None:
        self.message.setText(text)
        self.message.show()
        self.adjustSize()
