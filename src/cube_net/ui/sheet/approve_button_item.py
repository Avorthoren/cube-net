# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`ApproveButtonItem`: the round button in the middle of the segment chosen for gluing (CUT_APPROVING).

A green check mark when the rearrangement can be approved, a grey "x" when it can't (clicking it undoes the
rearrangement then). It looks raised, like a button, and has a constant size in pixels.
"""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QLinearGradient, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.geometry import Vec
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style

# How far the arms of the "x" reach from the centre along each axis, as a share of the button's radius.
CROSS_ARM = 0.4


class ApproveButtonItem(QGraphicsItem):
    def __init__(self) -> None:
        super().__init__()
        self.setZValue(200)  # above everything else on the sheet
        self._area = QRectF()
        self._position: Vec | None = None
        self._enabled = False
        self._pressed = False

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

    def set_pressed(self, pressed: bool) -> None:
        """Shown pushed in: the mouse button is down on it (it acts when it's released there)."""
        if pressed != self._pressed:
            self._pressed = pressed
            self.update()

    def pressed(self) -> bool:
        return self._pressed

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
        # Raised: a soft shadow below it, lit from above, and a rim a little darker than the symbol. Pressed: pushed
        # down onto the sheet (no shadow, a little lower) and lit from below, like a hollow.
        shadow = net_style.APPROVE_BUTTON_SHADOW_PX
        if self._pressed:
            center = center + QPointF(0, shadow / 2)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(palette.APPROVE_BUTTON_SHADOW)
            painter.drawEllipse(center + QPointF(0, shadow), r + shadow / 2, r + shadow / 2)
        light = QLinearGradient(center + QPointF(0, -r), center + QPointF(0, r))
        top, bottom = palette.APPROVE_BUTTON_FILL, palette.APPROVE_BUTTON_SHADE
        if self._pressed:  # in the button's own shadow: darker, and darkest at the top edge
            top, bottom = palette.APPROVE_BUTTON_PRESSED_TOP, palette.APPROVE_BUTTON_SHADE
        light.setColorAt(0, top)
        light.setColorAt(1, bottom)
        painter.setPen(QPen(colour.darker(115), net_style.APPROVE_CHECK_WIDTH_PX))
        painter.setBrush(QBrush(light))
        painter.drawEllipse(center, r, r)
        pen = QPen(colour, net_style.APPROVE_CHECK_WIDTH_PX)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        if self._enabled:
            check = [QPointF(-0.5, 0.05), QPointF(-0.12, 0.42), QPointF(0.5, -0.35)]
            painter.drawPolyline(QPolygonF([center + p * r for p in check]))
        else:
            arm = CROSS_ARM * r
            painter.drawLine(center + QPointF(-arm, -arm), center + QPointF(arm, arm))
            painter.drawLine(center + QPointF(-arm, arm), center + QPointF(arm, -arm))
        painter.restore()
