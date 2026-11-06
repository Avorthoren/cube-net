"""Exact helpers for simple polygons given as vertex lists (no repeated closing vertex)."""

from collections.abc import Sequence
from fractions import Fraction

from cube_net.core.geometry.predicates import on_segment
from cube_net.core.geometry.vec import Vec


def signed_area(polygon: Sequence[Vec]) -> Fraction:
    """Shoelace formula: positive for counter-clockwise polygons, negative for clockwise ones."""
    n = len(polygon)
    twice = sum((polygon[i].cross(polygon[(i + 1) % n]) for i in range(n)), Fraction(0))
    return twice / 2


def polygon_contains(polygon: Sequence[Vec], p: Vec) -> bool:
    """True if `p` is inside the polygon or on its boundary (exact; even-odd rule)."""
    n = len(polygon)
    inside = False
    for i in range(n):
        a, b = polygon[i], polygon[(i + 1) % n]
        if on_segment(p, a, b):
            return True
        if (a.y > p.y) != (b.y > p.y):
            # x of the edge at the height of p (exact, no rounding)
            x_cross = a.x + (p.y - a.y) * (b.x - a.x) / (b.y - a.y)
            if p.x < x_cross:
                inside = not inside
    return inside
