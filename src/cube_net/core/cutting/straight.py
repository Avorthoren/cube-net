"""Straight segments: what holding SHIFT does to a segment of the cut line (docs/idea.txt).

The segment from an anchor point goes horizontally or vertically, whichever is closer to the mouse. Snapping must keep
it that way, so what it snaps to is where its line crosses a cut or a fold, not the closest point of them.
"""

from __future__ import annotations

from fractions import Fraction

from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, Net


def straighten(anchor: Vec, p: Vec) -> Vec:
    """The point of the horizontal or the vertical through `anchor` closest to `p` (horizontal if it's a tie)."""
    d = p - anchor
    return Vec(p.x, anchor.y) if abs(d.x) >= abs(d.y) else Vec(anchor.x, p.y)


def line_meets_segment(anchor: Vec, through: Vec, a: Vec, b: Vec) -> Vec | None:
    """Where the line through `anchor` and `through` meets segment a-b, or None. If the line runs along the segment,
    it's `through`, if that's on the segment."""
    d = through - anchor
    e = b - a
    denominator = d.cross(e)
    if denominator == 0:
        collinear = d != Vec(0, 0) and (a - anchor).cross(d) == 0
        return through if collinear and (through - a).dot(through - b) <= 0 else None
    u = (a - anchor).cross(d) / denominator
    if not 0 <= u <= 1:
        return None
    return anchor + d * ((a - anchor).cross(e) / denominator)


def closest_straight_point(net: Net, anchor: Vec, p: Vec) -> tuple[Vec, HalfEdge] | None:
    """The point of the perimeter closest to `p` that is straight from `anchor`, with its cut (cuts running along the
    line don't count: a segment can't go along them). None if there's no such point."""
    best: tuple[Fraction, int] | None = None
    result: tuple[Vec, HalfEdge] | None = None
    for cut in net.boundary_edges():
        a, b = cut.origin.position, cut.destination.position
        for through in (anchor + Vec(1, 0), anchor + Vec(0, 1)):
            if (through - anchor).cross(b - a) == 0:
                continue
            hit = line_meets_segment(anchor, through, a, b)
            if hit is None or hit == anchor:
                continue
            key = ((hit - p).length_squared(), cut.id)
            if best is None or key < best:
                best, result = key, (hit, cut)
    return result
