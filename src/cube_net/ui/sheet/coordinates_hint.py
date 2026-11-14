# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`CoordinatesHint`: a point's exact coordinates next to the mouse, in a translucent box (docs/idea.txt).

It's drawn inside the sheet view (a child of its viewport), not as a window of its own: so it's translucent on every
system (a window's transparency depends on the desktop), never takes the mouse, and shows and goes in the same frame
as what it describes. It sits above and to the right of the mouse; where it wouldn't fit in the view, to the left of
the mouse, or below it.
"""

from PyQt6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QFont, QFontDatabase, QFontMetrics, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

from cube_net.ui import palette
from cube_net.ui.sheet import net_style

# How round the box's corners are (px).
CORNER_RADIUS_PX = 3.0


def hint_font() -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setPixelSize(net_style.COORDINATES_FONT_PX)
    return font


def hint_place(mouse: QPoint, size: QSize, area: QSize) -> QPoint:
    """Where the box's top-left corner goes, for the mouse at `mouse` in an area of `area` (both in the view's
    pixels): above and to the right of the mouse; to its left if it doesn't fit on the right, below it if it doesn't
    fit above."""
    offset = net_style.COORDINATES_OFFSET_PX
    x = mouse.x() + offset
    if x + size.width() > area.width():
        x = mouse.x() - offset - size.width()
    y = mouse.y() - offset - size.height()
    if y < 0:
        y = mouse.y() + offset
    return QPoint(max(0, x), max(0, y))


class CoordinatesHint(QWidget):
    def __init__(self, viewport: QWidget) -> None:
        super().__init__(viewport)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._lines: list[str] = []
        self.hide()

    def lines(self) -> list[str]:
        """What it shows (empty: it's hidden)."""
        return list(self._lines) if self.isVisible() else []

    def show_at(self, lines: list[str], mouse: QPoint) -> None:
        """Show `lines` next to the mouse at `mouse` (the viewport's pixels)."""
        metrics = QFontMetrics(hint_font())
        padding = net_style.COORDINATES_PADDING_PX
        width = max(metrics.horizontalAdvance(line) for line in lines) + 2 * padding
        height = metrics.lineSpacing() * len(lines) + 2 * padding
        self._lines = lines
        self.resize(width, height)
        parent = self.parentWidget()
        assert parent is not None
        self.move(hint_place(mouse, self.size(), parent.size()))
        self.show()
        self.raise_()
        self.update()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(palette.COORDINATES_BORDER, 1))
        painter.setBrush(palette.COORDINATES_BACKGROUND)
        painter.drawRoundedRect(box, CORNER_RADIUS_PX, CORNER_RADIUS_PX)
        font = hint_font()
        painter.setFont(font)
        painter.setPen(palette.COORDINATES_TEXT)
        metrics = QFontMetrics(font)
        padding = net_style.COORDINATES_PADDING_PX
        for i, line in enumerate(self._lines):
            baseline = padding + i * metrics.lineSpacing() + metrics.ascent()
            painter.drawText(QPointF(padding, baseline), line)
        painter.end()
