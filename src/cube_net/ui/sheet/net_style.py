"""Sizes of the net's drawing elements, in screen pixels (constant at any zoom, docs/idea.txt)."""

# Width of fold edges and cuts (cuts lie fully inside their face).
EDGE_WIDTH_PX = 5.0

# Radius of the vertex circles on the perimeter.
VERTEX_RADIUS_PX = 10.0

# A face is divided into 10 x 5 rectangles of 1/10 x 1/5 units (docs/idea.txt).
HATCH_COLUMNS = 10
HATCH_ROWS = 5

# Pixel size of debug vertex labels (the image index is drawn smaller, as a subscript).
LABEL_FONT_PX = 13

# Gap between a vertex circle and its label.
LABEL_GAP_PX = 3.0

# Hitbox of a cut: a strip of this width along the cut, inside its face (wider than the drawn line, easier to hit).
CUT_HITBOX_PX = EDGE_WIDTH_PX * 1.5

# A highlighted cut (under the mouse) is drawn this wide, still fully inside its face.
HIGHLIGHT_WIDTH_PX = CUT_HITBOX_PX

# Width of the bounding rectangle's line.
BOUNDING_LINE_PX = 1.5

# Extra width (each side) of the halo that marks the new cut line.
CUT_LINE_HALO_PX = 3.0

# Width of the segment from the cut line's last point to the mouse.
RUBBER_BAND_PX = 1.5

# Width of the ring around a highlighted (hovered) perimeter vertex.
VERTEX_HIGHLIGHT_PX = 3.0

# Points of the cut line the user can't edit (crossings with cube edges, counterpart images of endpoints) are drawn
# smaller than the user's points while the line is being drawn and edited: this many times the vertex radius.
DERIVED_POINT_RADIUS_FACTOR = 0.5

# The hollow circle in the middle of a cut-line segment (click: a new point there): this many times the vertex radius.
MIDPOINT_RADIUS_FACTOR = 0.6

# Total width of a fold line's hitbox, centered on the line (a click or a dragged point there lands on the fold).
FOLD_HITBOX_PX = CUT_HITBOX_PX

# Width of a part of a cut that can't be chosen for gluing (its counterpart is in the same half), while it's shown so.
USELESS_CUT_PX = 1.5

# Radius of the round "approve" button shown in the middle of the segment chosen for gluing.
APPROVE_BUTTON_RADIUS_PX = 14.0

# Width of the check mark or the "x" on that button, and of its outline.
APPROVE_CHECK_WIDTH_PX = 3.0
