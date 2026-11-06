"""`default_net()`: the cross from docs/idea.txt, the starting point of every new project."""

from cube_net.core.cube import CUBE, FACES, LOCAL_CORNERS
from cube_net.core.net.builder import RegionSpec, build_net
from cube_net.core.net.net import Net


def default_net() -> Net:
    """Six unit squares placed by `CUBE.default_placement`: 6 regions, 5 folds, 14 perimeter segments."""
    specs = []
    for face in FACES:
        placement = CUBE.default_placement(face)
        specs.append(RegionSpec(face, placement, [placement.apply(c) for c in LOCAL_CORNERS]))
    return build_net(specs)
