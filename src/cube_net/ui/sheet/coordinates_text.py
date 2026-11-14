# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The text of the coordinates hint (docs/idea.txt): a point's y, then its x, each as its exact, reduced fraction, then
as a decimal with 3 digits after the point:

    y: -892392/7255 ≈ -123.004        y:  17
    x:    5405/539  ≈   10.028        x: 101/8 = 12.625

"=" when the decimal is the exact value, "≈" when it's rounded. An integer is just that number: no slash, no decimal.
The fractions' slashes are one under the other (exactly one space between "y:" or "x:" and the longest numerator), and
so are the signs and the decimal points (one space between the sign and the longest decimal). In the hint, a numerator
or a denominator longer than `MAX_DIGITS` digits shows as `TOO_LONG`; the copied text has them all.
"""

from fractions import Fraction

from cube_net.core.geometry import Vec

# The longest numerator or denominator the hint shows (digits, without the sign).
MAX_DIGITS = 10

# What the hint shows instead of a longer one.
TOO_LONG = "too_long"

# Thousandths: the decimals have 3 digits after the point.
_THOUSAND = 1000


def decimal_text(value: Fraction) -> str:
    """`value` with 3 digits after the point, rounded to the nearest thousandth the way the mouse's position is
    (`quantize`: exact ties go to the even one), so that a point placed at the footer's coordinates shows the same
    digits. A tiny negative value is "-0.000"."""
    thousandths = round(value * _THOUSAND)
    whole, rest = divmod(abs(thousandths), _THOUSAND)
    sign = "-" if value < 0 else ""
    return f"{sign}{whole}.{rest:03d}"


def is_exact(value: Fraction) -> bool:
    """The 3-digit decimal is the value itself."""
    return (value * _THOUSAND).denominator == 1


def _number(value: int, limit: int | None) -> str:
    """`value`, or `TOO_LONG` if it has more than `limit` digits (None: no limit)."""
    if limit is not None and len(str(abs(value))) > limit:
        return TOO_LONG
    return str(value)


def coordinate_lines(point: Vec, limit: int | None = MAX_DIGITS) -> list[str]:
    """The hint's lines: y, then x (see the module's docstring). `limit`: the longest number shown as it is (None:
    every number in full, as copied)."""
    rows = [("y", point.y), ("x", point.x)]
    numerators = [_number(value.numerator, limit) for _, value in rows]
    fractional = [value.denominator != 1 for _, value in rows]
    denominators = [_number(value.denominator, limit) if has else "" for (_, value), has in zip(rows, fractional)]
    decimals = [decimal_text(value) for _, value in rows]
    numerator_width = max(len(numerator) for numerator in numerators)
    denominator_width = max((len(d) for d, has in zip(denominators, fractional) if has), default=0)
    whole_width = max((len(t.split(".")[0]) for t, has in zip(decimals, fractional) if has), default=0)
    lines = []
    for (name, value), numerator, denominator, decimal, has in zip(
        rows, numerators, denominators, decimals, fractional, strict=True
    ):
        line = f"{name}: {numerator:>{numerator_width}}"
        if has:
            whole, rest = decimal.split(".")
            sign = "=" if is_exact(value) else "≈"
            line += f"/{denominator:<{denominator_width}} {sign} {whole:>{whole_width}}.{rest}"
        lines.append(line)
    return lines


def copied_text(point: Vec) -> str:
    """What Ctrl+C copies: the hint's two lines, with every number in full."""
    return "\n".join(coordinate_lines(point, limit=None))
