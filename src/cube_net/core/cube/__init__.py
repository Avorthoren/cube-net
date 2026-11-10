# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The cube surface: topology of faces/edges/vertices and points on the surface (docs/plan.md, section 3.2)."""

from cube_net.core.cube.dashes import DASH_LENGTH, DashLayout, dash_layout
from cube_net.core.cube.surface_point import SurfacePoint, SurfacePointKind
from cube_net.core.cube.topology import (
    CUBE,
    DEFAULT_FACE_ORIGINS,
    FACE_CORNERS,
    FACES,
    LOCAL_CORNERS,
    VERTICES,
    CubeTableError,
    CubeTopology,
    Edge,
    Face,
    VertexLabel,
)

__all__ = [
    "CUBE",
    "DASH_LENGTH",
    "DEFAULT_FACE_ORIGINS",
    "FACES",
    "FACE_CORNERS",
    "LOCAL_CORNERS",
    "VERTICES",
    "CubeTableError",
    "CubeTopology",
    "DashLayout",
    "Edge",
    "Face",
    "SurfacePoint",
    "SurfacePointKind",
    "VertexLabel",
    "dash_layout",
]
