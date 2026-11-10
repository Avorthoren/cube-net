# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`TooltipLabel`: a tooltip that looks like the usual ones, but that's shown and hidden exactly when it's told.

Qt's own tooltip (`QToolTip`) lingers for 300 ms after it's told to hide, and only a graphics view's items can have
ordinary tooltips on the sheet.
"""

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QLabel, QToolTip, QWidget

# Where the tooltip goes, from the mouse: below and to the right of it, clear of the cursor.
OFFSET_PX = QPoint(12, 18)


class TooltipLabel(QLabel):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent, Qt.WindowType.ToolTip)
        self.setPalette(QToolTip.palette())
        self.setFont(QToolTip.font())
        self.setAutoFillBackground(True)
        self.setMargin(4)
        self.setFrameShape(QLabel.Shape.Box)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def show_at(self, text: str, global_mouse: QPoint) -> None:
        """Show `text` next to the mouse (screen coordinates)."""
        self.setText(text)
        self.adjustSize()
        self.move(global_mouse + OFFSET_PX)
        self.show()
        self.raise_()
