# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`RulerTool`: the ruler instrument (docs/idea.txt).

While active, every left click on the sheet adds a measured point (rounded to 1/1000 unit like all input), and
dragging doesn't pan the view. With SHIFT held, the segment to the mouse is restricted (see `restricted_point`), at once
when SHIFT is pressed or released. Deactivating forgets the points. Nothing of the ruler is saved or undoable.
"""

from PyQt6.QtCore import QObject, QPointF, pyqtSignal

from cube_net.core.geometry import Vec, quantize
from cube_net.core.ruler import Ruler, restricted_point
from cube_net.ui.sheet import ruler_style
from cube_net.ui.sheet.ruler_item import RulerItem
from cube_net.ui.sheet.sheet_view import SheetView


class RulerTool(QObject):
    # A point was added to the ruler.
    point_added = pyqtSignal(Vec)

    # The placed points changed (a point was added, or the ruler was switched on or off).
    points_changed = pyqtSignal()

    def __init__(self, view: SheetView) -> None:
        super().__init__(view)
        self._view = view
        self._ruler = Ruler()
        self._cursor: Vec | None = None
        self._mouse: tuple[float, float] | None = None
        self._active = False
        self.item = RulerItem()
        scene = view.scene()
        assert scene is not None
        scene.addItem(self.item)
        view.left_pressed.connect(self._on_left_pressed)
        view.mouse_moved.connect(self._on_mouse_moved)
        view.mouse_left.connect(self._on_mouse_left)
        view.zoom_changed.connect(self._update_area)
        view.shift_changed.connect(self._on_shift_changed)

    @property
    def active(self) -> bool:
        return self._active

    @property
    def ruler(self) -> Ruler:
        return self._ruler

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        self._ruler.clear()
        self._cursor = None
        self._view.set_panning_enabled(not active)
        self._update_area()
        self._refresh()
        self.points_changed.emit()

    def total_length(self) -> float | None:
        """Total length of the placed segments, or None if no point is placed yet."""
        return self._ruler.total_length() if self._ruler.points else None

    def _target(self, x: float, y: float) -> Vec | None:
        """Where a point would go for the mouse at (x, y): None if that's off the sheet."""
        point = quantize(x, y)
        if self._view.shift_held():
            point = restricted_point(self._ruler.points, point)
        return point if self._view.sheet_rect().contains(QPointF(float(point.x), float(point.y))) else None

    def _on_left_pressed(self, x: float, y: float) -> None:
        if not self._active:
            return
        self._mouse = x, y
        point = self._target(x, y)
        if point is None:
            return
        self._ruler.add(point)
        self._cursor = point
        self._refresh()
        self.point_added.emit(point)
        self.points_changed.emit()

    def _on_mouse_moved(self, x: float, y: float) -> None:
        if not self._active:
            return
        self._mouse = x, y
        self._cursor = self._target(x, y)
        self._refresh()

    def _on_mouse_left(self) -> None:
        self._mouse = None
        if self._active:
            self._cursor = None
            self._refresh()

    def _on_shift_changed(self) -> None:
        if self._active and self._mouse is not None:
            self._on_mouse_moved(*self._mouse)

    def _update_area(self, *_: object) -> None:
        """The sheet, plus room for labels that stick out of it (a fixed number of pixels at the current zoom)."""
        self.item.set_rect(self._view.sheet_rect(), ruler_style.LABEL_REACH_PX / self._view.scale_factor())

    def _refresh(self) -> None:
        self.item.set_state(self._ruler.points if self._active else (), self._cursor if self._active else None)
