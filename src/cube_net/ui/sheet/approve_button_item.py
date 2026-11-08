"""`ApproveButtonItem`: the round check mark in the middle of the segment chosen for gluing (CUT_APPROVING).

Green when the rearrangement can be approved, grey when it can't. It has a constant size in pixels.
"""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.geometry import Vec
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style


class ApproveButtonItem(QGraphicsItem):
    def __init__(self) -> None:
        super().__init__()
        self.setZValue(200)  # above everything else on the sheet
        self._area = QRectF()
        self._position: Vec | None = None
        self._enabled = False

    def set_area(self, rect: QRectF) -> None:
        """Everything the item can paint on (the sheet plus room for its pixel size)."""
        self.prepareGeometryChange()
        self._area = QRectF(rect)

    def set_state(self, position: Vec | None, enabled: bool) -> None:
        """Where the button is (None: not shown) and whether it can be clicked."""
        self._position = position
        self._enabled = enabled
        self.update()

    def position(self) -> Vec | None:
        return self._position

    def enabled(self) -> bool:
        return self._enabled

    def boundingRect(self) -> QRectF:
        return QRectF(self._area)

    def paint(
        self, painter: QPainter | None, option: QStyleOptionGraphicsItem | None, widget: QWidget | None = None
    ) -> None:
        if painter is None or self._position is None:
            return
        center = painter.worldTransform().map(to_qpointf(self._position))
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colour = palette.SUCCESS if self._enabled else palette.APPROVE_BUTTON_DISABLED
        r = net_style.APPROVE_BUTTON_RADIUS_PX
        painter.setPen(QPen(colour, net_style.APPROVE_CHECK_WIDTH_PX))
        painter.setBrush(palette.APPROVE_BUTTON_FILL)
        painter.drawEllipse(center, r, r)
        pen = QPen(colour, net_style.APPROVE_CHECK_WIDTH_PX)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        check = [QPointF(-0.5, 0.05), QPointF(-0.12, 0.42), QPointF(0.5, -0.35)]
        painter.drawPolyline(QPolygonF([center + p * r for p in check]))
        painter.restore()
