# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`starting_net()`: the net a new project of a body starts from; `default_net()`: the cube's, the cross from
docs/idea.txt."""

from cube_net.core.body import CUBE, Body
from cube_net.core.net.builder import RegionSpec, build_net
from cube_net.core.net.net import Net


def starting_net(body: Body) -> Net:
    """Every face placed as the body's `start` says, in that order (which numbers the images of each vertex)."""
    specs = []
    for face, placement in body.start:
        specs.append(RegionSpec(face, placement, [placement.apply(c) for c in body.face(face).corners]))
    return build_net(body, specs)


def default_net() -> Net:
    """The cube's cross: 6 regions, 5 folds, 14 perimeter segments."""
    return starting_net(CUBE)
