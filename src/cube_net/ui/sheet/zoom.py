# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Zoom rules for the sheet (docs/idea.txt, zoom section). Pure functions, no Qt.

Zoom is expressed as a scale: screen pixels per unit (1 unit = edge of the cube).
The limits depend on the net, the screen and an app setting (docs/idea.txt).
"""

# A new project shows the net at 50% of the screen height.
INITIAL_NET_SCREEN_FRACTION = 0.5

# How far in the view can zoom by default, and what the user may set instead (pixels per unit; an app setting).
DEFAULT_MAX_ZOOM = 1000
MAX_ZOOM_RANGE = (500, 10000)

# Zooming out stops where the net takes this much of the screen (of its height or width, whichever it takes more of).
MIN_ZOOM_NET_SCREEN_FRACTION = 0.5

# Zoom factor per mouse wheel notch.
WHEEL_STEP = 1.15


def initial_scale(screen_height_px: float, net_height: float) -> float:
    """Scale at which a net of `net_height` units takes 50% of the screen height."""
    if screen_height_px <= 0 or net_height <= 0:
        raise ValueError(f"need positive sizes, got screen={screen_height_px}, net={net_height}")
    return INITIAL_NET_SCREEN_FRACTION * screen_height_px / net_height


def zoom_limits(
    screen_width_px: float, screen_height_px: float, net_width: float, net_height: float, max_scale: float
) -> tuple[float, float]:
    """(min_scale, max_scale) allowed for a net of the given size (in units) on the screen (docs/idea.txt, zoom).

    1. Zoom in: up to `max_scale` (an app setting).
    2. Zoom out: as long as the net takes at least `MIN_ZOOM_NET_SCREEN_FRACTION` of the screen, in the dimension where
       it takes more of it. Never more than `max_scale`, so there's always a zoom to be at.
    """
    if min(screen_width_px, screen_height_px, net_width, net_height, max_scale) <= 0:
        raise ValueError(
            f"need positive sizes, got screen={screen_width_px}x{screen_height_px}, net={net_width}x{net_height}, "
            f"max_scale={max_scale}"
        )
    # The scale at which the net fills the screen.
    fits = min(screen_width_px / net_width, screen_height_px / net_height)
    return min(MIN_ZOOM_NET_SCREEN_FRACTION * fits, max_scale), max_scale


def clamp_scale(scale: float, limits: tuple[float, float]) -> float:
    low, high = limits
    return min(max(scale, low), high)
