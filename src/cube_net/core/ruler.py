"""`Ruler`: the measuring tool's points (docs/idea.txt, "ruler" instrument). Not part of the project or the history."""

import math
from collections.abc import Sequence
from fractions import Fraction
from itertools import pairwise

from cube_net.core.geometry import QUANTUM, Vec


def distance(a: Vec, b: Vec) -> float:
    """Euclidean distance (generally irrational, so a float: for display only)."""
    return math.sqrt(squared_distance(a, b))


def squared_distance(a: Vec, b: Vec) -> Fraction:
    return (b - a).length_squared()


def restricted_point(points: Sequence[Vec], p: Vec) -> Vec:
    """Where the next ruler point goes for the mouse at `p` while SHIFT is held (docs/idea.txt, ruler).

    The first segment is horizontal or vertical; every next one parallel or perpendicular to the previous segment
    (the last one of non-zero length), whichever is closer to `p`, parallel if it's a tie. Without a point there's no
    segment to restrict: `p` itself.

    The point lands on a grid along that direction, with steps of at most `QUANTUM`. The direction is reduced to the
    smallest integer vector: restricted segments keep the same direction (or its perpendicular), so their numbers stay
    small however long the ruler gets.
    """
    if not points:
        return p
    anchor = points[-1]
    previous = next((b - a for a, b in reversed(list(pairwise(points))) if a != b), None)
    if previous is None:
        offset = p - anchor
        return Vec(p.x, anchor.y) if abs(offset.x) >= abs(offset.y) else Vec(anchor.x, p.y)
    along = _primitive(previous)
    across = Vec(-along.y, along.x)
    candidates = [_on_line(anchor, u, p) for u in (along, across)]
    return min(candidates, key=lambda q: (q - p).length_squared())


def _primitive(d: Vec) -> Vec:
    """The smallest vector with integer coordinates pointing the same way as `d` (which isn't zero)."""
    scale = math.lcm(d.x.denominator, d.y.denominator)
    x, y = int(d.x * scale), int(d.y * scale)
    g = math.gcd(x, y)
    return Vec(x // g, y // g)


def _on_line(anchor: Vec, u: Vec, p: Vec) -> Vec:
    """The point of the grid along the line through `anchor` in direction `u` that is closest to `p`."""
    steps = math.ceil((abs(u.x) + abs(u.y)) / QUANTUM)  # u has integer coordinates: one step is at most QUANTUM long
    t = (p - anchor).dot(u) / u.length_squared()
    return anchor + u * Fraction(round(t * steps), steps)


class Ruler:
    """A polyline of measured points: each new point is connected to the previous one."""

    def __init__(self) -> None:
        self._points: list[Vec] = []

    @property
    def points(self) -> Sequence[Vec]:
        return tuple(self._points)

    @property
    def last(self) -> Vec | None:
        return self._points[-1] if self._points else None

    def add(self, p: Vec) -> None:
        self._points.append(p)

    def clear(self) -> None:
        self._points.clear()

    def segments(self) -> list[tuple[Vec, Vec]]:
        """Consecutive pairs of points."""
        return list(pairwise(self._points))

    def total_length(self) -> float:
        """Sum of the lengths of all segments between placed points (0 with fewer than 2 points).

        The exact lengths are summed first; round only for display.
        """
        return math.fsum(distance(a, b) for a, b in self.segments())
