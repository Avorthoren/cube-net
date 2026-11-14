# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Origin`: where the coordinate system the user sees has its origin (docs/idea.txt: right click -> Move the origin).

The geometry never moves: the net, the cut line and the grid keep their sheet coordinates, the ones the core works in.
Only the coordinates shown and typed are shifted (never turned): a point at sheet coordinates p is shown at p minus the
origin's position.
"""

from dataclasses import dataclass
from fractions import Fraction

from cube_net.core.geometry import QUANTUM, Vec, quantize

_ZERO = Vec(0, 0)


@dataclass(frozen=True, slots=True)
class Origin:
    # Where the shown origin is, in sheet coordinates.
    position: Vec = _ZERO

    # The point it was moved by (sheet coordinates) and that point's name then (None: never moved).
    point: Vec | None = None
    name: str | None = None

    def shown(self, p: Vec) -> Vec:
        """How the sheet point `p` is shown."""
        return p - self.position

    def sheet(self, shown: Vec) -> Vec:
        """The sheet point shown at `shown`."""
        return shown + self.position

    def quantize(self, x: float, y: float) -> Vec:
        """The mouse at sheet point (x, y), rounded to the nearest thousandth of the shown coordinates (so that what a
        click makes is what the footer showed)."""
        if self.position == _ZERO:
            return quantize(x, y)
        shown_x, shown_y = Fraction(x) - self.position.x, Fraction(y) - self.position.y  # exact: no float arithmetic
        return self.sheet(Vec(round(shown_x / QUANTUM) * QUANTUM, round(shown_y / QUANTUM) * QUANTUM))

    def moved(self, point: Vec, shown: Vec, name: str | None) -> Origin:
        """The origin that shows the sheet point `point` (named `name`) at `shown`."""
        return Origin(point - shown, point, name)


# Where the origin is until it's moved: the sheet's own.
DEFAULT_ORIGIN = Origin()
