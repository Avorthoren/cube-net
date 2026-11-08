"""Exact 2D point/vector `Vec` and the exact-number guard `to_fraction` (docs/plan.md, section 3.1).

All coordinates are `fractions.Fraction`. Floats are deliberately rejected: a float coming from the UI must go through
`quantize()` first, so that every computation in the core stays exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from numbers import Rational

type Scalar = int | Fraction


def to_fraction(value: object) -> Fraction:
    """
    Convert an exact rational number to `Fraction`.
    Rejects floats and bools (they are almost always a bug here).

    TODO: This will be used a lot. Later, when application is tested well
          these checks can be dropped (together with this function).
          We can just call `Fraction(value)` directly whenever needed.
    """
    if isinstance(value, bool) or not isinstance(value, Rational):
        raise TypeError(f"expected int or Fraction, got {type(value).__name__}: {value!r}")
    return Fraction(value)


@dataclass(frozen=True, slots=True, order=True)
class Vec:
    """An immutable point/vector on the sheet plane (or in a face's local frame) with exact coordinates.

    Ordering is lexicographic by (x, y), which is what convex hull algorithms need.
    """

    x: Fraction
    y: Fraction

    def __init__(self, x: Scalar, y: Scalar) -> None:
        object.__setattr__(self, "x", to_fraction(x))
        object.__setattr__(self, "y", to_fraction(y))

    @classmethod
    def _of_fractions(cls, x: Fraction, y: Fraction) -> Vec:
        """A `Vec` of what's known to be fractions, without checking: this is the hottest code of the application."""
        result = object.__new__(cls)
        object.__setattr__(result, "x", x)
        object.__setattr__(result, "y", y)
        return result

    def __add__(self, other: Vec) -> Vec:
        if not isinstance(other, Vec):
            return NotImplemented
        return Vec._of_fractions(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec) -> Vec:
        if not isinstance(other, Vec):
            return NotImplemented
        return Vec._of_fractions(self.x - other.x, self.y - other.y)

    def __neg__(self) -> Vec:
        return Vec._of_fractions(-self.x, -self.y)

    def __mul__(self, k: Scalar) -> Vec:
        if isinstance(k, bool) or not isinstance(k, Rational):
            return NotImplemented
        return Vec._of_fractions(self.x * k, self.y * k)

    __rmul__ = __mul__

    def __truediv__(self, k: Scalar) -> Vec:
        if isinstance(k, bool) or not isinstance(k, Rational):
            return NotImplemented
        if k == 0:
            raise ZeroDivisionError("Vec division by zero")
        return Vec._of_fractions(self.x / k, self.y / k)

    def dot(self, other: Vec) -> Fraction:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vec) -> Fraction:
        """Z-component of the 3D cross product: > 0 if `other` is counter-clockwise from `self`."""
        return self.x * other.y - self.y * other.x

    def length_squared(self) -> Fraction:
        return self.dot(self)

    def rotated90(self, k: int = 1) -> Vec:
        """Rotate counter-clockwise by k * 90 degrees around the origin (k may be negative)."""
        match k % 4:
            case 0:
                return self
            case 1:
                return Vec(-self.y, self.x)
            case 2:
                return Vec(-self.x, -self.y)
            case _:
                return Vec(self.y, -self.x)

    def is_zero(self) -> bool:
        return self.x == 0 and self.y == 0

    def to_floats(self) -> tuple[float, float]:
        """Approximate coordinates, for drawing only."""
        return float(self.x), float(self.y)

    def __repr__(self) -> str:
        return f"Vec({self.x}, {self.y})"


def main():
    v1 = Vec(1, 2)
    v2 = Vec(2, 3)
    print(v1)
    print(id(v1))
    v1 += v2
    print(id(v1))
    print(v1)


if __name__ == "__main__":
    main()
