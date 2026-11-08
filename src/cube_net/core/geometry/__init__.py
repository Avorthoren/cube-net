"""Exact 2D geometry (docs/plan.md, section 3.1). One closely related group of definitions per module."""

from cube_net.core.geometry.box import Box
from cube_net.core.geometry.convex_hull import convex_hull
from cube_net.core.geometry.polygon import polygon_contains, signed_area
from cube_net.core.geometry.predicates import (
    IntersectionKind,
    SegmentIntersection,
    classify_segments,
    on_segment,
    orient,
)
from cube_net.core.geometry.quantize import QUANTUM, quantize, quantize_scalar
from cube_net.core.geometry.rigid90 import Rigid90
from cube_net.core.geometry.sectors import sectors_overlap, strictly_within
from cube_net.core.geometry.vec import Scalar, Vec, to_fraction

__all__ = [
    "QUANTUM",
    "Box",
    "IntersectionKind",
    "Rigid90",
    "Scalar",
    "SegmentIntersection",
    "Vec",
    "classify_segments",
    "convex_hull",
    "on_segment",
    "orient",
    "polygon_contains",
    "quantize",
    "quantize_scalar",
    "sectors_overlap",
    "signed_area",
    "strictly_within",
    "to_fraction",
]
