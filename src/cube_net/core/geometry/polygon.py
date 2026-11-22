# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exact helpers for simple polygons given as vertex lists (no repeated closing vertex)."""

from collections.abc import Iterable, Sequence
from fractions import Fraction

from cube_net.core.geometry.predicates import on_segment
from cube_net.core.geometry.vec import Vec


def signed_area(polygon: Sequence[Vec]) -> Fraction:
    """Shoelace formula: positive for counter-clockwise polygons, negative for clockwise ones."""
    n = len(polygon)
    twice = sum((polygon[i].cross(polygon[(i + 1) % n]) for i in range(n)), Fraction(0))
    return twice / 2


def polygon_centroid(polygon: Sequence[Vec]) -> tuple[Vec, Fraction] | None:
    """The polygon's centre of mass (uniform density) and its area, positive whichever way it runs (exact); None if it
    has no area. A slit (the polygon going along a part and back) weighs nothing."""
    n = len(polygon)
    twice = x = y = Fraction(0)
    for i in range(n):
        a, b = polygon[i], polygon[(i + 1) % n]
        cross = a.cross(b)
        twice += cross
        x += (a.x + b.x) * cross
        y += (a.y + b.y) * cross
    if twice == 0:
        return None
    return Vec(x / (3 * twice), y / (3 * twice)), abs(twice) / 2


def area_centroid(solids: Iterable[Sequence[Vec]], holes: Iterable[Sequence[Vec]] = ()) -> Vec | None:
    """The centre of mass of the paper the `solids` cover, without the `holes` (inside them, not overlapping each
    other), of uniform density (exact): the solids' moments (centre times area) and areas, minus the holes'. Every
    area is taken positive, so the way a loop runs doesn't matter. None if no area is left."""
    moment = Vec(0, 0)
    area = Fraction(0)
    for loops, sign in ((solids, 1), (holes, -1)):
        for loop in loops:
            found = polygon_centroid(loop)
            if found is not None:
                center, loop_area = found
                moment = moment + center * (sign * loop_area)
                area += sign * loop_area
    if area == 0:
        return None
    return moment / area


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


def loops_contain(loops: Sequence[Sequence[Vec]], p: Vec) -> bool:
    """True if `p` is inside the region the loops bound (an outer one and holes inside it), or on one of them (exact;
    even-odd rule over all their sides)."""
    inside = False
    for loop in loops:
        n = len(loop)
        for i in range(n):
            a, b = loop[i], loop[(i + 1) % n]
            if on_segment(p, a, b):
                return True
            if (a.y > p.y) != (b.y > p.y):
                x_cross = a.x + (p.y - a.y) * (b.x - a.x) / (b.y - a.y)
                if p.x < x_cross:
                    inside = not inside
    return inside
