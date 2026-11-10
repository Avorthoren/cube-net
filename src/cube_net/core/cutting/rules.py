# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Validity rules of the cut line (docs/idea.txt, CUTTING state; docs/plan.md, section 4.2).

The cut line must lie strictly inside the net, except for its first and last points, which lie on the perimeter. So a
new segment a-b may touch the perimeter only at a or b, and only if that end is on the perimeter; it may touch the
cut line only at a, where it continues the previous segment.
"""

from collections.abc import Iterable, Sequence
from fractions import Fraction
from itertools import pairwise
from math import ceil

from cube_net.core.cutting.cut_line import CutLine, CutPoint
from cube_net.core.geometry import IntersectionKind, Vec, classify_segments, on_segment
from cube_net.core.net import HalfEdge, Net

# At most this many points after the first one (docs/idea.txt).
MAX_POINTS_AFTER_FIRST = 50

# How far apart the points are that a point projected onto a cut can land on: the size mouse input is rounded to.
PROJECTION_STEP = Fraction(1, 1000)


def project_onto(edge: HalfEdge, p: Vec) -> Vec:
    """The point of the cut `edge` closest to `p`, among points at most `PROJECTION_STEP` apart along it (the ends of
    the cut included). It's exactly on the cut.

    The steps are there because the exact closest point has a denominator of about the square of the cut's. Points on
    a cut become the ends of later cuts, so the numbers would double in length with every generation of cuts, and soon
    have thousands of digits. This way they just grow a little. Mouse input is rounded to the same size anyway.
    """
    a, b = edge.origin.position, edge.destination.position
    d = b - a
    t = min(max((p - a).dot(d) / d.length_squared(), Fraction(0)), Fraction(1))
    steps = max(1, ceil((abs(d.x) + abs(d.y)) / PROJECTION_STEP))
    return a + d * Fraction(round(t * steps), steps)


def strictly_inside(net: Net, p: Vec) -> bool:
    """`p` is on the net but not on its perimeter (folds inside the net are fine)."""
    if not net.contains(p):
        return False
    return not any(on_segment(p, he.origin.position, he.destination.position) for he in net.boundary_edges())


def segment_valid(net: Net, points: Sequence[CutPoint], i: int) -> bool:
    """Is segment i (from points[i] to points[i + 1]) of the polyline `points` valid?

    It must lie strictly inside the net except for ends on the perimeter, touch the perimeter only at such ends, and
    touch the rest of the polyline only where it continues it: at its own ends, and only with the neighbouring
    segments (no overlap, no going back along them).
    """
    a, b = points[i], points[i + 1]
    if a.position == b.position:
        return False
    for p in (a, b):
        if not p.on_perimeter and not strictly_inside(net, p.position):
            return False
    if not strictly_inside(net, (a.position + b.position) / 2):
        return False  # e.g. leaving the net straight from a point on the perimeter
    for he in net.boundary_edges():
        hit = classify_segments(a.position, b.position, he.origin.position, he.destination.position)
        if hit.kind is IntersectionKind.DISJOINT:
            continue
        if hit.kind is not IntersectionKind.TOUCH:
            return False
        touch = hit.point
        if not ((touch == a.position and a.on_perimeter) or (touch == b.position and b.on_perimeter)):
            return False
    for j, (c, d) in enumerate(pairwise(p.position for p in points)):
        if j == i:
            continue
        hit = classify_segments(a.position, b.position, c, d)
        if hit.kind is IntersectionKind.DISJOINT:
            continue
        shared = a.position if j == i - 1 else b.position if j == i + 1 else None
        if not (hit.kind is IntersectionKind.TOUCH and hit.point == shared):
            return False
    return True


def invalid_segments(net: Net, points: Sequence[CutPoint], indices: Iterable[int]) -> list[int]:
    """Which of the segments `indices` of the polyline `points` are invalid."""
    return [i for i in indices if 0 <= i < len(points) - 1 and not segment_valid(net, points, i)]


def segment_allowed(net: Net, line: CutLine, end: CutPoint) -> bool:
    """May the segment from the line's last point to `end` be added?"""
    points = [*line.points, end]
    return segment_valid(net, points, len(points) - 2)
