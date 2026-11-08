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
