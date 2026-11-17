# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The default `Style` (what the style files say), and what the UI adds to the core's `Style`: the least vertex radius
an edge width allows."""

import math
from dataclasses import replace

from cube_net.core.style import Style
from cube_net.ui import palette
from cube_net.ui.sheet import net_style


def fitted(style: Style) -> Style:
    """`style` with the vertex radius raised to the least its edge width allows, if it's below that (the edges got
    thicker, or the style was saved before that rule)."""
    least = least_vertex_radius(style.edge_width)
    return style if style.vertex_radius >= least else replace(style, vertex_radius=least)


def least_vertex_radius(edge_width: float) -> float:
    """The least vertex radius with edges of `edge_width` (`net_style.least_vertex_radius`), rounded up to a tenth of
    a pixel as the fields show it, so that it's never below the least."""
    return math.ceil(round(net_style.least_vertex_radius(edge_width) * 10, 6)) / 10


def _name(color: object) -> str:
    return str(color.name()).upper()  # type: ignore[attr-defined]


# What the style files say, taken before anything could change it. A new template starts with it, and so does the
# built-in Cube. The README's animation shows it: after changing the defaults, run scripts/make_readme_animation.py.
DEFAULT_STYLE = Style(
    hatch_columns=net_style.HATCH_COLUMNS,
    hatch_rows=net_style.HATCH_ROWS,
    dashes_per_edge=net_style.DASHES_PER_EDGE,
    edge_width=net_style.EDGE_WIDTH_PX,
    vertex_radius=net_style.VERTEX_RADIUS_PX,
    grid_color=_name(palette.GRID),
    grid_width=net_style.GRID_WIDTH_PX,
)
