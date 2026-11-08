"""Exact geometric predicates: orientation and segment-segment classification (docs/plan.md, section 3.1).

Every validity rule of the application (cut line strictly inside the net, perimeter overlap check, ...) is built on
`classify_segments`, so it must be exact and must handle all degenerate configurations explicitly.
Segments are given by their endpoints and are treated as closed (endpoints included).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from cube_net.core.geometry.vec import Vec


def orient(a: Vec, b: Vec, c: Vec) -> int:
    """Orientation of the triple: 1 if a->b->c turns counter-clockwise, -1 if clockwise, 0 if collinear."""
    cross = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
    return (cross > 0) - (cross < 0)


def on_segment(p: Vec, a: Vec, b: Vec) -> bool:
    """True if `p` lies on the closed segment a-b (works for a degenerate segment a == b too)."""
    # The bounding box first: it rules out most points, for much less than the orientation costs.
    in_box = min(a.x, b.x) <= p.x <= max(a.x, b.x) and min(a.y, b.y) <= p.y <= max(a.y, b.y)
    return in_box and orient(a, b, p) == 0


class IntersectionKind(Enum):
    # No common points.
    DISJOINT = "disjoint"

    # Exactly one common point, lying strictly inside both segments (a proper crossing).
    CROSSING = "crossing"

    # Exactly one common point, which is an endpoint of at least one segment (endpoint-endpoint or T-touch).
    TOUCH = "touch"

    # Collinear segments sharing a sub-segment of positive length.
    OVERLAP = "overlap"


@dataclass(frozen=True, slots=True)
class SegmentIntersection:
    """Result of `classify_segments`.

    `points` is empty for DISJOINT, holds the single common point for CROSSING/TOUCH, and holds the two ends of the
    common sub-segment for OVERLAP (ordered along the direction of the first segment).
    """

    kind: IntersectionKind
    points: tuple[Vec, ...] = ()

    @property
    def point(self) -> Vec:
        """The single common point of a CROSSING or TOUCH."""
        if len(self.points) != 1:
            raise ValueError(f"{self.kind.name} has no single common point")
        return self.points[0]


_DISJOINT = SegmentIntersection(IntersectionKind.DISJOINT)


def classify_segments(p1: Vec, p2: Vec, q1: Vec, q2: Vec) -> SegmentIntersection:
    """Classify how closed segments p1-p2 and q1-q2 intersect. Both segments must have positive length."""
    r = p2 - p1
    s = q2 - q1
    if r.is_zero() or s.is_zero():
        raise ValueError("degenerate (zero-length) segment")

    denominator = r.cross(s)
    offset = q1 - p1

    if denominator == 0:
        if offset.cross(r) != 0:
            return _DISJOINT  # parallel, on different lines
        return _classify_collinear(p1, r, q1, q2)

    # Lines intersect at p1 + t*r == q1 + u*s.
    t = offset.cross(s) / denominator

    u = offset.cross(r) / denominator
    if not (0 <= t <= 1 and 0 <= u <= 1):
        return _DISJOINT
    point = p1 + r * t
    kind = IntersectionKind.CROSSING if 0 < t < 1 and 0 < u < 1 else IntersectionKind.TOUCH
    return SegmentIntersection(kind, (point,))


def _classify_collinear(p1: Vec, r: Vec, q1: Vec, q2: Vec) -> SegmentIntersection:
    """Both segments lie on one line. Work with parameters along the first segment: p1 -> 0, p2 -> 1."""
    rr = r.dot(r)
    tq1 = (q1 - p1).dot(r) / rr
    tq2 = (q2 - p1).dot(r) / rr
    lo: Fraction = max(min(tq1, tq2), Fraction(0))
    hi: Fraction = min(max(tq1, tq2), Fraction(1))
    if lo > hi:
        return _DISJOINT
    if lo == hi:
        return SegmentIntersection(IntersectionKind.TOUCH, (p1 + r * lo,))
    return SegmentIntersection(IntersectionKind.OVERLAP, (p1 + r * lo, p1 + r * hi))
