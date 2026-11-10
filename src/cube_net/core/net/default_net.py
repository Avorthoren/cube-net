# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`default_net()`: the cross from docs/idea.txt, the starting point of every new project."""

from cube_net.core.cube import CUBE, LOCAL_CORNERS
from cube_net.core.net.builder import RegionSpec, build_net
from cube_net.core.net.net import Net

# Faces are added in this order, so vertex ids (creation order) number the images of each cube vertex exactly as
# in docs/idea.txt: A_1 = (11, 14), A_2 = (10, 13), A_3 = (11, 10), E_1 = (11, 11), E_2 = (10, 12), and so on.
BUILD_ORDER = (1, 2, 6, 3, 4, 5)


def default_net() -> Net:
    """Six unit squares placed by `CUBE.default_placement`: 6 regions, 5 folds, 14 perimeter segments."""
    specs = []
    for face in BUILD_ORDER:
        placement = CUBE.default_placement(face)
        specs.append(RegionSpec(face, placement, [placement.apply(c) for c in LOCAL_CORNERS]))
    return build_net(specs)
