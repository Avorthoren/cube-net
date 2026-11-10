# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The cube net on the sheet (docs/plan.md, section 3.3)."""

from cube_net.core.net.builder import NetBuildError, RegionSpec, build_net
from cube_net.core.net.default_net import default_net
from cube_net.core.net.elements import EdgeKind, HalfEdge, NetVertex, Region
from cube_net.core.net.hit_test import boundary_edge_at, boundary_edge_from, boundary_vertex_at, fold_edge_at
from cube_net.core.net.net import Net, NetCopy, NetInvariantError
from cube_net.core.net.validate import validate_net

__all__ = [
    "EdgeKind",
    "HalfEdge",
    "Net",
    "NetBuildError",
    "NetCopy",
    "NetInvariantError",
    "NetVertex",
    "Region",
    "RegionSpec",
    "boundary_edge_at",
    "boundary_edge_from",
    "boundary_vertex_at",
    "build_net",
    "default_net",
    "fold_edge_at",
    "validate_net",
]
