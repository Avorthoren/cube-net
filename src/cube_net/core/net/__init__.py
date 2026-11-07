"""The cube net on the sheet (docs/plan.md, section 3.3)."""

from cube_net.core.net.builder import NetBuildError, RegionSpec, build_net
from cube_net.core.net.default_net import default_net
from cube_net.core.net.elements import EdgeKind, HalfEdge, NetVertex, Region
from cube_net.core.net.hit_test import boundary_edge_at
from cube_net.core.net.net import Net, NetInvariantError

__all__ = [
    "EdgeKind",
    "HalfEdge",
    "Net",
    "NetBuildError",
    "NetInvariantError",
    "NetVertex",
    "Region",
    "RegionSpec",
    "boundary_edge_at",
    "build_net",
    "default_net",
]
