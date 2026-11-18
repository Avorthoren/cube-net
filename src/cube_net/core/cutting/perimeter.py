# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Where the cut line meets the perimeter: a point on it, and the cuts a segment crosses (docs/template_plan.md,
§8.2)."""

from fractions import Fraction
from math import ceil

from cube_net.core.cutting.cut_line import CutPoint
from cube_net.core.geometry import IntersectionKind, Vec, classify_segments, on_segment
from cube_net.core.net import HalfEdge, Net

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


def on_the_perimeter(net: Net, p: Vec) -> HalfEdge | None:
    """A cut `p` lies on, if any."""
    return next((he for he in net.boundary_edges() if on_segment(p, he.origin.position, he.destination.position)), None)


def segment_crossings(net: Net, a: Vec, b: Vec) -> list[CutPoint] | None:
    """Where the segment a-b crosses cuts (properly: not at a vertex of the perimeter), in order from a, each a point
    on its cut. None if it touches the perimeter anywhere else than at a or b, runs along it, or crosses two cuts at one
    point (a slit: it would leave the net and come back at once)."""
    if a == b:
        return []
    found: list[tuple[Vec, HalfEdge]] = []
    for he in net.boundary_edges():
        hit = classify_segments(a, b, he.origin.position, he.destination.position)
        if hit.kind is IntersectionKind.DISJOINT:
            continue
        if hit.kind is IntersectionKind.CROSSING:
            found.append((hit.point, he))
            continue
        if hit.kind is IntersectionKind.TOUCH and hit.point in (a, b):
            continue  # the segment's own end: whether it may be there is the point's business
        return None
    exact = [p for p, _ in found]
    if len(set(exact)) != len(exact):
        return None
    d = b - a
    found.sort(key=lambda item: (item[0] - a).dot(d))
    return [CutPoint(project_onto(he, p), he) for p, he in found]
