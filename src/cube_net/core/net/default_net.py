# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`starting_net()`: the net a new project of a body starts from; `default_net()`: the cube's, the cross from
docs/idea.txt."""

from cube_net.core.body import CUBE, Body
from cube_net.core.geometry import Vec
from cube_net.core.net.builder import NetBuildError, RegionSpec, build_net
from cube_net.core.net.net import Net


def starting_net(body: Body) -> Net:
    """Every face placed as the body's `start` says. The vertices get their ids (which number the images of each
    vertex) in the body's `vertex_order` (then the points that aren't vertices of the body), or else in the order the
    faces reach them."""
    specs = []
    for piece in body.start:
        specs.append(
            RegionSpec(piece.face, piece.placement, [piece.placement.apply(c) for c in piece.local_corners(body)])
        )
    net = build_net(body, specs)
    if body.vertex_order is not None:
        rank: dict[tuple[Vec, str | None], int] = {key: i for i, key in enumerate(body.vertex_order)}
        if set(rank) != {(v.position, v.point.vertex) for v in net.vertices if v.point.vertex is not None}:
            raise NetBuildError("the body's order of the starting net's vertices doesn't name exactly its vertices")
        # Points that aren't vertices of the body (inside a face glued from pieces) come last, as the faces reach them.
        net.vertices.sort(key=lambda v: rank.get((v.position, v.point.vertex), len(rank)))
        for i, v in enumerate(net.vertices):
            v.id = i
        net.reindex()
    return net


def default_net() -> Net:
    """The cube's cross: 6 regions, 5 folds, 14 perimeter segments."""
    return starting_net(CUBE)
