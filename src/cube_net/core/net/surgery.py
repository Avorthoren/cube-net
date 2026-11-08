"""Local changes of the net's DCEL: new vertices, splitting an edge, adding an edge across a region.

These are building blocks: they keep the half-edge links right, but the net as a whole may be incomplete in between
(`Net.reindex()` has to be called when the whole change is done).
"""

from cube_net.core.cube import SurfacePoint
from cube_net.core.geometry import Vec
from cube_net.core.net.elements import EdgeKind, HalfEdge, NetVertex, Region
from cube_net.core.net.net import Net, _cycle


def new_vertex(net: Net, position: Vec, point: SurfacePoint) -> NetVertex:
    vertex = NetVertex(max(v.id for v in net.vertices) + 1, position, point)
    net.vertices.append(vertex)
    return vertex


def new_half_edge(net: Net, origin: NetVertex, kind: EdgeKind, region: Region | None) -> HalfEdge:
    he = HalfEdge(max(e.id for e in net.half_edges) + 1, origin, kind, region)
    net.half_edges.append(he)
    return he


def outgoing(vertex: NetVertex) -> list[HalfEdge]:
    """The half-edges leaving `vertex`, counter-clockwise, starting at `vertex.edge`."""
    return rotation_from(vertex.edge)


def rotation_from(start: HalfEdge) -> list[HalfEdge]:
    """The half-edges leaving the origin of `start`, counter-clockwise, starting at `start`."""
    edges = [start]
    he = start.prev.twin
    while he is not start:
        edges.append(he)
        he = he.prev.twin
    return edges


def split_edge(net: Net, he: HalfEdge, position: Vec, point: SurfacePoint) -> NetVertex:
    """Put a new vertex on the edge of `he`: a->b becomes a->w and w->b (on both sides of the edge)."""
    twin = he.twin
    w = new_vertex(net, position, point)
    he2 = new_half_edge(net, w, he.kind, he.region)  # w -> b, on the side of `he`
    twin2 = new_half_edge(net, w, twin.kind, twin.region)  # w -> a, on the side of `twin`
    he2.next, he2.prev = he.next, he
    he.next.prev = he2
    he.next = he2
    twin2.next, twin2.prev = twin.next, twin
    twin.next.prev = twin2
    twin.next = twin2
    he.twin, twin2.twin = twin2, he
    twin.twin, he2.twin = he2, twin
    w.edge = he2
    return w


def corner(vertex: NetVertex, region: Region) -> HalfEdge:
    """The half-edge leaving `vertex` along the boundary of `region`."""
    for he in outgoing(vertex):
        if he.region is region:
            return he
    raise ValueError(f"{vertex} is not on the boundary of {region}")


def add_edge(net: Net, a: NetVertex, b: NetVertex, region: Region, kind: EdgeKind) -> HalfEdge:
    """Add the edge a->b inside `region`; returns the half-edge a->b, with `region` or its new part on its left.

    `a` must be on the region's boundary. A brand-new `b` (no edges yet) makes a dead end inside the region. If `b` is
    on the boundary too, the edge divides the region in two: one part keeps `region`, the other is a new region.
    """
    ha = corner(a, region)
    forward = new_half_edge(net, a, kind, region)
    backward = new_half_edge(net, b, kind, region)
    forward.twin, backward.twin = backward, forward
    pa = ha.prev
    if not hasattr(b, "edge"):
        pa.next, forward.prev = forward, pa
        forward.next, backward.prev = backward, forward
        backward.next, ha.prev = ha, backward
        b.edge = backward
        return forward
    hb = corner(b, region)
    pb = hb.prev
    pa.next, forward.prev = forward, pa
    forward.next, hb.prev = hb, forward
    pb.next, backward.prev = backward, pb
    backward.next, ha.prev = ha, backward
    region.edge = forward
    part = Region(max(r.id for r in net.regions) + 1, region.face, region.placement)
    net.regions.append(part)
    part.edge = backward
    for he in _cycle(backward):
        he.region = part
    return forward


