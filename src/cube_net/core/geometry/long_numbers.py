# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""How long the numbers of a point may be: every coordinate stays exact, so an action that would make a numerator or a
denominator longer than `MAX_NUMBER_DIGITS` digits is refused instead (`long_number` finds such a number).

Without that, numbers made from numbers made before grow with every generation of cuts (crossings of crossings), to
thousands of digits. And Python turns an integer of more than 4300 digits into text only if asked to: saving a project
would fail, so the limit is well below that.
"""

from dataclasses import dataclass
from enum import Enum
from math import log10

from cube_net.core.geometry.vec import Vec

# The most digits a numerator or a denominator of a coordinate may have.
MAX_NUMBER_DIGITS = 2100


class Axis(Enum):
    X = "x"
    Y = "y"


class Part(Enum):
    NUMERATOR = "numerator"
    DENOMINATOR = "denominator"


@dataclass(frozen=True, slots=True)
class LongNumber:
    """A coordinate's number that's too long: which coordinate, which of its numbers, how many digits."""

    axis: Axis
    part: Part
    digits: int


def digits(n: int) -> int:
    """How many digits `n` has (its sign aside): without turning it into text, which Python refuses past 4300."""
    n = abs(n)
    if n == 0:
        return 1
    estimate = int(n.bit_length() * log10(2))  # n has estimate or estimate + 1 digits
    return estimate + 1 if n >= 10**estimate else estimate


def long_number(p: Vec) -> LongNumber | None:
    """The first number of `p` longer than `MAX_NUMBER_DIGITS` digits (x before y, numerator before denominator), if
    any."""
    for axis, value in ((Axis.X, p.x), (Axis.Y, p.y)):
        for part, n in ((Part.NUMERATOR, value.numerator), (Part.DENOMINATOR, value.denominator)):
            if (
                n.bit_length() > MAX_NUMBER_DIGITS * 3 and (count := digits(n)) > MAX_NUMBER_DIGITS
            ):  # (shorter ones aren't counted)
                return LongNumber(axis, part, count)
    return None
