"""`Box`: an exact axis-aligned rectangle (bounding boxes, the sheet)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from cube_net.core.geometry.vec import Scalar, Vec


@dataclass(frozen=True, slots=True)
class Box:
    """Closed axis-aligned rectangle `[lo.x, hi.x] x [lo.y, hi.y]` with exact coordinates (may be degenerate)."""

    lo: Vec
    hi: Vec

    def __post_init__(self) -> None:
        if self.lo.x > self.hi.x or self.lo.y > self.hi.y:
            raise ValueError(f"Box corners out of order: lo={self.lo}, hi={self.hi}")

    @classmethod
    def around(cls, points: Iterable[Vec]) -> Box:
        """The smallest box containing all `points` (at least one point is required)."""
        pts = list(points)
        if not pts:
            raise ValueError("Box.around() needs at least one point")
        return cls(
            Vec(min(p.x for p in pts), min(p.y for p in pts)),
            Vec(max(p.x for p in pts), max(p.y for p in pts)),
        )

    @property
    def width(self) -> Fraction:
        return self.hi.x - self.lo.x

    @property
    def height(self) -> Fraction:
        return self.hi.y - self.lo.y

    @property
    def center(self) -> Vec:
        return (self.lo + self.hi) / 2

    def expanded(self, margin: Scalar) -> Box:
        """The box grown by `margin` on every side."""
        m = Vec(margin, margin)
        return Box(self.lo - m, self.hi + m)

    def contains(self, p: Vec) -> bool:
        return self.lo.x <= p.x <= self.hi.x and self.lo.y <= p.y <= self.hi.y
