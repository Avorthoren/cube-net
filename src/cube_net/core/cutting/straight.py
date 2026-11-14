# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Straight segments: what holding SHIFT, or a locked slope, does to a segment of the cut line (docs/idea.txt).

With SHIFT, the segment from an anchor point goes horizontally or vertically, whichever is closer to the mouse; with
a locked slope (right click -> Set slope), along that slope. Snapping must keep it that way, so what it snaps to is
where its line crosses a cut or a fold, not the closest point of them.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd, lcm

from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, Net


def straighten(anchor: Vec, p: Vec) -> Vec:
    """The point of the horizontal or the vertical through `anchor` closest to `p` (horizontal if it's a tie)."""
    d = p - anchor
    return Vec(p.x, anchor.y) if abs(d.x) >= abs(d.y) else Vec(anchor.x, p.y)


def along(anchor: Vec, direction: Vec, p: Vec) -> Vec:
    """The point of the line through `anchor` going `direction` (not zero) closest to `p`."""
    return anchor + direction * ((p - anchor).dot(direction) / direction.length_squared())


def slope_of(direction: Vec) -> tuple[int, int]:
    """A direction (not zero) as the smallest integers (y, x) going the same way or the opposite one, with x >= 0
    (and y > 0 if x is 0: vertical)."""
    scale = lcm(direction.x.denominator, direction.y.denominator)
    x, y = int(direction.x * scale), int(direction.y * scale)
    common = gcd(x, y)
    x, y = x // common, y // common
    if x < 0 or (x == 0 and y < 0):
        x, y = -x, -y
    return y, x


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


def closest_straight_point(net: Net, anchor: Vec, p: Vec, direction: Vec | None = None) -> tuple[Vec, HalfEdge] | None:
    """The point of the perimeter closest to `p` that is straight from `anchor` (horizontally or vertically; or going
    `direction`, if given), with its cut (cuts running along the line don't count: a segment can't go along them).
    None if there's no such point."""
    best: tuple[Fraction, int] | None = None
    result: tuple[Vec, HalfEdge] | None = None
    directions = (Vec(1, 0), Vec(0, 1)) if direction is None else (direction,)
    for cut in net.boundary_edges():
        a, b = cut.origin.position, cut.destination.position
        for through in (anchor + d for d in directions):
            if (through - anchor).cross(b - a) == 0:
                continue
            hit = line_meets_segment(anchor, through, a, b)
            if hit is None or hit == anchor:
                continue
            key = ((hit - p).length_squared(), cut.id)
            if best is None or key < best:
                best, result = key, (hit, cut)
    return result
