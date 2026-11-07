"""Validity rules of the cut line (docs/idea.txt, CUTTING state; docs/plan.md, section 4.2).

The cut line must lie strictly inside the net, except for its first and last points, which lie on the perimeter. So a
new segment a-b may touch the perimeter only at a or b, and only if that end is on the perimeter; it may touch the
cut line only at a, where it continues the previous segment.
"""

from fractions import Fraction

from cube_net.core.cutting.cut_line import CutLine, CutPoint
from cube_net.core.geometry import IntersectionKind, Vec, classify_segments, on_segment
from cube_net.core.net import HalfEdge, Net

# At most this many points after the first one (docs/idea.txt).
MAX_POINTS_AFTER_FIRST = 50


def project_onto(edge: HalfEdge, p: Vec) -> Vec:
    """The point of the cut `edge` closest to `p` (exact; the ends of the cut included)."""
    a, b = edge.origin.position, edge.destination.position
    d = b - a
    t = (p - a).dot(d) / d.length_squared()
    return a + d * min(max(t, Fraction(0)), Fraction(1))


def strictly_inside(net: Net, p: Vec) -> bool:
    """`p` is on the net but not on its perimeter (folds inside the net are fine)."""
    if not net.contains(p):
        return False
    return not any(on_segment(p, he.origin.position, he.destination.position) for he in net.boundary_edges())


def segment_allowed(net: Net, line: CutLine, end: CutPoint) -> bool:
    """May the segment from the line's last point to `end` be added?"""
    a, b = line.last, end
    if a.position == b.position:
        return False
    if not b.on_perimeter and not strictly_inside(net, b.position):
        return False
    if not strictly_inside(net, (a.position + b.position) / 2):
        return False  # e.g. leaving the net straight from the starting point
    for he in net.boundary_edges():
        hit = classify_segments(a.position, b.position, he.origin.position, he.destination.position)
        if hit.kind is IntersectionKind.DISJOINT:
            continue
        if hit.kind is not IntersectionKind.TOUCH:
            return False
        touch = hit.point
        if not ((touch == a.position and a.on_perimeter) or (touch == b.position and b.on_perimeter)):
            return False
    segments = line.segments()
    for i, (c, d) in enumerate(segments):
        hit = classify_segments(a.position, b.position, c, d)
        if hit.kind is IntersectionKind.DISJOINT:
            continue
        continues_previous = i == len(segments) - 1 and hit.kind is IntersectionKind.TOUCH and hit.point == a.position
        if not continues_previous:
            return False
    return True
