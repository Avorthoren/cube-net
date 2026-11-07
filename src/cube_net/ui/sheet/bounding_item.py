"""`BoundingItem`: draws the minimum-area bounding rectangle (docs/idea.txt): a thin line, green on success."""

from collections.abc import Sequence

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.geometry import Box, Vec
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style


class BoundingItem(QGraphicsItem):
    def __init__(self) -> None:
        super().__init__()
        self.setZValue(50)  # above the net, below the ruler
        self._corners: tuple[Vec, ...] = ()
        self._success = False

    def set_rectangle(self, corners: Sequence[Vec] | None, success: bool) -> None:
        """The rectangle to draw (None: draw nothing) and whether its area is below the threshold."""
        self.prepareGeometryChange()
        self._corners = tuple(corners) if corners is not None else ()
        self._success = success
        self.update()

    def corners(self) -> tuple[Vec, ...]:
        return self._corners

    def success(self) -> bool:
        return self._success

    def boundingRect(self) -> QRectF:
        if not self._corners:
            return QRectF()
        box = Box.around(self._corners).expanded(1)  # room for the line width at any reasonable zoom
        return QRectF(float(box.lo.x), float(box.lo.y), float(box.width), float(box.height))

    def paint(
        self, painter: QPainter | None, option: QStyleOptionGraphicsItem | None, widget: QWidget | None = None
    ) -> None:
        if painter is None or not self._corners:
            return
        world = painter.worldTransform()
        painter.save()
        painter.resetTransform()  # constant pixel width
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colour = palette.SUCCESS if self._success else palette.BOUNDING_RECTANGLE
        painter.setPen(QPen(colour, net_style.BOUNDING_LINE_PX))
        painter.drawPolygon(QPolygonF([world.map(to_qpointf(c)) for c in self._corners]))
        painter.restore()
