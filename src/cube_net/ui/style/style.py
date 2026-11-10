# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Style`: the values of Settings -> Style, with their ranges. The defaults are what the style files say."""

import math
import re
from dataclasses import dataclass, replace

from cube_net.ui import palette
from cube_net.ui.sheet import net_style

# How a colour is written: #RRGGBB.
COLOR_PATTERN = re.compile(r"#[0-9A-F]{6}")

# The allowed values (docs/idea.txt, settings).
TILING_RANGE = (1, 30)
DASHES_RANGE = (1, 30)
EDGE_WIDTH_RANGE = (1.0, 15.0)
VERTEX_RADIUS_RANGE = (1.0, 30.0)
GRID_WIDTH_RANGE = (0.0, 5.0)


class StyleError(ValueError):
    """A style value is out of its range."""


@dataclass(frozen=True, slots=True)
class Style:
    # Face k's colour is face_colors[k - 1], as "#RRGGBB".
    face_colors: tuple[str, str, str, str, str, str]

    # A face is tiled into hatch_columns x hatch_rows rectangles.
    hatch_columns: int
    hatch_rows: int

    # A whole cube edge has this many dashes of each of its colours.
    dashes_per_edge: int

    # Width of cuts and folds, in pixels.
    edge_width: float

    # Radius of the vertex circles, in pixels.
    vertex_radius: float

    grid_color: str

    # Width of the grid lines, in pixels; 0: no grid.
    grid_width: float

    def __post_init__(self) -> None:
        for color in (*self.face_colors, self.grid_color):
            if not COLOR_PATTERN.fullmatch(color):
                raise StyleError(f"a colour must be #RRGGBB with capital letters, got {color!r}")
        if len(self.face_colors) != 6:
            raise StyleError(f"there are 6 faces, got {len(self.face_colors)} colours")
        _check("tiling", self.hatch_columns, TILING_RANGE)
        _check("tiling", self.hatch_rows, TILING_RANGE)
        _check("dashes", self.dashes_per_edge, DASHES_RANGE)
        _check("edge width", self.edge_width, EDGE_WIDTH_RANGE)
        _check("vertex radius", self.vertex_radius, VERTEX_RADIUS_RANGE)
        _check("grid width", self.grid_width, GRID_WIDTH_RANGE)

    def fitted(self) -> Style:
        """This style with the vertex radius raised to the least its edge width allows, if it's below that (the edges
        got thicker, or the style was saved before that rule)."""
        least = least_vertex_radius(self.edge_width)
        return self if self.vertex_radius >= least else replace(self, vertex_radius=least)


def least_vertex_radius(edge_width: float) -> float:
    """The least vertex radius with edges of `edge_width` (`net_style.least_vertex_radius`), rounded up to a tenth of
    a pixel as the fields show it, so that it's never below the least."""
    return math.ceil(round(net_style.least_vertex_radius(edge_width) * 10, 6)) / 10


def _check(name: str, value: float, allowed: tuple[float, float]) -> None:
    low, high = allowed
    if not low <= value <= high:
        raise StyleError(f"{name} must be from {low} to {high}, got {value}")


def _name(color: object) -> str:
    return str(color.name()).upper()  # type: ignore[attr-defined]


# What the style files say, taken before anything could change it.
DEFAULT_STYLE = Style(
    face_colors=tuple(_name(palette.FACE_COLORS[face]) for face in range(1, 7)),  # type: ignore[arg-type]
    hatch_columns=net_style.HATCH_COLUMNS,
    hatch_rows=net_style.HATCH_ROWS,
    dashes_per_edge=net_style.DASHES_PER_EDGE,
    edge_width=net_style.EDGE_WIDTH_PX,
    vertex_radius=net_style.VERTEX_RADIUS_PX,
    grid_color=_name(palette.GRID),
    grid_width=net_style.GRID_WIDTH_PX,
)
