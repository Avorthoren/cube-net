"""Putting a `Style` in place: everything that paints or hit-tests reads it from `net_style` and `palette`."""

from PyQt6.QtGui import QColor

from cube_net.ui import palette
from cube_net.ui.sheet import net_style
from cube_net.ui.style.style import Style


def apply_style(style: Style) -> None:
    """Use `style` from now on. What's on screen has to be repainted (and caches of the old style forgotten)."""
    net_style.set_sizes(
        style.edge_width,
        style.vertex_radius,
        style.hatch_columns,
        style.hatch_rows,
        style.dashes_per_edge,
        style.grid_width,
    )
    palette.set_colors(
        {face: QColor(color) for face, color in enumerate(style.face_colors, start=1)}, QColor(style.grid_color)
    )
