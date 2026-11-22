# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The sheet: the rectangle the cube net lies on (docs/idea.txt; docs/plan.md, section 4.8)."""

from collections.abc import Iterable

from cube_net.core.geometry import Box, Vec

# Distance (in units) from the net's bounding box to each edge of the sheet.
SHEET_MARGIN = 5

# The size of the sheet a template is drawn on, in units (fixed: it doesn't follow the net).
TEMPLATE_SHEET_WIDTH = 100

TEMPLATE_SHEET_HEIGHT = 100


def sheet_box(net_points: Iterable[Vec]) -> Box:
    """The sheet for a net with the given vertex positions: its bounding box plus `SHEET_MARGIN` on each side."""
    return Box.around(net_points).expanded(SHEET_MARGIN)
