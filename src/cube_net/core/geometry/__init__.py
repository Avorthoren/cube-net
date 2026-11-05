"""Exact 2D geometry (docs/plan.md, section 3.1). One closely related group of definitions per module."""

from cube_net.core.geometry.predicates import (
    IntersectionKind,
    SegmentIntersection,
    classify_segments,
    on_segment,
    orient,
)
from cube_net.core.geometry.rigid90 import Rigid90
from cube_net.core.geometry.vec import Scalar, Vec, to_fraction

__all__ = [
    "IntersectionKind",
    "Rigid90",
    "Scalar",
    "SegmentIntersection",
    "Vec",
    "classify_segments",
    "on_segment",
    "orient",
    "to_fraction",
]
