"""`SheetItem`: the white sheet with its 1x1 grid, drawn in scene (= cube) units."""

import math

from PyQt6.QtCore import QLineF, QRectF
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.ui import palette


class SheetItem(QGraphicsItem):
    """Draws the sheet rectangle and grid lines at every integer coordinate inside it.

    Lines are cosmetic (1 pixel wide at any zoom). The cube net will be drawn on top and hide the grid.
    """

    def __init__(self, rect: QRectF | None = None) -> None:
        super().__init__()
        self._rect = QRectF() if rect is None else QRectF(rect)
        self.setZValue(-100)

    def set_rect(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self._rect = QRectF(rect)
        self.update()

    def rect(self) -> QRectF:
        return QRectF(self._rect)

    def boundingRect(self) -> QRectF:
        return QRectF(self._rect)

    def paint(
        self, painter: QPainter | None, option: QStyleOptionGraphicsItem | None, widget: QWidget | None = None
    ) -> None:
        if painter is None or self._rect.isEmpty():
            return
        r = self._rect
        painter.fillRect(r, palette.SHEET)

        grid_pen = QPen(palette.GRID, 0)  # width 0 = cosmetic 1 px
        painter.setPen(grid_pen)
        lines = [QLineF(x, r.top(), x, r.bottom()) for x in range(math.ceil(r.left()), math.floor(r.right()) + 1)]
        lines += [QLineF(r.left(), y, r.right(), y) for y in range(math.ceil(r.top()), math.floor(r.bottom()) + 1)]
        painter.drawLines(lines)

        painter.setPen(QPen(palette.SHEET_BORDER, 0))
        painter.drawRect(r)
