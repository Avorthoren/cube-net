# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`build_net()`: assemble a `Net` from region polygons (used for the default net and in tests).

All consistency checks of the input happen here, once, with readable `NetBuildError`s.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from cube_net.core.cube import Face, SurfacePoint
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


def build_net(specs: Iterable[RegionSpec]) -> Net:
    """Build a net. Corners at the same sheet position become one vertex; sides shared by two regions become inner
    edges (FOLD on a cube edge, SEAM otherwise); all other sides become the perimeter.

    Limitation: no two perimeter segments may start at the same vertex (no touching parts), which is enough for the
    default net and for tests.
    """
    vertices: dict[Vec, NetVertex] = {}
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
            point = SurfacePoint(spec.face, to_local.apply(position))
            vertex = vertices.get(position)
            if vertex is None:
                vertex = vertices[position] = NetVertex(len(vertices), position, point)
            elif vertex.point != point:
                raise NetBuildError(f"regions disagree at {position}: {vertex.point} vs {point}")
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

    outside_from: dict[NetVertex, HalfEdge] = {}
    paired: set[HalfEdge] = set()
    for (a, b), he in by_side.items():
        if he in paired:
            continue
        mate = by_side.get((b, a))
        if mate is not None:
            paired.add(mate)
            on_cube_edge = len(a.point.faces & b.point.faces) == 2
            he.kind = mate.kind = EdgeKind.FOLD if on_cube_edge else EdgeKind.SEAM
            he.twin, mate.twin = mate, he
            continue
        out = HalfEdge(len(half_edges), b, EdgeKind.BOUNDARY, None)
        half_edges.append(out)
        he.twin, out.twin = out, he
        if b in outside_from:
            raise NetBuildError(f"two perimeter segments start at {b.position} (touching parts are not supported)")
        outside_from[b] = out

    for out in outside_from.values():
        nxt = outside_from.get(out.destination)
        if nxt is None:
            raise NetBuildError(f"perimeter is broken at {out.destination.position}")
        out.next, nxt.prev = nxt, out

    net = Net(vertices.values(), half_edges, regions)
    if len(net.perimeter()) != len(outside_from):
        raise NetBuildError("the net's perimeter must be a single cycle (the net must be connected and have no holes)")
    return net
