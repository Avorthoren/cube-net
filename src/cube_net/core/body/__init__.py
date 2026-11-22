# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The body the net folds into: faces glued along their sides, and points on its surface (docs/template_plan.md, §3).
The cube is one body."""

from cube_net.core.body.body import Body, BodyEdge, BodyError, BodyFace, Face, Side, StartPiece, VertexName
from cube_net.core.body.cube import (
    BUILD_ORDER,
    CUBE,
    DEFAULT_FACE_ORIGINS,
    FACE_CORNERS,
    FACES,
    LOCAL_CORNERS,
    VERTICES,
    cube_body,
)
from cube_net.core.body.dashes import DashLayout, dash_layout
from cube_net.core.body.surface_point import SurfacePoint, SurfacePointKind

__all__ = [
    "BUILD_ORDER",
    "CUBE",
    "DEFAULT_FACE_ORIGINS",
    "FACES",
    "FACE_CORNERS",
    "LOCAL_CORNERS",
    "VERTICES",
    "Body",
    "BodyEdge",
    "BodyError",
    "BodyFace",
    "DashLayout",
    "Face",
    "Side",
    "StartPiece",
    "SurfacePoint",
    "SurfacePointKind",
    "VertexName",
    "cube_body",
    "dash_layout",
]
