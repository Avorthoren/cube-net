# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`ProjectSettings`: settings that belong to one project (docs/idea.txt). Saved with the project from M9 on."""

from dataclasses import dataclass
from fractions import Fraction

# The goal of the application: a net that fits into a rectangle of less than this area (docs/idea.txt).
DEFAULT_AREA_THRESHOLD = Fraction(71, 10)

# The allowed thresholds, with at most 3 decimals (0: nothing is ever below it).
MIN_AREA_THRESHOLD = Fraction(0)

MAX_AREA_THRESHOLD = Fraction(20)


class ProjectSettingsError(ValueError):
    """A project setting has an invalid value."""


@dataclass(frozen=True, slots=True)
class ProjectSettings:
    # Below this bounding-rectangle area the app celebrates: green rectangle and area, blinking button.
    area_threshold: Fraction = DEFAULT_AREA_THRESHOLD

    def __post_init__(self) -> None:
        t = self.area_threshold
        if not isinstance(t, Fraction):
            raise ProjectSettingsError(f"area threshold must be a Fraction, got {type(t).__name__}: {t!r}")
        if t < MIN_AREA_THRESHOLD:
            raise ProjectSettingsError(f"area threshold can't be negative, got {format_threshold(t)}")
        if t > MAX_AREA_THRESHOLD:
            raise ProjectSettingsError(f"area threshold can't exceed {format_threshold(MAX_AREA_THRESHOLD)}")
        if (t * 1000).denominator != 1:
            raise ProjectSettingsError(f"area threshold can have at most 3 decimals, got {float(t)}")


def format_threshold(value: Fraction) -> str:
    return f"{float(value):.3f}"
