"""`SheetView`: shows the sheet; handles zoom, scrolling, panning and mouse coordinates (docs/plan.md, section 6.2).

Scene coordinates are cube units with the Y axis pointing up (the view's transform is `scale(s, -s)`), so positions
from the core are used as-is.
"""

from collections.abc import Callable

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter, QResizeEvent, QShowEvent, QTransform, QWheelEvent
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget

from cube_net.core.geometry import Box
from cube_net.ui import palette
from cube_net.ui.sheet import zoom
from cube_net.ui.sheet.sheet_item import SheetItem

type HitTest = Callable[[float, float], bool]
"""Tells whether a sheet point (x, y) lies on the cube net."""


def _to_rect(box: Box) -> QRectF:
    return QRectF(float(box.lo.x), float(box.lo.y), float(box.width), float(box.height))


class SheetView(QGraphicsView):
    mouse_moved = pyqtSignal(float, float)
    """Mouse position in sheet coordinates (emitted on every move over the view)."""
    mouse_left = pyqtSignal()
    """The mouse left the view."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self._sheet_item = SheetItem()
        self._scene().addItem(self._sheet_item)

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
        self._on_net: HitTest = lambda _x, _y: False
        self._pan_last: QPoint | None = None
        self._pending_initial_view: Box | None = None
        self._apply_transform()

    # --- setup ------------------------------------------------------------------------------------------------------

    def set_sheet(self, sheet: Box) -> None:
        """Set the sheet rectangle (in units). The current zoom is clamped to the new limits."""
        self._sheet = _to_rect(sheet)
        self._sheet_item.set_rect(self._sheet)
        self._scale = zoom.clamp_scale(self._scale, self.zoom_limits())
        self._apply_transform()

    def set_net_hit_test(self, on_net: HitTest) -> None:
        """Panning by dragging is only allowed outside the cube net; this tells where the net is."""
        self._on_net = on_net

    def show_initial_view(self, net: Box) -> None:
        """Zoom so that the net takes 50% of the screen height and center it. Deferred until the view is shown."""
        if not self.isVisible():
            self._pending_initial_view = net
            return
        self._pending_initial_view = None
        self._scale = zoom.clamp_scale(zoom.initial_scale(self._screen_height(), float(net.height)), self.zoom_limits())
        self._apply_transform()
        self.centerOn(float(net.center.x), float(net.center.y))

    # --- queries ----------------------------------------------------------------------------------------------------

    def scale_factor(self) -> float:
        """Current zoom: screen pixels per unit."""
        return self._scale

    def sheet_rect(self) -> QRectF:
        return QRectF(self._sheet)

    def is_on_net(self, x: float, y: float) -> bool:
        """Whether the sheet point (x, y) lies on the cube net."""
        return self._on_net(x, y)

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
        if event.button() == Qt.MouseButton.LeftButton:
            p = self.to_sheet(event.position())
            if not self.is_on_net(p.x(), p.y()):
                self._pan_last = event.position().toPoint()
                self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
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
        if event is not None and event.button() == Qt.MouseButton.LeftButton and self._pan_last is not None:
            self._pan_last = None
            self.viewport().unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event: object) -> None:
        self.mouse_left.emit()
        super().leaveEvent(event)  # type: ignore[arg-type]

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._update_scene_rect()

    def showEvent(self, event: QShowEvent | None) -> None:
        super().showEvent(event)
        if self._pending_initial_view is not None:
            self.show_initial_view(self._pending_initial_view)

    # --- internals --------------------------------------------------------------------------------------------------

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
