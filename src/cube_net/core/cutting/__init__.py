# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Drawing a new cut line across the net (docs/idea.txt; docs/plan.md, section 4.2)."""

from cube_net.core.cutting.approve import approve
from cube_net.core.cutting.cut_line import CutLine, CutPoint
from cube_net.core.cutting.images import CounterpartImage, counterpart_image, endpoint_point
from cube_net.core.cutting.overlap import overlapping_cuts
from cube_net.core.cutting.pieces import Piece, crossings, pieces, region_at, surface_point_at
from cube_net.core.cutting.rearrange import Rearranged, rearrange
from cube_net.core.cutting.rules import (
    MAX_POINTS_AFTER_FIRST,
    invalid_segments,
    project_onto,
    segment_allowed,
    segment_valid,
    strictly_inside,
)
from cube_net.core.cutting.split import SplitNet, connected_regions, split_net
from cube_net.core.cutting.straight import closest_straight_point, line_meets_segment, straighten

__all__ = [
    "MAX_POINTS_AFTER_FIRST",
    "CounterpartImage",
    "CutLine",
    "CutPoint",
    "Piece",
    "Rearranged",
    "SplitNet",
    "approve",
    "closest_straight_point",
    "connected_regions",
    "counterpart_image",
    "crossings",
    "endpoint_point",
    "invalid_segments",
    "line_meets_segment",
    "overlapping_cuts",
    "pieces",
    "project_onto",
    "rearrange",
    "region_at",
    "segment_allowed",
    "segment_valid",
    "split_net",
    "straighten",
    "strictly_inside",
    "surface_point_at",
]
