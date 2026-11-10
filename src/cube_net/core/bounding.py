# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The minimum-area bounding rectangle of the net (docs/idea.txt, "bounding rectangle"; docs/plan.md, section 4.7).

The smallest rectangle around a convex polygon has one side on a hull edge, so it's enough to try a rectangle aligned
with every hull edge. Everything is exact: with an edge direction e and its perpendicular n = e rotated by 90 degrees,
a corner is (s * e + t * n) / |e|^2, where s and t are extreme values of p.e and p.n over the hull; so corners and the
area are rational numbers, and the comparison with the threshold is exact.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from cube_net.core.geometry import Vec, convex_hull


@dataclass(frozen=True, slots=True)
class BoundingRectangle:
    area: Fraction

    # Corners, counter-clockwise.
    corners: tuple[Vec, Vec, Vec, Vec]


def min_area_rectangle(points: Iterable[Vec]) -> BoundingRectangle:
    """The smallest-area rectangle (any orientation) containing all `points` (at least one point).

    If several orientations give the same area, the first hull edge (counter-clockwise from the lowest-leftmost point)
    wins, so the result is deterministic. Degenerate input (all points on a line) gives area 0.
    """
    hull = convex_hull(points)
    if not hull:
        raise ValueError("min_area_rectangle() needs at least one point")
    if len(hull) == 1:
        p = hull[0]
        return BoundingRectangle(Fraction(0), (p, p, p, p))
    if len(hull) == 2:
        a, b = hull
        return BoundingRectangle(Fraction(0), (a, b, b, a))

    best: BoundingRectangle | None = None
    for i, a in enumerate(hull):
        e = hull[(i + 1) % len(hull)] - a
        n = e.rotated90()
        along = [p.dot(e) for p in hull]
        across = [p.dot(n) for p in hull]
        s0, s1, t0, t1 = min(along), max(along), min(across), max(across)
        e2 = e.length_squared()
        area = (s1 - s0) * (t1 - t0) / e2
        if best is None or area < best.area:
            corners = (_corner(e, n, s0, t0), _corner(e, n, s1, t0), _corner(e, n, s1, t1), _corner(e, n, s0, t1))
            best = BoundingRectangle(area, corners)
    assert best is not None
    return best


def _corner(e: Vec, n: Vec, s: Fraction, t: Fraction) -> Vec:
    """The point p with p.e == s and p.n == t (e and n perpendicular and of equal length)."""
    return (e * s + n * t) / e.length_squared()
