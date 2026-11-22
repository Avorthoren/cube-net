# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Validity rules of the cut line (docs/idea.txt, CUTTING state; docs/plan.md, section 4.2).

The cut line starts on the perimeter, goes into the net, and may then go anywhere: what it cuts is its parts on the net
(`real_cut.py`, docs/template_plan.md §8.2). It may cross the perimeter, at a cut, but not touch it otherwise; it may
touch itself only where a segment continues the previous one.
"""

from collections.abc import Iterable, Sequence
from enum import Enum
from itertools import pairwise

from cube_net.core.cutting.cut_line import CutLine, CutPoint
from cube_net.core.cutting.perimeter import on_the_perimeter, segment_crossings
from cube_net.core.geometry import IntersectionKind, Vec, classify_segments, on_segment
from cube_net.core.net import Net

# At most this many points after the first one (docs/idea.txt).
MAX_POINTS_AFTER_FIRST = 50


class LineProblem(Enum):
    """Which rule of the cut line a change breaks (what Place a vertex tells)."""

    # A segment of no length: a point where its neighbour on the line is.
    NO_LENGTH = "no length"

    # A point that isn't one of the line's ends on the perimeter (only the line's ends, and the points put on a cut,
    # may be there).
    ON_THE_PERIMETER = "on the perimeter"

    # A segment runs along the perimeter, or touches it elsewhere than at the line's own points on it.
    ALONG_THE_PERIMETER = "along the perimeter"

    # The line's first segment doesn't go into the net from its first point.
    NOT_INTO_THE_NET = "not into the net"

    # At one of its points on the perimeter, the line neither goes into the net nor comes out of it.
    NOT_THROUGH = "not through"

    # The line touches or crosses itself (other than where a segment continues the previous one).
    TOUCHES_ITSELF = "touches itself"

    # The finished line wouldn't divide the net in two exactly at its last point (before it, or not at all).
    NOT_DIVIDED_AT_THE_END = "not divided at the end"


def strictly_inside(net: Net, p: Vec) -> bool:
    """`p` is on the net but not on its perimeter (folds inside the net are fine)."""
    if not net.contains(p):
        return False
    return not any(on_segment(p, he.origin.position, he.destination.position) for he in net.boundary_edges())


def segment_valid(net: Net, points: Sequence[CutPoint], i: int) -> bool:
    """Is segment i (from points[i] to points[i + 1]) of the polyline `points` valid (`segment_problem`)?"""
    return segment_problem(net, points, i) is None


def segment_problem(net: Net, points: Sequence[CutPoint], i: int) -> LineProblem | None:
    """The rule segment i (from points[i] to points[i + 1]) of the polyline `points` breaks, if any.

    Its points that aren't on the perimeter may be anywhere else: on the net, outside it, in a hole. It may cross cuts
    (entering or leaving the net there), but not touch the perimeter anywhere else than at its own points on it, nor
    run along it (`segment_crossings`). At a point on the perimeter, the line goes into the net or out of it: the parts
    of the line on both sides of it, one on the net, the other off it (the first point: the line goes into the net).
    And it touches the rest of the polyline only where it continues it: at its own ends, and only with the
    neighbouring segments (no overlap, no going back along them).
    """
    a, b = points[i], points[i + 1]
    if a.position == b.position:
        return LineProblem.NO_LENGTH
    for p in (a, b):
        if not p.on_perimeter and on_the_perimeter(net, p.position) is not None:
            return LineProblem.ON_THE_PERIMETER
    crossings = segment_crossings(net, a.position, b.position)
    if crossings is None:
        return LineProblem.ALONG_THE_PERIMETER
    if a.on_perimeter:
        after = _on_net(net, a.position, crossings[0].position if crossings else b.position)
        if i == 0:
            if not after:
                return LineProblem.NOT_INTO_THE_NET  # e.g. leaving the net straight from where the line starts
        else:
            previous = segment_crossings(net, points[i - 1].position, a.position)
            before_from = previous[-1].position if previous else points[i - 1].position
            if previous is not None and _on_net(net, before_from, a.position) == after:
                return LineProblem.NOT_THROUGH  # touching the perimeter without going in or out
    for j, (c, d) in enumerate(pairwise(p.position for p in points)):
        if j == i:
            continue
        hit = classify_segments(a.position, b.position, c, d)
        if hit.kind is IntersectionKind.DISJOINT:
            continue
        shared = a.position if j == i - 1 else b.position if j == i + 1 else None
        if not (hit.kind is IntersectionKind.TOUCH and hit.point == shared):
            return LineProblem.TOUCHES_ITSELF
    return None


def _on_net(net: Net, a: Vec, b: Vec) -> bool:
    """Does the part a-b of the line (no cut crossed between) lie on the net?"""
    m = (a + b) / 2
    return net.contains(m) and on_the_perimeter(net, m) is None


def invalid_segments(net: Net, points: Sequence[CutPoint], indices: Iterable[int]) -> list[int]:
    """Which of the segments `indices` of the polyline `points` are invalid."""
    return [i for i in indices if 0 <= i < len(points) - 1 and not segment_valid(net, points, i)]


def segment_allowed(net: Net, line: CutLine, end: CutPoint) -> bool:
    """May the segment from the line's last point to `end` be added?"""
    return added_segment_problem(net, line, end) is None


def added_segment_problem(net: Net, line: CutLine, end: CutPoint) -> LineProblem | None:
    """The rule the segment from the line's last point to `end` would break, if any."""
    points = [*line.points, end]
    return segment_problem(net, points, len(points) - 2)