def _link(a: HalfEdge, b: HalfEdge) -> None:
    a.next, b.prev = b, a


def glue_cuts(
    net: Net, kept: HalfEdge, moved: HalfEdge
) -> tuple[tuple[HalfEdge, HalfEdge] | None, tuple[HalfEdge, HalfEdge] | None]:
    """Glue two cuts lying on each other: `kept` a->b and `moved` b->a (their ends coincide on the sheet, and may
    already be the same vertices). Their outside half-edges go away and the perimeter closes up.

    Returns, for each of the two ends (the one at `kept`'s destination first), the outside half-edges now meeting
    there: (arriving, leaving); None if the perimeter already passes through that end without a gap.
    """
    outer_kept, outer_moved = kept.twin, moved.twin
    a, b = kept.origin, kept.destination
    other_a, other_b = moved.destination, moved.origin
    for old, new in ((other_a, a), (other_b, b)):
        if old is not new:
            for he in rotation_from(old.edge):
                he.origin = new
            net.vertices.remove(old)

    in_b, out_b = outer_kept.prev, outer_moved.next
    in_a, out_a = outer_moved.prev, outer_kept.next
    end_b = None if out_b is outer_kept else (in_b, out_b)
    end_a = None if in_a is outer_kept else (in_a, out_a)
    if end_b is not None:
        _link(in_b, out_b)
    if end_a is not None:
        _link(in_a, out_a)

    on_cube_edge = len(a.point.faces & b.point.faces) == 2
    kept.kind = moved.kind = EdgeKind.FOLD if on_cube_edge else EdgeKind.SEAM
    kept.twin, moved.twin = moved, kept
    net.half_edges.remove(outer_kept)
    net.half_edges.remove(outer_moved)
    a.edge, b.edge = kept, moved
    return end_b, end_a


def remove_edge(net: Net, he: HalfEdge) -> None:
    """Remove an inner edge: the regions on its sides become one, or, if it's a dead end, its loose end goes away."""
    twin = he.twin
    keep, other = he.region, twin.region
    if keep is None or other is None:
        raise ValueError(f"{he} is not an inner edge")
    if keep is not other:
        if keep.placement != other.placement or keep.face != other.face:
            raise ValueError(f"{keep} and {other} can't become one region")
        for edge in _cycle(twin):
            edge.region = keep
        net.regions.remove(other)
    u, v = he.origin, twin.origin
    prev_he, next_he = he.prev, he.next
    prev_twin, next_twin = twin.prev, twin.next
    if next_twin is he:
        net.vertices.remove(u)
    else:
        _link(prev_he, next_twin)
        u.edge = next_twin
    if next_he is twin:
        net.vertices.remove(v)
    else:
        _link(prev_twin, next_he)
        v.edge = next_he
    keep.edge = next(e for e in (next_he, next_twin, prev_he, prev_twin) if e is not he and e is not twin)
    net.half_edges.remove(he)
    net.half_edges.remove(twin)


def dissolve_vertex(net: Net, vertex: NetVertex) -> None:
    """Remove a vertex with exactly two edges, joining them into one (u->v, v->w become u->w, on both sides)."""
    edges = outgoing(vertex)
    if len(edges) != 2:
        raise ValueError(f"{vertex} has {len(edges)} edges, expected 2")
    he2, twin1 = edges
    he1, twin2 = he2.prev, twin1.prev
    _link(he1, he2.next)
    _link(twin2, twin1.next)
    he1.twin, twin2.twin = twin2, he1
    if he2.region is not None and he2.region.edge is he2:
        he2.region.edge = he1
    if twin1.region is not None and twin1.region.edge is twin1:
        twin1.region.edge = twin2
    net.half_edges.remove(he2)
    net.half_edges.remove(twin1)
    net.vertices.remove(vertex)
