"""`Ruler`: the measuring tool's points (docs/idea.txt, "ruler" instrument). Not part of the project or the history."""

import math
from collections.abc import Sequence
from fractions import Fraction
from itertools import pairwise

from cube_net.core.geometry import Vec


def distance(a: Vec, b: Vec) -> float:
    """Euclidean distance (generally irrational, so a float: for display only)."""
    return math.sqrt(squared_distance(a, b))


def squared_distance(a: Vec, b: Vec) -> Fraction:
    return (b - a).length_squared()


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
