"""Zoom rules for the sheet (docs/idea.txt, zoom section). Pure functions, no Qt.

Zoom is expressed as a scale: screen pixels per unit (1 unit = edge of the cube).
The limits are provisional (docs/idea.txt), so they live in one replaceable function.
"""

INITIAL_NET_SCREEN_FRACTION = 0.5
"""A new project shows the net at 50% of the screen height."""

WHEEL_STEP = 1.15
"""Zoom factor per mouse wheel notch."""


def initial_scale(screen_height_px: float, net_height: float) -> float:
    """Scale at which a net of `net_height` units takes 50% of the screen height."""
    if screen_height_px <= 0 or net_height <= 0:
        raise ValueError(f"need positive sizes, got screen={screen_height_px}, net={net_height}")
    return INITIAL_NET_SCREEN_FRACTION * screen_height_px / net_height


def zoom_limits(screen_height_px: float, sheet_width: float, sheet_height: float) -> tuple[float, float]:
    """(min_scale, max_scale) allowed for a sheet of the given size (in units).

    1. Zoom out: the smaller sheet dimension stays at least 10% of the screen height.
    2. Zoom in: the screen height stays at least 5% of the bigger sheet dimension.
    If the two rules contradict each other (an extremely elongated sheet), the zoom-out rule wins.
    """
    if screen_height_px <= 0 or sheet_width <= 0 or sheet_height <= 0:
        raise ValueError(f"need positive sizes, got screen={screen_height_px}, sheet={sheet_width}x{sheet_height}")
    min_scale = 0.10 * screen_height_px / min(sheet_width, sheet_height)
    max_scale = screen_height_px / (0.05 * max(sheet_width, sheet_height))
    return min_scale, max(min_scale, max_scale)


def clamp_scale(scale: float, limits: tuple[float, float]) -> float:
    low, high = limits
    return min(max(scale, low), high)
