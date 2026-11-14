# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Placing a point of the cut line at typed coordinates (docs/idea.txt: right click -> Place a vertex).

The point would have been put somewhere by a click or a drag; that place decides what it may be:
- free (inside a face): both coordinates are typed;
- on a perimeter edge (a cut) or on a fold line: the coordinates are tied by the line's equation, and the point must
  stay on that edge or fold, between its ends. On a slanted line either coordinate is typed, and the other follows
  from it; on a vertical line only y (x is the line's), on a horizontal one only x;
- on SHIFT's horizontal or vertical line through the previous point (unless it would have snapped to an edge, which
  wins): the coordinate along the line is typed, the other is the previous point's.

`Constraint` says which, and `problem` tells why a typed point can't go there, before the editor's own rules (which
may still reject the segments: see `Problem.BREAKS_LINE`).
"""

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from cube_net.core.cutting.rules import strictly_inside
from cube_net.core.geometry import Vec, on_segment
from cube_net.core.net import HalfEdge, Net


class LineKind(Enum):
    # Inside a face: both coordinates are free.
    FREE = "free"

    # On a perimeter edge (a cut).
    EDGE = "edge"

    # On a fold line.
    FOLD = "fold"

    # On SHIFT's horizontal or vertical line through the previous point.
    STRAIGHT = "straight"


class Axis(Enum):
    # Both coordinates are typed (free; or on a slanted line, where either one gives the other).
    BOTH = "both"

    # Only y (a vertical line: x is the line's).
    Y = "y"

    # Only x (a horizontal line: y is the line's).
    X = "x"


class Problem(Enum):
    # A point inside the net (not one of the line's ends) is outside it.
    OUTSIDE_NET = "outside_net"

    # A point inside the net is on its perimeter, where only the line's ends may be.
    ON_PERIMETER = "on_perimeter"

    # A point on an edge is beyond its ends (or off its line).
    OFF_EDGE = "off_edge"

    # A point on a fold line is beyond its ends (or off its line).
    OFF_FOLD = "off_fold"

    # The line already has as many points as it may.
    TOO_MANY_POINTS = "too_many_points"

    # The new segments would leave the net, or touch or cross the line (the editor's rules reject them).
    BREAKS_LINE = "breaks_line"


@dataclass(frozen=True)
class Constraint:
    kind: LineKind

    # EDGE, FOLD: the segment's ends; STRAIGHT: the previous point (`a`) and, as `b`, any other point of the line.
    a: Vec | None = None
    b: Vec | None = None

    # EDGE: the cut; FOLD: the fold.
    edge: HalfEdge | None = None

    @staticmethod
    def free() -> Constraint:
        return Constraint(LineKind.FREE)

    @staticmethod
    def on_edge(edge: HalfEdge) -> Constraint:
        return Constraint(LineKind.EDGE, edge.origin.position, edge.destination.position, edge)

    @staticmethod
    def on_fold(fold: HalfEdge) -> Constraint:
        return Constraint(LineKind.FOLD, fold.origin.position, fold.destination.position, fold)

    @staticmethod
    def straight(anchor: Vec, horizontal: bool) -> Constraint:
        return Constraint(LineKind.STRAIGHT, anchor, anchor + (Vec(1, 0) if horizontal else Vec(0, 1)))

    @property
    def axis(self) -> Axis:
        """The coordinates that can be typed: both (free, or a slanted line); only y on a vertical line, only x on a
        horizontal one."""
        if self.kind is LineKind.FREE:
            return Axis.BOTH
        assert self.a is not None and self.b is not None
        if self.a.y == self.b.y:
            return Axis.X
        return Axis.Y if self.a.x == self.b.x else Axis.BOTH

    @property
    def bound(self) -> bool:
        """The coordinates are tied by a line: typing one gives the other."""
        return self.kind is not LineKind.FREE

    def point_from(self, source: Axis, x: Fraction, y: Fraction) -> Vec:
        """The point: (x, y) if it's free; on a line, the one whose `source` coordinate (X or Y) is the typed one of
        (x, y), the other from the line's equation."""
        if self.kind is LineKind.FREE:
            return Vec(x, y)
        a, b = self.a, self.b
        assert a is not None and b is not None
        if self.axis is not Axis.BOTH:
            source = self.axis  # only that one can be typed
        if source is Axis.X:
            return Vec(x, a.y + (x - a.x) * (b.y - a.y) / (b.x - a.x))
        return Vec(a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y), y)

    def nearest(self, p: Vec) -> Vec:
        """The point of the line closest to `p`: of an edge or a fold, between its ends (never beyond them, even where
        the next edge goes on in line with it: that's another edge); of SHIFT's line, anywhere; free: `p` itself."""
        if self.kind is LineKind.FREE:
            return p
        a, b = self.a, self.b
        assert a is not None and b is not None
        d = b - a
        t = (p - a).dot(d) / d.length_squared()
        if self.kind is not LineKind.STRAIGHT:
            t = min(max(t, Fraction(0)), Fraction(1))
        return a + d * t

    def problem(self, net: Net, p: Vec) -> Problem | None:
        """Why `p` can't be placed here as far as its own position goes (the segments are the editor's to judge)."""
        if self.kind in (LineKind.EDGE, LineKind.FOLD):
            assert self.a is not None and self.b is not None
            if not on_segment(p, self.a, self.b):
                return Problem.OFF_EDGE if self.kind is LineKind.EDGE else Problem.OFF_FOLD
        if self.kind is LineKind.EDGE:
            return None  # the line's ends belong on the perimeter
        if not net.contains(p):
            return Problem.OUTSIDE_NET
        if not strictly_inside(net, p):
            return Problem.ON_PERIMETER
        return None


def fold_through(net: Net, p: Vec) -> HalfEdge | None:
    """The fold line `p` lies exactly on, if any (a typed point there is on that fold, as a clicked one would be)."""
    return next(
        (fold for fold in net.fold_edges() if on_segment(p, fold.origin.position, fold.destination.position)), None
    )


class Action(Enum):
    # DEFAULT: the line's first point (on the perimeter).
    START = "start"

    # CUTTING: the line's next point.
    ADD = "add"

    # CUT_EDITING: the point being dragged goes there.
    MOVE = "move"


@dataclass(frozen=True)
class Placement:
    """What a right click offers to place by typing: where the point would have gone by a click (or the drag), what
    it may be (`constraint`), and what placing it does."""

    action: Action
    position: Vec
    constraint: Constraint

    # MOVE: the index of the point being dragged.
    index: int | None = None
