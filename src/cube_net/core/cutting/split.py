"""Splitting the net along the cut line (docs/plan.md, section 4.3).

`split_net` builds a new net in which the line has become real cuts: the perimeter is divided at the line's ends and at
their counterpart images, fold edges at the line's crossings, and each piece of the line has two sides, with vertices
of their own. The result has two separate halves and two perimeter cycles, and it satisfies the rule that every cut has
exactly two images with the same subdivision. The original net is not changed.

Vertices are created in order along the line, so the names they get later are the ones the line's preview showed.
"""

from dataclasses import dataclass
from itertools import pairwise

from cube_net.core.cube import SurfacePoint
from cube_net.core.cutting.cut_line import CutLine, CutPoint
from cube_net.core.cutting.images import counterpart_image
from cube_net.core.cutting.pieces import pieces, region_at
from cube_net.core.geometry import Vec, on_segment
from cube_net.core.net import EdgeKind, HalfEdge, Net, NetCopy, NetVertex, Region
from cube_net.core.net.surgery import add_edge, new_half_edge, new_vertex, outgoing, rotation_from, split_edge


@dataclass(frozen=True, slots=True)
class SplitNet:
    net: Net

    # The inner half-edges of the new cuts (both sides of every piece of the line).
    line_edges: frozenset[HalfEdge]

    # The other cuts whose counterpart is in the same half: choosing them can't rearrange anything.
    same_half_cuts: frozenset[HalfEdge]


def connected_regions(start: Region) -> set[Region]:
    """All regions reachable from `start` across inner edges."""
    found = {start}
    stack = [start]
    while stack:
        for he in Net.region_cycle(stack.pop()):
            other = he.twin.region
            if other is not None and other not in found:
                found.add(other)
                stack.append(other)
    return found


def split_net(net: Net, line: CutLine) -> SplitNet:
    """The net with the closed, valid cut line `line` turned into cuts."""
    copy = net.copy()
    stops = _create_stops(net, copy, line)
    forward = [_connect(copy.net, a, b) for a, b in pairwise(stops)]
    backward = [he.twin for he in forward]
    _unzip(copy.net, stops, forward)
    copy.net.reindex()
    line_edges = frozenset(forward) | frozenset(backward)
    return SplitNet(copy.net, line_edges, _same_half_cuts(copy.net, line_edges))


def _same_half_cuts(net: Net, line_edges: frozenset[HalfEdge]) -> frozenset[HalfEdge]:
    assert net.regions
    half = connected_regions(net.regions[0])  # one half is enough: there are two
    result = set()
    for he in net.boundary_edges():
        if he not in line_edges and (he.region in half) == (net.counterpart(he).region in half):
            result.add(he)
    return frozenset(result)


def _create_stops(net: Net, copy: NetCopy, line: CutLine) -> list[NetVertex]:
    """Vertices (in the copy) for everything along the line: its points and its crossings with fold edges."""
    positions = [p.position for p in line.points]
    stops: list[NetVertex] = [_endpoint_vertex(net, copy, line.points[0])]
    for segment, (a, b) in enumerate(pairwise(positions)):
        parts = pieces(net, a, b)
        for i, part in enumerate(parts):
            is_last = segment == len(positions) - 2 and i == len(parts) - 1
            if is_last:
                stops.append(_endpoint_vertex(net, copy, line.points[-1]))
            else:
                stops.append(_inner_vertex(copy.net, part.end, part.end_point))
    return stops


def _endpoint_vertex(net: Net, copy: NetCopy, point: CutPoint) -> NetVertex:
    if point.vertex is not None:
        return copy.vertices[point.vertex]
    assert point.edge is not None
    region = point.edge.region
    assert region is not None
    vertex = _vertex_on_cut(copy, point.edge, point.position, _surface_point(point.position, region))
    image = counterpart_image(net, point)
    assert image is not None
    _vertex_on_cut(copy, image.edge, image.position, image.point)
    return vertex


def _surface_point(position: Vec, region: Region) -> SurfacePoint:
    return SurfacePoint(region.face, region.placement.inverse().apply(position))


