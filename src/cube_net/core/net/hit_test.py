"""Finding the cut under the mouse (docs/plan.md, section 4.1).

A cut's hitbox lies inside the region it bounds (docs/idea.txt, note 4): a strip of width `max_distance` along the
inner side of the cut. So when two parts of the net touch along a segment, each side reaches only its own cut.
"""

from fractions import Fraction

from cube_net.core.geometry import Vec, polygon_contains
from cube_net.core.net.elements import HalfEdge
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
