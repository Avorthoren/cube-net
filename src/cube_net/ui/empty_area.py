# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`EmptyArea`: what the window shows in place of the sheet while no project or template is open (at start, until
one is opened or started, or when none could be): just the grey of the area around the sheet."""

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QWidget

from cube_net.ui import palette


class EmptyArea(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        colours = self.palette()
        colours.setColor(QPalette.ColorRole.Window, palette.MAIN_AREA)
        self.setPalette(colours)
        self.setAutoFillBackground(True)
