"""The single entry point for inexact user input into the exact core (docs/plan.md, section 1, principle 3).

Every point that comes from the UI (mouse positions in sheet units, as floats) goes through `quantize()`. For now it
rounds each coordinate to the nearest multiple of `QUANTUM` (1/1000 unit, docs/idea.txt). Snapping to vertices, edges
and grid will be added here later.
"""

import math
from fractions import Fraction

from cube_net.core.geometry.vec import Vec

QUANTUM = Fraction(1, 1000)
"""Default rounding step for user input, in cube units."""


def quantize_scalar(value: float | int, step: Fraction = QUANTUM) -> Fraction:
    """Round a number to the nearest multiple of `step`; exact ties go to the even multiple (like `round()`).

    The float is first converted to `Fraction` exactly (its true binary value), so the result does not depend on
    float arithmetic.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"expected float or int, got {type(value).__name__}: {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"cannot quantize non-finite value {value!r}")
    if not isinstance(step, Fraction) or step <= 0:
        raise ValueError(f"step must be a positive Fraction, got {step!r}")
    return round(Fraction(value) / step) * step


def quantize(x: float | int, y: float | int, step: Fraction = QUANTUM) -> Vec:
    """Turn a UI position (sheet units) into an exact `Vec` on the `step` grid."""
    return Vec(quantize_scalar(x, step), quantize_scalar(y, step))
