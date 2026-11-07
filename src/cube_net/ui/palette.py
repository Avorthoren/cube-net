"""Colours used by the UI (docs/idea.txt; docs/plan.md, section 6.5)."""

from types import MappingProxyType

from PyQt6.QtGui import QColor

# Background of the main area around the sheet.
MAIN_AREA = QColor("#9AA0A6")

SHEET = QColor("#FFFFFF")
SHEET_BORDER = QColor("#5F6368")

# Thin light-grey 1x1 grid on the sheet.
GRID = QColor("#D3D3D3")

FACE_COLORS = MappingProxyType(
    {
        # Default face colours from docs/idea.txt. Look-alike colours are on opposite faces (1-6, 2-5, 3-4).
        # Will become an application setting later.
        1: QColor("#0057B8"),  # deep blue
        2: QColor("#F28E00"),  # orange
        3: QColor("#008A4B"),  # green
        4: QColor("#8B45B5"),  # purple
        5: QColor("#E50055"),  # magenta
        6: QColor("#00A6D6"),  # cyan
    }
)

# Second colour of the hatch pattern and of dashes of cuts inside a face.
WHITE = QColor("#FFFFFF")

# Thin outline of vertex circles, so that sectors stand out on similar colours.
VERTEX_OUTLINE = QColor("#3C4043")

# Debug vertex labels.
LABEL = QColor("#000000")

# Ruler lines and points (red, so they stand out on every face colour and never look like the black error flashes).
RULER = QColor("#C5221F")

# Text of ruler labels, drawn on a translucent white box so it's readable over the hatch.
RULER_TEXT = QColor("#000000")
RULER_LABEL_BACKGROUND = QColor(255, 255, 255, 210)

# The bounding rectangle (thin line).
BOUNDING_RECTANGLE = QColor("#000000")

# Success: the bounding rectangle's area is below the threshold. Clearly different from face 3's green (#008A4B).
SUCCESS = QColor("#39D353")

# The new cut line being drawn: a translucent halo around its dashes and points, so it differs from existing cuts.
CUT_LINE_HALO = QColor(255, 214, 0, 170)

# The segment from the cut line's last point to the mouse.
RUBBER_BAND = QColor(32, 33, 36, 200)

# A rejected segment is shown in this colour for a moment (docs/idea.txt: black for 200 ms).
REJECTED = QColor("#000000")

# Ring around a perimeter vertex under the mouse (a click there starts / ends the cut line at that vertex).
VERTEX_HIGHLIGHT = QColor(255, 214, 0, 230)
