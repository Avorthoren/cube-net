# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Sizes of the ruler's drawing elements, in screen pixels (constant at any zoom)."""

# Width of ruler lines.
LINE_WIDTH_PX = 2.0

# Radius of ruler points.
POINT_RADIUS_PX = 3.5

# Pixel size of the coordinate and distance labels.
FONT_PX = 12

# Labels of points are drawn this far up-right of the point; the label at the mouse is drawn down-right of it,
# so the cursor doesn't cover it.
POINT_LABEL_OFFSET_PX = 8.0
CURSOR_LABEL_OFFSET_PX = 16.0

# Distance labels are drawn this far from the middle of their segment, perpendicular to it.
DISTANCE_LABEL_OFFSET_PX = 12.0

# Padding inside the label background box.
LABEL_PADDING_PX = 2.0

# How far (in pixels) ruler labels can reach beyond the sheet. The ruler item claims this much room around the sheet,
# so that Qt repaints its labels there too (otherwise the grey main area could cover them).
LABEL_REACH_PX = 300.0
