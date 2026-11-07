"""Drawing a new cut line across the net (docs/idea.txt; docs/plan.md, section 4.2)."""

from cube_net.core.cutting.cut_line import CutLine, CutPoint
from cube_net.core.cutting.pieces import Piece, pieces, region_at, surface_point_at
from cube_net.core.cutting.rules import MAX_POINTS_AFTER_FIRST, project_onto, segment_allowed, strictly_inside

__all__ = [
    "MAX_POINTS_AFTER_FIRST",
    "CutLine",
    "CutPoint",
    "Piece",
    "pieces",
    "project_onto",
    "region_at",
    "segment_allowed",
    "strictly_inside",
    "surface_point_at",
]
