# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Putting a `Style` in place: everything that paints or hit-tests reads it from `net_style` and `palette`."""

from PyQt6.QtGui import QColor

from cube_net.core.style import Style
from cube_net.ui import palette
from cube_net.ui.sheet import net_style


def apply_style(style: Style) -> None:
    """Use `style` from now on. What's on screen has to be repainted (and caches of the old style forgotten)."""
    net_style.set_sizes(
        style.edge_width,
        style.vertex_radius,
        style.hatch_columns,
        style.hatch_rows,
        style.dashes_per_unit,
        style.grid_width,
    )
    palette.set_grid_color(QColor(style.grid_color))


def style_in_place() -> Style:
    """The style everything paints in now (the latest `apply_style`'s)."""
    return Style(
        hatch_columns=net_style.HATCH_COLUMNS,
        hatch_rows=net_style.HATCH_ROWS,
        dashes_per_unit=net_style.DASHES_PER_UNIT,
        edge_width=net_style.EDGE_WIDTH_PX,
        vertex_radius=net_style.VERTEX_RADIUS_PX,
        grid_color=palette.GRID.name().upper(),
        grid_width=net_style.GRID_WIDTH_PX,
    )
