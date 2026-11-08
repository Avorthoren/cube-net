"""`SheetView`: shows the sheet; handles zoom, scrolling, panning and mouse coordinates (docs/plan.md, section 6.2).

Scene coordinates are cube units with the Y axis pointing up (the view's transform is `scale(s, -s)`), so positions
from the core are used as-is.
"""

from collections.abc import Callable

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QMoveEvent, QPainter, QResizeEvent, QShowEvent, QTransform, QWheelEvent
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget

from cube_net.core.geometry import Box
from cube_net.core.labels import VertexLabel
from cube_net.core.net import Net, NetVertex
from cube_net.ui import palette
from cube_net.ui.sheet import zoom
from cube_net.ui.sheet.net_item import NetItem
from cube_net.ui.sheet.sheet_item import SheetItem

type HitTest = Callable[[float, float], bool]
"""Tells whether a sheet point (x, y) lies on the cube net."""


def _to_rect(box: Box) -> QRectF:
    return QRectF(float(box.lo.x), float(box.lo.y), float(box.width), float(box.height))


class SheetView(QGraphicsView):
    # Mouse position in sheet coordinates (emitted on every move over the view).
    mouse_moved = pyqtSignal(float, float)

    # The mouse left the view.
    mouse_left = pyqtSignal()

    # Left button pressed at a sheet point (x, y) that doesn't start panning.
    left_pressed = pyqtSignal(float, float)

    # Left button released at a sheet point (x, y), unless it ended panning.
    left_released = pyqtSignal(float, float)

    # The zoom changed: new scale in pixels per unit.
    zoom_changed = pyqtSignal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self._sheet_item = SheetItem()
        self._scene().addItem(self._sheet_item)
        self._net_item: NetItem | None = None

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)  # zoom anchoring is done manually
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setBackgroundBrush(palette.MAIN_AREA)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        self._scale = 1.0
        self._sheet = QRectF()
        self._press_claim: HitTest = lambda _x, _y: False
        self._pan_last: QPoint | None = None
        self._panning_enabled = True
        self._press_modifiers = Qt.KeyboardModifier.NoModifier
        self._pending_initial_view: Box | None = None
        # Where the viewport's top-left corner was in the window, so the sheet can be kept in place when it moves.
        self._viewport_origin: QPoint | None = None
        self._apply_transform()

    # --- setup ------------------------------------------------------------------------------------------------------

    def set_sheet(self, sheet: Box) -> None:
        """Set the sheet rectangle (in units). The current zoom is clamped to the new limits. What's on screen stays
        where it is, as far as the zoom allows."""
        anchor = self.to_sheet(QPointF(0, 0))
        self._sheet = _to_rect(sheet)
        self._sheet_item.set_rect(self._sheet)
        self._scale = zoom.clamp_scale(self._scale, self.zoom_limits())
        self._apply_transform()
        if self.isVisible():
            drift = self.from_sheet(anchor)
            self.pan_by(drift.x(), drift.y())

    def set_net(self, net: Net) -> None:
        """Show `net` on the sheet (replacing the previous one)."""
        if self._net_item is None:
            self._net_item = NetItem(net)
            self._scene().addItem(self._net_item)
        else:
            self._net_item.set_net(net)

    def set_vertex_labels(self, labels: dict[NetVertex, VertexLabel] | None) -> None:
        """Debug labels next to the net's vertices (None: hide them)."""
        if self._net_item is not None:
            self._net_item.set_labels(labels)

    def net_item(self) -> NetItem | None:
        return self._net_item

    def set_panning_enabled(self, enabled: bool) -> None:
        """Dragging from where a press means nothing pans the view only when enabled (e.g. not while the ruler is
        active)."""
        self._panning_enabled = enabled

    def set_press_claim(self, claim: HitTest) -> None:
        """Tells where a press of the left button means something. Dragging from anywhere else pans the view."""
        self._press_claim = claim

    def show_initial_view(self, net: Box) -> None:
        """Zoom so that the net takes 50% of the screen height and center it. Deferred until the view is shown."""
        if not self.isVisible():
            self._pending_initial_view = net
            return
        self._pending_initial_view = None
        self._scale = zoom.clamp_scale(zoom.initial_scale(self._screen_height(), float(net.height)), self.zoom_limits())
        self._apply_transform()
        self.centerOn(float(net.center.x), float(net.center.y))
        self._viewport_origin = self._viewport_origin_in_window()

    # --- queries ----------------------------------------------------------------------------------------------------

    def scale_factor(self) -> float:
        """Current zoom: screen pixels per unit."""
        return self._scale

    def sheet_rect(self) -> QRectF:
        return QRectF(self._sheet)

    def press_modifiers(self) -> Qt.KeyboardModifier:
        """The modifier keys held during the latest mouse press."""
        return self._press_modifiers

    def is_panning(self) -> bool:
        """Whether the user is dragging the sheet right now."""
        return self._pan_last is not None

    def press_claimed(self, x: float, y: float) -> bool:
        """Does a press at sheet point (x, y) mean something (so that it can't start panning)?"""
        return self._press_claim(x, y)

    def zoom_limits(self) -> tuple[float, float]:
        if self._sheet.isEmpty():
            return (0.0, float("inf"))
        return zoom.zoom_limits(self._screen_height(), self._sheet.width(), self._sheet.height())

    def to_sheet(self, viewport_pos: QPointF) -> QPointF:
        """Viewport pixel position -> sheet coordinates (units, Y up)."""
        inverted, _ = self.viewportTransform().inverted()
        return inverted.map(viewport_pos)

    def from_sheet(self, sheet_pos: QPointF) -> QPointF:
        """Sheet coordinates -> viewport pixel position."""
        return self.viewportTransform().map(sheet_pos)

    # --- actions ----------------------------------------------------------------------------------------------------

    def zoom_by(self, factor: float, viewport_pos: QPointF) -> bool:
        """Zoom by `factor`, keeping the sheet point under `viewport_pos` fixed. Returns False if clamped to no-op."""
        anchor = self.to_sheet(viewport_pos)
        new_scale = zoom.clamp_scale(self._scale * factor, self.zoom_limits())
        if new_scale == self._scale:
            return False
        self._scale = new_scale
        self._apply_transform()
        drift = self.from_sheet(anchor) - viewport_pos
        self.pan_by(drift.x(), drift.y())
        return True

    def pan_by(self, dx: float, dy: float) -> None:
        """Scroll the view by (dx, dy) pixels: positive dx shows content further to the right."""
        h, v = self.horizontalScrollBar(), self.verticalScrollBar()
        if h is not None:
            h.setValue(h.value() + round(dx))
        if v is not None:
            v.setValue(v.value() + round(dy))

    # --- Qt events --------------------------------------------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        if event is None:
            return
        pos = event.position()
        if self._sheet.contains(self.to_sheet(pos)):
            self.zoom_by(zoom.WHEEL_STEP ** (event.angleDelta().y() / 120), pos)
            event.accept()
        else:
            super().wheelEvent(event)  # outside the sheet the wheel just scrolls

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            return
        self._press_modifiers = event.modifiers()
        if event.button() == Qt.MouseButton.LeftButton:
            p = self.to_sheet(event.position())
            if self._panning_enabled and not self.press_claimed(p.x(), p.y()):
                self._pan_last = event.position().toPoint()
                self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self.left_pressed.emit(p.x(), p.y())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            return
        pos = event.position()
        if self._pan_last is not None:
            delta = pos.toPoint() - self._pan_last
            self._pan_last = pos.toPoint()
            self.pan_by(-delta.x(), -delta.y())
        p = self.to_sheet(pos)
        self.mouse_moved.emit(p.x(), p.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            if self._pan_last is not None:
                self._pan_last = None
                self.viewport().unsetCursor()
            else:
                p = self.to_sheet(event.position())
                self.left_released.emit(p.x(), p.y())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event: object) -> None:
        self.mouse_left.emit()
        super().leaveEvent(event)  # type: ignore[arg-type]

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._update_scene_rect()
        self._keep_sheet_in_place()

    def moveEvent(self, event: QMoveEvent | None) -> None:
        super().moveEvent(event)
        self._keep_sheet_in_place()

    def showEvent(self, event: QShowEvent | None) -> None:
        super().showEvent(event)
        if self._pending_initial_view is not None:
            self.show_initial_view(self._pending_initial_view)

    # --- internals --------------------------------------------------------------------------------------------------

    def _viewport_origin_in_window(self) -> QPoint:
        return self.viewport().mapTo(self.window(), QPoint(0, 0))

    def _keep_sheet_in_place(self) -> None:
        """When the view moves or changes size inside its window (e.g. the instrument panel next to it gets wider),
        scroll by the same amount, so the sheet stays where it was on the screen.

        Measured relative to the window, not the screen: moving the whole window moves the sheet with it, as it should.
        """
        if not self.isVisible():
            return
        origin = self._viewport_origin_in_window()
        if self._viewport_origin is not None:
            shift = origin - self._viewport_origin
            if not shift.isNull():
                self.pan_by(shift.x(), shift.y())
        self._viewport_origin = origin

    def _scene(self) -> QGraphicsScene:
        scene = self.scene()
        assert scene is not None
        return scene

    def _screen_height(self) -> float:
        screen = self.screen()
        return float(screen.geometry().height()) if screen is not None else 1080.0

    def _apply_transform(self) -> None:
        self.setTransform(QTransform.fromScale(self._scale, -self._scale))
        self._update_scene_rect()
        self.zoom_changed.emit(self._scale)

    def _update_scene_rect(self) -> None:
        """The scene extends one viewport beyond the sheet on every side, so any part of the sheet can be scrolled to
        any place of the viewport (needed for zooming around the cursor near the sheet's edges)."""
        if self._sheet.isEmpty():
            return
        viewport = self.viewport()
        if viewport is None:
            return
        mx = viewport.width() / self._scale
        my = viewport.height() / self._scale
        self.setSceneRect(self._sheet.adjusted(-mx, -my, mx, my))
