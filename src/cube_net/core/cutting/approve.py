"""Approving a rearrangement: gluing the halves for good (docs/idea.txt note 5 and 6; docs/plan.md, section 4.6).

1. The chosen cut is glued with its counterpart.
2. From both of its ends the gluing goes on along the perimeter, while the next two cuts are images of the same part
   of the cube and lie on each other. It stops at the first pair that doesn't match.
3. Cleanup. Cuts glued inside a cube face leave nothing behind: such seams disappear, and the regions on their sides
   become one. Vertices left inside the net disappear. So do points of the perimeter that no longer mean anything: where
   at all their images the perimeter goes straight on, between cuts of the same colours.
"""

from cube_net.core.cube import SurfacePoint
from cube_net.core.cutting.rearrange import Rearranged
from cube_net.core.geometry import orient
from cube_net.core.net import EdgeKind, HalfEdge, Net, NetVertex
from cube_net.core.net.surgery import dissolve_vertex, glue_cuts, outgoing, remove_edge
from cube_net.core.net.validate import validate_net


def approve(rearranged: Rearranged) -> Net:
    """The new net (`rearranged` itself stays as it is). Must be a valid rearrangement."""
    if not rearranged.valid:
        raise ValueError("a rearrangement with overlapping halves can't be approved")
    copy = rearranged.net.copy()
    net = copy.net
    end_b, end_a = glue_cuts(net, copy.edges[rearranged.kept], copy.edges[rearranged.moved])
    for end in (end_b, end_a):
        if end is not None:
            _zip(net, *end)
    _dissolve_seams(net)
    _remove_inner_vertices(net)
    _remove_redundant_points(net)
    net.reindex()
    validate_net(net)
    return net


def _zip(net: Net, arriving: HalfEdge, leaving: HalfEdge) -> None:
    """Keep gluing where two outside half-edges meet at a vertex, while they run along the same part of the cube."""
    while arriving in net.half_edges and leaving in net.half_edges:
        far_a, far_b = arriving.origin, leaving.destination
        if far_a is far_b or far_a.point != far_b.point or far_a.position != far_b.position:
            return
        end_b, _ = glue_cuts(net, arriving.twin, leaving.twin)
        if end_b is None:
            return
        arriving, leaving = end_b


def _dissolve_seams(net: Net) -> None:
    while True:
        seams = [he for he in net.half_edges if he.kind is EdgeKind.SEAM]
        if not seams:
            return
        for he in seams:
            # Between two regions, or a dead end. Anything else becomes one of these as the others are removed.
            if he.region is not he.twin.region or he.next is he.twin or he.twin.next is he:
                remove_edge(net, he)
                break
        else:
            raise RuntimeError("seams that can't be removed: the net is inconsistent")


def _remove_inner_vertices(net: Net) -> None:
    on_perimeter = {he.origin for he in net.half_edges if he.region is None}
    for vertex in [v for v in net.vertices if v not in on_perimeter]:
        dissolve_vertex(net, vertex)


def _remove_redundant_points(net: Net) -> None:
    images: dict[SurfacePoint, list[NetVertex]] = {}
    for vertex in net.vertices:
        images.setdefault(vertex.point, []).append(vertex)
    for point, vertices in images.items():
        if point.vertex is None and all(is_straight_through(v) for v in vertices):
            for vertex in vertices:
                dissolve_vertex(net, vertex)


def is_straight_through(vertex: NetVertex) -> bool:
    """Does the perimeter just pass through this vertex, in a straight line, with the same colours on both sides?"""
    edges = outgoing(vertex)
    if len(edges) != 2:
        return False
    u, w = edges[0].destination, edges[1].destination
    p = vertex.position
    straight = orient(u.position, p, w.position) == 0 and (u.position - p).dot(w.position - p) < 0
    return straight and (u.point.faces & vertex.point.faces) == (w.point.faces & vertex.point.faces)
