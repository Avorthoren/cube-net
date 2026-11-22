# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Approving a rearrangement: gluing the halves for good (docs/idea.txt note 5 and 6; docs/plan.md, section 4.6).

1. The chosen cut is glued with its counterpart.
2. From both of its ends the gluing goes on along the perimeter, while the next two cuts are images of the same part
   of the cube and lie on each other. It stops at the first pair that doesn't match.
3. Any other two cuts that are images of the same part of the body and lie on each other are glued too (and the gluing
   goes on from their ends): a net may get a hole that way (docs/template_plan.md §8.2).
4. Cleanup. Cuts glued inside a cube face leave nothing behind: such seams disappear, and the regions on their sides
   become one; a seam with one region on both sides (it would make the region a ring) stays, unseen. Vertices left
   inside the net disappear. So do points of the perimeter that no longer mean anything: where at all their images the
   perimeter goes straight on, between cuts of the same colours.
"""

import math

from cube_net.core.body import SurfacePoint
from cube_net.core.cutting.rearrange import Rearranged
from cube_net.core.geometry import IntersectionKind, Vec, classify_segments, orient
from cube_net.core.net import EdgeKind, HalfEdge, Net, NetVertex, Region
from cube_net.core.net.surgery import add_edge, dissolve_vertex, glue_cuts, outgoing, remove_edge
from cube_net.core.net.validate import validate_net


def approve(rearranged: Rearranged) -> Net:
    """The new net (`rearranged` itself stays as it is). Must be a valid rearrangement."""
    if not rearranged.valid:
        raise ValueError("a rearrangement with overlapping halves can't be approved")
    copy = rearranged.net.copy()
    net = copy.net
    _glue(net, copy.edges[rearranged.kept], copy.edges[rearranged.moved])
    while (pair := _lying_on_each_other(net)) is not None:
        _glue(net, *pair)
    _dissolve_seams(net)
    _move_seam_ends(net)
    _remove_inner_vertices(net)
    _remove_redundant_points(net)
    net.reindex()
    validate_net(net)
    return net


def _glue(net: Net, kept: HalfEdge, moved: HalfEdge) -> None:
    """Glue the two cuts, and go on from their ends."""
    end_b, end_a = glue_cuts(net, kept, moved)
    for end in (end_b, end_a):
        if end is not None:
            _zip(net, *end)


def _lying_on_each_other(net: Net) -> tuple[HalfEdge, HalfEdge] | None:
    """Two cuts, images of the same part of the body, lying on each other, if there are any."""
    net.reindex()
    for he in net.boundary_edges():
        other = net.counterpart(he)
        if (
            other is not he
            and he.origin.position == other.destination.position
            and he.destination.position == other.origin.position
        ):
            return he, other
    return None


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
            # Between two regions, or a dead end. A seam with one region on both sides that isn't a dead end stays:
            # without it, the region would be a ring.
            if he.region is not he.twin.region or he.next is he.twin or he.twin.next is he:
                remove_edge(net, he)
                break
        else:
            return


def _move_seam_ends(net: Net) -> None:
    """A seam that stays (it keeps a face with a hole from being a ring) may end at a point inside the net that isn't
    a vertex of the body, where other edges meet: where a cut was glued, on a fold (the seam from a corner of the hole
    to the cut's end). That end is moved to a vertex of the body or of the perimeter the seam's other end can see
    across the face, the nearest one, so that the point can go (`_remove_inner_vertices`)."""
    on_perimeter = {he.origin for he in net.half_edges if he.region is None}
    for vertex in [v for v in net.vertices if v not in on_perimeter and v.point.vertex is None]:
        if len(outgoing(vertex)) == 2:
            continue  # (a straight line through it, seam or fold: it can go as it is)
        for seam in [he for he in outgoing(vertex) if he.kind is EdgeKind.SEAM]:
            region = seam.region
            assert region is not None
            start = seam.destination
            ends = {
                he.origin
                for he in Net.region_cycle(region)
                if he.origin is not start and (he.origin in on_perimeter or he.origin.point.vertex is not None)
            }
            seen = [end for end in ends if _sees(net, start, end, region)]
            if not seen:
                continue  # (the net isn't valid: validation says so)
            end = min(seen, key=lambda v: ((v.position - vertex.position).length_squared(), v.id))
            add_edge(net, start, end, region, EdgeKind.SEAM)  # the region in two parts, for a moment
            remove_edge(net, seam)  # one again


def _sees(net: Net, a: NetVertex, b: NetVertex, region: Region) -> bool:
    """Can `a` and `b` be joined by a straight seam inside `region`: leaving each of them inside one of its corners in
    the region (as `add_edge` joins them), and meeting nothing else on the way? Other edges may touch the seam's ends
    (another vertex at the same place: the other side of a cut through it)."""
    p, q = a.position, b.position
    if p == q or not (_opens_toward(a, region, q) and _opens_toward(b, region, p)):
        return False
    for he in net.half_edges:
        u, v = he.origin.position, he.destination.position
        if he.id > he.twin.id or u == v:
            continue  # (each edge once)
        meeting = classify_segments(p, q, u, v)
        if meeting.kind is IntersectionKind.DISJOINT:
            continue
        if meeting.kind is not IntersectionKind.TOUCH or meeting.point not in (p, q):
            return False
    return True


def _opens_toward(vertex: NetVertex, region: Region, toward: Vec) -> bool:
    """Does a corner of `region` at `vertex` hold the direction to `toward`, strictly inside it?"""
    p = vertex.position

    def angle(v: Vec) -> float:
        return math.atan2(float(v.y), float(v.x))

    for he in outgoing(vertex):
        if he.region is not region:
            continue
        out, back = angle(he.destination.position - p), angle(he.prev.origin.position - p)
        span = (back - out) % (2 * math.pi) or 2 * math.pi
        turn = (angle(toward - p) - out) % (2 * math.pi)
        if 0 < turn < span:
            return True
    return False


def _remove_inner_vertices(net: Net) -> None:
    """Remove the points inside the net that aren't vertices of the body (a vertex of the body where the surface is
    flat can end up inside the net; it stays)."""
    on_perimeter = {he.origin for he in net.half_edges if he.region is None}
    for vertex in [v for v in net.vertices if v not in on_perimeter and v.point.vertex is None]:
        dissolve_vertex(net, vertex)


def _remove_redundant_points(net: Net) -> None:
    images: dict[SurfacePoint, list[NetVertex]] = {}
    for vertex in net.vertices:
        images.setdefault(vertex.point, []).append(vertex)
    for point, vertices in images.items():
        if point.vertex is None and all(is_straight_through(net, v) for v in vertices):
            for vertex in vertices:
                dissolve_vertex(net, vertex)


def is_straight_through(net: Net, vertex: NetVertex) -> bool:
    """Does the perimeter just pass through this vertex, in a straight line, with the same colours on both sides?"""
    edges = outgoing(vertex)
    if len(edges) != 2:
        return False
    u, w = edges[0].destination, edges[1].destination
    p = vertex.position
    straight = orient(u.position, p, w.position) == 0 and (u.position - p).dot(w.position - p) < 0
    return straight and net.segment_faces(edges[0]) == net.segment_faces(edges[1])
