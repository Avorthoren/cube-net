# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Style`: the values of Settings -> Style, with their ranges (docs/idea.txt, settings). It belongs to the document:
a project or a template keeps its own and is saved with it (docs/template_plan.md, §8.3). The face colours, shown
there too, are kept apart (`ProjectSettings.face_colors`, or the template's faces). The defaults are what the
application's style files say (`cube_net.ui.style.DEFAULT_STYLE`)."""

from dataclasses import dataclass

from cube_net.core.body.body import COLOR_PATTERN

# The allowed values (docs/idea.txt, settings). The tiling and the dashes are any positive numbers up to 30 (with 2
# decimals in the fields).
TILING_RANGE = (0.01, 30.0)
DASHES_RANGE = (0.01, 30.0)
EDGE_WIDTH_RANGE = (1.0, 15.0)
VERTEX_RADIUS_RANGE = (1.0, 30.0)
GRID_WIDTH_RANGE = (0.0, 5.0)


# The names some style values are saved under, unlike their fields (see `stored_name`).
STORED_NAMES = {"dashes_per_unit": "dashes_per_edge"}


class StyleError(ValueError):
    """A style value is out of its range."""


@dataclass(frozen=True, slots=True)
class Style:
    # Every unit square of the grid is tiled into hatch_columns x hatch_rows rectangles: a rectangle is
    # 1 / hatch_columns wide and 1 / hatch_rows high (more than a unit if they're below 1).
    hatch_columns: float
    hatch_rows: float

    # A unit of length of a cut or a fold has this many dashes of each of its colours (a cube's edge is a unit long).
    dashes_per_unit: float

    # Width of cuts and folds, in pixels.
    edge_width: float

    # Radius of the vertex circles, in pixels.
    vertex_radius: float

    grid_color: str

    # Width of the grid lines, in pixels; 0: no grid.
    grid_width: float

    def __post_init__(self) -> None:
        if not isinstance(self.grid_color, str) or not COLOR_PATTERN.fullmatch(self.grid_color):
            raise StyleError(f"a colour must be #RRGGBB with capital letters, got {self.grid_color!r}")
        _check("tiling", self.hatch_columns, TILING_RANGE)
        _check("tiling", self.hatch_rows, TILING_RANGE)
        _check("dashes", self.dashes_per_unit, DASHES_RANGE)
        _check("edge width", self.edge_width, EDGE_WIDTH_RANGE)
        _check("vertex radius", self.vertex_radius, VERTEX_RADIUS_RANGE)
        _check("grid width", self.grid_width, GRID_WIDTH_RANGE)


def stored_name(field: str) -> str:
    """The name a style value is saved under (in files and in the application's settings): its field's, except for
    the dashes, which were per edge when only the cube had them (a cube's edge is a unit long: the same number)."""
    return STORED_NAMES.get(field, field)


def _check(name: str, value: object, allowed: tuple[float, float]) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise StyleError(f"{name} must be a number, got {value!r}")
    low, high = allowed
    if not low <= value <= high:
        raise StyleError(f"{name} must be from {low} to {high}, got {value}")
