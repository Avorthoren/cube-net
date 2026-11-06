"""Colours used by the UI (docs/idea.txt; docs/plan.md, section 6.5)."""

from types import MappingProxyType

from PyQt6.QtGui import QColor

MAIN_AREA = QColor("#9AA0A6")
"""Background of the main area around the sheet."""
SHEET = QColor("#FFFFFF")
SHEET_BORDER = QColor("#5F6368")
GRID = QColor("#D3D3D3")
"""Thin light-grey 1x1 grid on the sheet."""

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
WHITE = QColor("#FFFFFF")
"""Second colour of the hatch pattern and of dashes of cuts inside a face."""
VERTEX_OUTLINE = QColor("#3C4043")
"""Thin outline of vertex circles, so that sectors stand out on similar colours."""
