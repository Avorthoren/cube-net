"""`Rigid90`: an exact rigid motion of the plane by a multiple of 90 degrees (docs/plan.md, section 3.1).

Every rearrangement of cube net parts is such a motion (docs/idea.txt, "Some facts we agreed on"), and so is the
placement of every cube net region (face-local frame -> sheet).
"""

from __future__ import annotations

from dataclasses import dataclass

from cube_net.core.geometry.vec import Vec

_ORIGIN = Vec(0, 0)


@dataclass(frozen=True, slots=True)
class Rigid90:
    """Orientation-preserving map `p -> R^k * p + t`, where R is the counter-clockwise rotation by 90 degrees.

    So `Rigid90(k, t)` represents rotation by 90 degrees counter-clockwise around the origin `k` times
    and then moving by `t`.

    `k` is always normalized to 0..3. Composition follows function notation: `(a @ b).apply(p) == a.apply(b.apply(p))`.
    """

    k: int
    t: Vec

    def __init__(self, k: int = 0, t: Vec = _ORIGIN) -> None:
        if isinstance(k, bool) or not isinstance(k, int):
            raise TypeError(f"k must be int, got {type(k).__name__}: {k!r}")
        if not isinstance(t, Vec):
            raise TypeError(f"t must be Vec, got {type(t).__name__}: {t!r}")
        object.__setattr__(self, "k", k % 4)
        object.__setattr__(self, "t", t)

    # --- constructors -------------------------------------------------------------------------------------------

    @classmethod
    def identity(cls) -> Rigid90:
        return cls()

    @classmethod
    def translation(cls, t: Vec) -> Rigid90:
        return cls(0, t)

    @classmethod
    def rotation(cls, k: int, center: Vec = _ORIGIN) -> Rigid90:
        """Rotation by k * 90 degrees counter-clockwise around `center`."""
        return cls(k, center - center.rotated90(k))

    @classmethod
    def from_segments(cls, src_start: Vec, src_end: Vec, dst_start: Vec, dst_end: Vec) -> Rigid90:
        """The unique motion that maps `src_start -> dst_start` and `src_end -> dst_end`.

        Raises `ValueError` if the segments are degenerate, have different lengths, or are not related by a rotation by
        a multiple of 90 degrees. For cube net counterparts this must never happen, so the error is an invariant check.
        """
        src_dir = src_end - src_start
        dst_dir = dst_end - dst_start
        if src_dir.is_zero() or dst_dir.is_zero():
            raise ValueError("degenerate (zero-length) segment")
        for k in range(4):
            if src_dir.rotated90(k) == dst_dir:
                return cls(k, dst_start - src_start.rotated90(k))
        raise ValueError(
            f"segments {src_start}->{src_end} and {dst_start}->{dst_end} are not related by a 90-degree rigid motion"
        )

    # --- application ----------------------------------------------------------------------------------------------

    def apply(self, p: Vec) -> Vec:
        """Map a point."""
        return p.rotated90(self.k) + self.t

    def apply_vector(self, v: Vec) -> Vec:
        """Map a direction/displacement (rotation only, no translation)."""
        return v.rotated90(self.k)

    # --- algebra --------------------------------------------------------------------------------------------------

    def __matmul__(self, other: Rigid90) -> Rigid90:
        """Composition: `self` applied after `other`."""
        if not isinstance(other, Rigid90):
            return NotImplemented
        return Rigid90(self.k + other.k, other.t.rotated90(self.k) + self.t)

    def inverse(self) -> Rigid90:
        return Rigid90(-self.k, -self.t.rotated90(-self.k))

    def is_identity(self) -> bool:
        return self.k == 0 and self.t.is_zero()

    def __repr__(self) -> str:
        return f"Rigid90(k={self.k}, t={self.t!r})"
