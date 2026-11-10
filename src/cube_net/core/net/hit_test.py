# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Finding the cut, the perimeter vertex or the fold line under the mouse (docs/plan.md, section 4.1).

A cut's hitbox lies inside the region it bounds (docs/idea.txt, note 4): a strip of width `max_distance` along the
inner side of the cut. So when two parts of the net touch along a segment, each side reaches only its own cut.
"""

from fractions import Fraction

from cube_net.core.geometry import Vec, polygon_contains
from cube_net.core.net.elements import HalfEdge, NetVertex
from cube_net.core.net.net import Net


def boundary_edge_at(net: Net, p: Vec, max_distance: Fraction) -> HalfEdge | None:
    """The cut (inner half-edge of a perimeter segment) whose hitbox contains `p`, or None.

    `p` must lie inside the cut's region, at most `max_distance` from the cut, and its projection onto the cut's line
    must fall within the cut. If several hitboxes contain `p` (near a corner), the closest cut wins; ties go to the
    lower id, so the result is deterministic.
    """
    best: tuple[Fraction, int, HalfEdge] | None = None
    limit = max_distance * max_distance
    for he in net.boundary_edges():
        a, b = he.origin.position, he.destination.position
        d = b - a
        length2 = d.length_squared()
        offset = p - a
        side = d.cross(offset)  # > 0: p is on the left of a->b, the region's side
        if side < 0:
            continue
        t = offset.dot(d)
        if t < 0 or t > length2:
            continue
        distance2 = side * side / length2
        if distance2 > limit:
            continue
        if best is not None and (distance2, he.id) >= best[:2]:
            continue
        region = he.region
        if region is None or not polygon_contains(net.region_polygon(region), p):
            continue
        best = (distance2, he.id, he)
    return None if best is None else best[2]


def boundary_vertex_at(net: Net, p: Vec, radius: Fraction) -> NetVertex | None:
    """The perimeter vertex whose circle (of `radius` units) contains `p`, or None. The closest one wins; ties go to
    the lower id."""
    best: tuple[Fraction, int, NetVertex] | None = None
    limit = radius * radius
    for vertex in net.boundary_vertices():
        distance2 = (vertex.position - p).length_squared()
        if distance2 <= limit and (best is None or (distance2, vertex.id) < best[:2]):
            best = (distance2, vertex.id, vertex)
    return None if best is None else best[2]


def boundary_edge_from(net: Net, vertex: NetVertex) -> HalfEdge:
    """A cut that starts at perimeter vertex `vertex` (the inner half-edge leaving it along the perimeter)."""
    for he in net.boundary_edges():
        if he.origin is vertex:
            return he
    raise ValueError(f"{vertex} is not on the perimeter")


def fold_edge_at(net: Net, p: Vec, half_width: Fraction, prefer: HalfEdge | None = None) -> HalfEdge | None:
    """The fold whose hitbox contains `p`, or None. A fold's hitbox is a strip centered on it, like the line drawn for
    it: `half_width` to each side, and not beyond its ends. The closest fold wins (ties: the lower id), except that
    `prefer` keeps winning for as long as `p` is in its hitbox: a point on a fold stays there until it leaves it.
    """
    best: tuple[Fraction, int, HalfEdge] | None = None
    limit = half_width * half_width
    for he in net.fold_edges():
        a, b = he.origin.position, he.destination.position
        d = b - a
        length2 = d.length_squared()
        offset = p - a
        t = offset.dot(d)
        if t < 0 or t > length2:
            continue
        side = d.cross(offset)
        distance2 = side * side / length2
        if distance2 > limit:
            continue
        if he is prefer:
            return he
        if best is None or (distance2, he.id) < best[:2]:
            best = (distance2, he.id, he)
    return None if best is None else best[2]