def _vertex_on_cut(copy: NetCopy, edge: HalfEdge, position: Vec, point: SurfacePoint) -> NetVertex:
    """The vertex at `position` on the original cut `edge`, which may already have been divided in the copy."""
    he = copy.edges[edge]
    while not on_segment(position, he.origin.position, he.destination.position):
        he = he.next
    for end in (he.origin, he.destination):
        if end.position == position:
            return end
    return split_edge(copy.net, he, position, point)


def _inner_vertex(net: Net, position: Vec, point: SurfacePoint) -> NetVertex:
    """The vertex for a stop inside the net: on a fold edge (dividing it), or a new free one."""
    for fold in net.fold_edges():
        if on_segment(position, fold.origin.position, fold.destination.position):
            return split_edge(net, fold, position, point)
    return new_vertex(net, position, point)


def _connect(net: Net, a: NetVertex, b: NetVertex) -> HalfEdge:
    """The half-edge a->b: an existing fold edge, if the line runs along it, or a new edge across the region."""
    if hasattr(b, "edge"):
        for he in outgoing(a):
            if he.destination is b:
                return he
    region = region_at(net, (a.position + b.position) / 2)
    assert region is not None
    return add_edge(net, a, b, region, EdgeKind.BOUNDARY)


def _unzip(net: Net, stops: list[NetVertex], forward: list[HalfEdge]) -> None:
    """Give the line two sides. The left side (of the direction along the line) keeps the stops; the right side gets
    copies of them. Every piece becomes two cuts, each with its own half-edge on the outside of the net."""
    backward = [he.twin for he in forward]
    last = len(stops) - 1
    outer_start = next(he for he in outgoing(stops[0]) if he.region is None)
    outer_end = next(he for he in outgoing(stops[last]) if he.region is None)
    into_start, into_end = outer_start.prev, outer_end.prev

    # Who goes to the right side around each stop (found before any link changes).
    right_groups: list[list[HalfEdge]] = []
    for k in range(last + 1):
        if k == 0:
            rotation = rotation_from(outer_start)
            group = rotation[1 : rotation.index(forward[0])]
        elif k == last:
            rotation = rotation_from(outer_end)
            group = [outer_end, *rotation[rotation.index(backward[-1]) :]]
        else:
            rotation = rotation_from(backward[k - 1])
            group = rotation[: rotation.index(forward[k])]
        right_groups.append(group)

    copies = [new_vertex(net, stop.position, stop.point) for stop in stops]
    for vertex, group in zip(copies, right_groups, strict=True):
        for he in group:
            he.origin = vertex

    left_outer, right_outer = [], []
    for k in range(last):
        forward[k].kind = backward[k].kind = EdgeKind.BOUNDARY
        left = new_half_edge(net, stops[k + 1], EdgeKind.BOUNDARY, None)  # runs from stop k + 1 back to stop k
        right = new_half_edge(net, copies[k], EdgeKind.BOUNDARY, None)  # runs from copy k to copy k + 1
        forward[k].twin, left.twin = left, forward[k]
        backward[k].twin, right.twin = right, backward[k]
        left_outer.append(left)
        right_outer.append(right)

    def link(a: HalfEdge, b: HalfEdge) -> None:
        a.next, b.prev = b, a

    # The left half's cycle: ... into_end -> (back along the line) -> outer_start ...
    link(into_end, left_outer[-1])
    for k in range(last - 1, 0, -1):
        link(left_outer[k], left_outer[k - 1])
    link(left_outer[0], outer_start)
    # The right half's cycle: ... into_start -> (forward along the line) -> outer_end ...
    link(into_start, right_outer[0])
    for k in range(last - 1):
        link(right_outer[k], right_outer[k + 1])
    link(right_outer[-1], outer_end)

    for k, stop in enumerate(stops):
        stop.edge = forward[k] if k < last else left_outer[-1]
    copies[0].edge = right_outer[0]
    for k in range(1, last + 1):
        copies[k].edge = backward[k - 1]
