"""Drawing a new cut line across the net (docs/idea.txt; docs/plan.md, section 4.2)."""

from cube_net.core.cutting.cut_line import CutLine, CutPoint
from cube_net.core.cutting.images import CounterpartImage, counterpart_image, endpoint_point
from cube_net.core.cutting.pieces import Piece, crossings, pieces, region_at, surface_point_at
from cube_net.core.cutting.rules import (
    MAX_POINTS_AFTER_FIRST,
    invalid_segments,
    project_onto,
    segment_allowed,
    segment_valid,
    strictly_inside,
)

__all__ = [
    "MAX_POINTS_AFTER_FIRST",
    "CounterpartImage",
    "CutLine",
    "CutPoint",
    "Piece",
    "counterpart_image",
    "crossings",
    "endpoint_point",
    "invalid_segments",
    "pieces",
    "project_onto",
    "region_at",
    "segment_allowed",
    "segment_valid",
    "strictly_inside",
    "surface_point_at",
]
