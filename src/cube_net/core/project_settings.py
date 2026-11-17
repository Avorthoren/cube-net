# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`ProjectSettings`: settings that belong to one project (docs/idea.txt), saved with it."""

from dataclasses import dataclass
from fractions import Fraction

from cube_net.core.body.body import COLOR_PATTERN
from cube_net.core.sheet import TEMPLATE_SHEET_HEIGHT, TEMPLATE_SHEET_WIDTH
from cube_net.core.style import Style

# The goal of the application: a net that fits into a rectangle of less than this area (docs/idea.txt).
DEFAULT_AREA_THRESHOLD = Fraction(71, 10)

# The allowed thresholds, with at most 3 decimals (0: nothing is ever below it).
MIN_AREA_THRESHOLD = Fraction(0)

# As large as the template sheet: no net of any body can need more.
MAX_AREA_THRESHOLD = Fraction(TEMPLATE_SHEET_WIDTH * TEMPLATE_SHEET_HEIGHT)


class ProjectSettingsError(ValueError):
    """A project setting has an invalid value."""


@dataclass(frozen=True, slots=True)
class ProjectSettings:
    # Below this bounding-rectangle area the app celebrates: green rectangle and area, blinking button.
    area_threshold: Fraction = DEFAULT_AREA_THRESHOLD

    # The colour of each face of the project's body (face k: face_colors[k - 1]), as "#RRGGBB". None: not chosen yet
    # (a new project, or one saved before colours belonged to projects); the application fills them in.
    face_colors: tuple[str, ...] | None = None

    # Settings -> Style (docs/template_plan.md, §8.3). None: not chosen yet (a project saved before the style belonged
    # to projects); the application fills it in.
    style: Style | None = None

    def __post_init__(self) -> None:
        if self.style is not None and not isinstance(self.style, Style):
            raise ProjectSettingsError(f"a style must be a Style, got {type(self.style).__name__}")
        if self.face_colors is not None:
            for color in self.face_colors:
                if not isinstance(color, str) or not COLOR_PATTERN.fullmatch(color):
                    raise ProjectSettingsError(f"a colour must be #RRGGBB with capital letters, got {color!r}")
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
