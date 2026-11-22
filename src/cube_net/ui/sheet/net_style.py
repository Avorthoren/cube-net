# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Sizes of the net's drawing elements, in screen pixels (constant at any zoom, docs/idea.txt).

The values here are the defaults. Some of them are app settings the user can change (Settings -> Style); `set_sizes`
puts the user's values in place, and everything reads them from here when it paints or hit-tests.

The README's animation shows them, but those of a style (its project has its own): after changing another one here,
run scripts/make_readme_animation.py.
"""

# Width of fold edges and cuts (cuts lie fully inside their face).
EDGE_WIDTH_PX = 4.0

# Radius of the vertex circles on the perimeter.
VERTEX_RADIUS_PX = 6.0

# A unit square (a cube's face) is divided into 10 x 5 rectangles of 1/10 x 1/5 units (docs/idea.txt). Any positive
# numbers will do (below 1, a rectangle is more than a unit).
HATCH_COLUMNS = 10.0
HATCH_ROWS = 5.0

# A unit of length (a whole cube edge) has this many dashes of each of its 2 colours.
DASHES_PER_UNIT = 10.0

# Width of the grid lines on the sheet (0: no grid).
GRID_WIDTH_PX = 1.0

# Pixel size of debug vertex labels (the image index is drawn smaller, as a subscript).
LABEL_FONT_PX = 13

# Gap between a vertex circle and its label.
LABEL_GAP_PX = 3.0

# Hitbox of a cut: a strip this many times as wide as the drawn line along the cut, inside its face (easier to hit).
CUT_HITBOX_FACTOR = 1.5
CUT_HITBOX_PX = EDGE_WIDTH_PX * CUT_HITBOX_FACTOR

# A highlighted cut (under the mouse) is drawn this wide, still fully inside its face.
HIGHLIGHT_WIDTH_PX = CUT_HITBOX_PX

# Width of the bounding rectangle's line.
BOUNDING_LINE_PX = 1.5

# Extra width (each side) of the halo that marks the new cut line.
CUT_LINE_HALO_PX = 3.0

# Width of the segment from the cut line's last point to the mouse.
RUBBER_BAND_PX = 1.5

# Width of the cut line where it's off the net (thin and dashed), and of the outline of its points there.
OFF_NET_LINE_PX = 1.5

# Width of the ring around a highlighted (hovered) perimeter vertex.
VERTEX_HIGHLIGHT_PX = 3.0

# Points of the cut line the user can't edit (crossings with cube edges, counterpart images of endpoints) are drawn
# smaller than the user's points while the line is being drawn and edited: this many times the vertex radius (see
# `derived_point_radius`).
DERIVED_POINT_RADIUS_FACTOR = 0.5

# The hollow circle in the middle of a cut-line segment (click: a new point there): this many times the vertex radius
# (see `midpoint_radius`).
MIDPOINT_RADIUS_FACTOR = 0.6

# No point is ever smaller across than this many times the width of the edges: neither the vertex circles (their
# radius can't be set lower, `least_vertex_radius`) nor the cut line's small dots and circles, which keep this size
# when the vertex radius is so small that their share of it would be less.
SMALL_POINT_DIAMETER_FACTOR = 1.4

# Total width of a fold line's hitbox, centered on the line (a click or a dragged point there lands on the fold).
FOLD_HITBOX_PX = CUT_HITBOX_PX

# Width of a part of a cut that can't be chosen for gluing (its counterpart is in the same half), while it's shown so.
USELESS_CUT_PX = 1.5

# How long the counterpart of a hovered cut stays regular, and then invisible, while it blinks: 6 changes per second.
COUNTERPART_BLINK_MS = round(1000 / 6)

# Radius of the round "approve" button shown in the middle of the segment chosen for gluing.
APPROVE_BUTTON_RADIUS_PX = 14.0

# How far below the approve button its shadow falls.
APPROVE_BUTTON_SHADOW_PX = 2.0

# Width of the check mark or the "x" on that button, and of its outline.
APPROVE_CHECK_WIDTH_PX = 3.0

# The coordinates hint (a point's exact coordinates): the size of its monospace text, the space around the text inside
# its box, and how far its corner is from the mouse (above and to the right of it, unless it wouldn't fit there):
# above it (or below), and to its left (where it doesn't fit on the right).
COORDINATES_FONT_PX = 12
COORDINATES_PADDING_PX = 4
COORDINATES_OFFSET_PX = 14

# How far right of the mouse the hint starts: clear of the pointers that go up and to the right of it (the pencil over
# a point of the cut line, its whole 32 px image), so they don't hide the start of its lines.
COORDINATES_RIGHT_OFFSET_PX = 32


def set_sizes(
    edge_width: float,
    vertex_radius: float,
    hatch_columns: float,
    hatch_rows: float,
    dashes_per_unit: float,
    grid_width: float,
) -> None:
    """Use these values from now on; the sizes that follow from the edge width follow it."""
    global EDGE_WIDTH_PX, VERTEX_RADIUS_PX, HATCH_COLUMNS, HATCH_ROWS, DASHES_PER_UNIT, GRID_WIDTH_PX
    global CUT_HITBOX_PX, HIGHLIGHT_WIDTH_PX, FOLD_HITBOX_PX
    EDGE_WIDTH_PX, VERTEX_RADIUS_PX, GRID_WIDTH_PX = edge_width, vertex_radius, grid_width
    HATCH_COLUMNS, HATCH_ROWS, DASHES_PER_UNIT = hatch_columns, hatch_rows, dashes_per_unit
    CUT_HITBOX_PX = EDGE_WIDTH_PX * CUT_HITBOX_FACTOR
    HIGHLIGHT_WIDTH_PX = CUT_HITBOX_PX
    FOLD_HITBOX_PX = CUT_HITBOX_PX


def smallest_point_radius() -> float:
    """The least radius of the cut line's small dots and hollow circles: a diameter of 140% of the edge width."""
    return EDGE_WIDTH_PX * SMALL_POINT_DIAMETER_FACTOR / 2


def derived_point_radius() -> float:
    """The radius of the small dots of the cut line (crossings with cube edges, images of its ends): a share of the
    vertex radius, but never less than `smallest_point_radius`."""
    return max(VERTEX_RADIUS_PX * DERIVED_POINT_RADIUS_FACTOR, smallest_point_radius())


def midpoint_radius() -> float:
    """The radius of the hollow circles in the middle of the cut line's segments, drawn and clicked: a share of the
    vertex radius, but never less than `smallest_point_radius`."""
    return max(VERTEX_RADIUS_PX * MIDPOINT_RADIUS_FACTOR, smallest_point_radius())


def least_vertex_radius(edge_width: float) -> float:
    """The least vertex radius the user can choose (Settings -> Style) with edges of `edge_width`: a vertex circle is
    at least 140% of the edge width across."""
    return edge_width * SMALL_POINT_DIAMETER_FACTOR / 2
