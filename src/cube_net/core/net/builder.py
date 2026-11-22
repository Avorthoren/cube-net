# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`build_net()`: assemble a `Net` from region polygons (used for the default net and in tests).

All consistency checks of the input happen here, once, with readable `NetBuildError`s.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction

from cube_net.core.body import Body, Face, SurfacePoint
from cube_net.core.geometry import Rigid90, Vec, signed_area
from cube_net.core.net.elements import EdgeKind, HalfEdge, NetVertex, Region
from cube_net.core.net.net import Net


class NetBuildError(ValueError):
    """The region polygons given to `build_net()` don't form a valid net."""


@dataclass(frozen=True, slots=True)
class RegionSpec:
    face: Face

    # Face-local frame -> sheet.
    placement: Rigid90

    # Sheet positions of the region's corners, counter-clockwise.
    corners: Sequence[Vec]


def build_net(body: Body, specs: Iterable[RegionSpec]) -> Net:
    """Build a net of `body`. Corners at the same sheet position that are the same point of the body become one vertex;
    other points of the body there are other vertices (a net that touches itself, docs/template_plan.md §8.1). Sides
    shared by two regions become inner edges (FOLD on an edge of the body, SEAM otherwise); all other sides become the
    perimeter, which may pass through a vertex more than once."""
    vertices: dict[tuple[Vec, SurfacePoint], NetVertex] = {}
    half_edges: list[HalfEdge] = []
    regions: list[Region] = []
    by_side: dict[tuple[NetVertex, NetVertex], HalfEdge] = {}

    for spec in specs:
        corners = list(spec.corners)
        if len(corners) < 3:
            raise NetBuildError(f"region of face {spec.face} needs at least 3 corners, got {len(corners)}")
        if signed_area(corners) <= 0:
            raise NetBuildError(f"corners of the region of face {spec.face} must be counter-clockwise: {corners}")
        region = Region(len(regions), spec.face, spec.placement)
        regions.append(region)
        to_local = spec.placement.inverse()
        cycle: list[HalfEdge] = []
        for position in corners:
            point = SurfacePoint(body, spec.face, to_local.apply(position))
            vertex = vertices.get((position, point))
            if vertex is None:
                vertex = vertices[(position, point)] = NetVertex(len(vertices), position, point)
            he = HalfEdge(len(half_edges), vertex, EdgeKind.BOUNDARY, region)
            half_edges.append(he)
            cycle.append(he)
        for i, he in enumerate(cycle):
            he.next = cycle[(i + 1) % len(cycle)]
            he.prev = cycle[i - 1]
            side = (he.origin, he.next.origin)
            if side in by_side:
                raise NetBuildError(f"regions overlap along {side[0].position} -> {side[1].position}")
            by_side[side] = he
            he.origin.edge = he
        region.edge = cycle[0]

    outside: list[HalfEdge] = []
    paired: set[HalfEdge] = set()
    for (a, b), he in by_side.items():
        if he in paired:
            continue
        mate = by_side.get((b, a))
        if mate is not None:
            paired.add(mate)
            inside = he.region
            assert inside is not None  # every side in by_side belongs to a region
            frame = inside.placement.inverse()
            on_edge = body.edge_through(inside.face, frame.apply(a.position), frame.apply(b.position))
            he.kind = mate.kind = EdgeKind.FOLD if on_edge is not None else EdgeKind.SEAM
            he.twin, mate.twin = mate, he
            continue
        out = HalfEdge(len(half_edges), b, EdgeKind.BOUNDARY, None)
        half_edges.append(out)
        he.twin, out.twin = out, he
        outside.append(out)

    leaving: dict[NetVertex, list[HalfEdge]] = {}
    for he in half_edges:
        leaving.setdefault(he.origin, []).append(he)
    followed: set[HalfEdge] = set()
    for out in outside:
        nxt = _turn(out, leaving[out.destination])
        if nxt.region is not None or nxt in followed:
            raise NetBuildError(f"perimeter is broken at {out.destination.position}")
        followed.add(nxt)
        out.next, nxt.prev = nxt, out

    net = Net(body, vertices.values(), half_edges, regions)
    if sum(len(cycle) for cycle in net.perimeters()) != len(outside):
        raise NetBuildError("the net's perimeter is broken")
    if len(net.perimeters()) > 1 and not _connected(net):
        raise NetBuildError("the net must be connected (it may have holes)")
    return net


def _turn(arriving: HalfEdge, leaving: list[HalfEdge]) -> HalfEdge:
    """The half-edge that follows `arriving` around the face on its left: of those leaving its destination, the first
    one clockwise from the way back (`arriving.twin`). Where the perimeter passes a vertex more than once, that keeps
    each pass with its own part of the net.

    At the tip of a slit, the perimeter goes back the way it came: a half-edge leaving the same way as `back` lies
    right after it if it's on the perimeter (between them is the slit, outside the net, as on `back`'s right), and a
    full turn later if a region is on its left (as on `back`'s: they can't be right next to each other)."""
    back = arriving.twin
    at = back.origin.position
    d0 = back.destination.position - at

    def clockwise(he: HalfEdge) -> tuple[int, Fraction]:
        """Sorts by the angle clockwise from `d0`, exactly: which half of the turn, then a ratio that grows with it."""
        d = he.destination.position - at
        x, y = d.dot(d0), d0.cross(d)  # y < 0: within half a turn clockwise of d0
        if y < 0:
            return 0, x / y
        if y == 0 and x < 0:
            return 1, Fraction(0)
        if y > 0:
            return 2, x / y
        return (-1 if he.region is None else 3), Fraction(0)  # the same way as d0: through a slit, or a full turn

    return min((he for he in leaving if he is not back), key=clockwise)


def _connected(net: Net) -> bool:
    """Do all regions hang together (through vertices they share)?"""
    at: dict[NetVertex, set[Region]] = {}
    for region in net.regions:
        for he in net.region_cycle(region):
            at.setdefault(he.origin, set()).add(region)
    found = {net.regions[0]}
    stack = [net.regions[0]]
    while stack:
        for he in net.region_cycle(stack.pop()):
            for other in at[he.origin] - found:
                found.add(other)
                stack.append(other)
    return len(found) == len(net.regions)
