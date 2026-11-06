"""The sheet: the rectangle the cube net lies on (docs/idea.txt; docs/plan.md, section 4.8)."""

from collections.abc import Iterable

from cube_net.core.geometry import Box, Vec

# Distance (in units) from the net's bounding box to each edge of the sheet.
SHEET_MARGIN = 5


def sheet_box(net_points: Iterable[Vec]) -> Box:
    """The sheet for a net with the given vertex positions: its bounding box plus `SHEET_MARGIN` on each side."""
    return Box.around(net_points).expanded(SHEET_MARGIN)
