# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`SheetContextMenu`: a right click on the sheet opens a menu wherever at least one of its items can be chosen there
(whatever the state: the user asked for that on 2026-11-20, after a fold line being drawn had none), and nowhere else:
- "Place a vertex" opens `PlaceVertexWindow` for the point a click there would make (where the dragged point is).
  Disabled where there's nothing to place (no point would be made, or it would be a vertex, whose coordinates are
  fixed). Cancel there also unlocks a locked slope;
- "Set slope" opens `SetSlopeWindow` for the current segment (the one a click would make; the dragged point's, from
  the point before it): set, the slope is locked until the point is placed or the drag ends. Disabled where there's
  no such segment (DEFAULT, the first point dragged, the mouse right on the previous point). Set during a drag, the
  drag goes on without its button (released meanwhile): the next click puts the point.
- "Move the origin" opens `MoveOriginWindow` for the drawn point under the mouse (the one the coordinates hint is
  about): the origin moves so that the point has the typed coordinates (`Origin`). Disabled where there's no such
  point, and while a point is dragged.
- In a template (with `TemplateTool`), "Assign the vertex" too, for the vertex under the mouse: what to do is the
  window's (`assign`). Disabled where there's no vertex, while the loop isn't closed yet, and while a vertex is dragged.

The menu is the application's own (`ContextMenu`), drawn in the window: on Wayland, a system popup can't open while the
drag's button is held. The menu and the window take the mouse, so a drag can't go on after them: placing the point ends
it there, anything else (Cancel, closing the menu or the window) ends it with the point back where it was. Only the main
window has this: the animations of Help -> Help don't.

While the window is open, the mouse over the sheet shows what it always shows (the footer's coordinates, the
coordinates hint): the view follows it (`SheetView.follow_cursor`), as the window keeps the
mouse's real moves from it. A point being dragged stays put meanwhile (`CutTool.freeze_drag`); for the line's next
point bound to a line, the dashed line to the mouse ends on that line, within an edge's or a fold's ends
(`CutTool.set_placing`).
"""

from collections.abc import Callable

from PyQt6.QtCore import QObject, QPointF

from cube_net.core.cutting import slope_of
from cube_net.core.cutting.placement import Placement
from cube_net.core.geometry import Vec
from cube_net.ui.context_menu import ContextMenu, MenuItem
from cube_net.ui.i18n import tr
from cube_net.ui.sheet.cut_tool import CutTool
from cube_net.ui.sheet.move_origin_window import MoveOriginWindow
from cube_net.ui.sheet.place_vertex_window import PlaceVertexWindow
from cube_net.ui.sheet.set_slope_window import SetSlopeWindow
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.template.template_tool import TemplateTool

# The menu's items, in their order.
PLACE_VERTEX = 0
SET_SLOPE = 1
MOVE_ORIGIN = 2
ASSIGN_VERTEX = 3


class SheetContextMenu(QObject):
    def __init__(
        self, view: SheetView, cut_tool: CutTool | TemplateTool, assign: Callable[[Vec], None] | None = None
    ) -> None:
        """`assign`: a template's Assign the vertex, for the vertex at a sheet point (None: not offered)."""
        super().__init__(view)
        self._view = view
        self._cut_tool = cut_tool
        self._assign = assign

        # The name of a drawn point (sheet coordinates), if it has one: what undoing a move of the origin tells.
        self.point_name: Callable[[Vec], str | None] = lambda _point: None

        view.right_pressed.connect(self._on_right_pressed)

    def items(self, placement: Placement | None, slope: Vec | None, vertex: Vec | None = None) -> list[MenuItem]:
        """The menu's items: "Place a vertex" (disabled without a placement), "Set slope" (disabled without a segment),
        "Move the origin" (disabled without a drawn point), and in a template "Assign the vertex"."""
        items = [
            MenuItem(tr("Place a vertex"), placement is not None),
            MenuItem(tr("Set slope"), slope is not None),
            MenuItem(tr("Move the origin"), vertex is not None),
        ]
        if self._assign is not None:
            assignable = isinstance(self._cut_tool, TemplateTool) and self._cut_tool.can_assign()
            items.append(MenuItem(tr("Assign the vertex"), assignable and vertex is not None))
        return items

    def items_at(self, x: float, y: float) -> list[MenuItem]:
        """The items for a right click at sheet point (x, y)."""
        vertex = self._cut_tool.vertex_at(x, y)
        return self.items(self._cut_tool.placement_at(x, y), self._cut_tool.slope_at(x, y), vertex)

    def offered_at(self, x: float, y: float) -> bool:
        """Is there a menu for a right click here: can any of its items be chosen?"""
        return any(item.enabled for item in self.items_at(x, y))

    def menu(self, placement: Placement | None, slope: Vec | None, vertex: Vec | None = None) -> ContextMenu:
        """The menu (`items`): the application's own (`ContextMenu`), not a system popup: on Wayland, one can't open
        while the drag's button is held."""
        window = self._view.window()
        assert window is not None
        return ContextMenu(window, self.items(placement, slope, vertex))

    def _on_right_pressed(self, x: float, y: float) -> None:
        vertex = self._cut_tool.vertex_at(x, y)
        placement = self._cut_tool.placement_at(x, y)
        slope = self._cut_tool.slope_at(x, y)
        if not any(item.enabled for item in self.items(placement, slope, vertex)):
            return  # nothing could be chosen: no menu
        menu = self.menu(placement, slope, vertex)
        viewport = self._view.viewport()
        window = self._view.window()
        assert viewport is not None and window is not None
        at = viewport.mapTo(window, self._view.from_sheet(QPointF(x, y)).toPoint())  # no screen coordinates: Wayland
        self._cut_tool.freeze_drag(True)
        try:
            chosen = menu.choose(at)
        finally:
            self._cut_tool.freeze_drag(False)
            menu.deleteLater()
        if chosen == PLACE_VERTEX and placement is not None:
            self.open_window(placement)
        elif chosen == SET_SLOPE and slope is not None:
            self.open_slope_window(slope)
        elif chosen == MOVE_ORIGIN and vertex is not None:
            self.open_origin_window(vertex)
        elif chosen == ASSIGN_VERTEX and vertex is not None and self._assign is not None:
            self._assign(vertex)
        elif self._cut_tool.dragging:
            self._cut_tool.cancel_drag()

    def open_window(self, placement: Placement) -> bool:
        """The window for `placement`; whether the point was placed (if not, a drag ends with the point back)."""
        origin = self._cut_tool.editor.origin
        window = PlaceVertexWindow(
            placement, lambda p: self._cut_tool.place(placement, p), self._view.window(), origin=origin
        )
        self._cut_tool.freeze_drag(True)
        self._cut_tool.set_placing(placement)
        self._view.follow_cursor(window)
        try:
            placed = window.exec() == PlaceVertexWindow.DialogCode.Accepted
        finally:
            self._view.follow_cursor(None)
            self._cut_tool.set_placing(None)
            self._cut_tool.freeze_drag(False)
        window.deleteLater()
        if not placed:
            self._cut_tool.unlock_slope()
            if self._cut_tool.dragging:
                self._cut_tool.cancel_drag()
        return placed

    def open_slope_window(self, slope: Vec) -> bool:
        """The window for the current segment's slope (`slope`: its direction now); whether a slope was set (if not,
        a drag ends with the point back)."""
        y, x = slope_of(slope)
        window = SetSlopeWindow(y, x, self._view.window())
        self._cut_tool.freeze_drag(True)
        self._view.follow_cursor(window)
        try:
            accepted = window.exec() == SetSlopeWindow.DialogCode.Accepted
        finally:
            self._view.follow_cursor(None)
            self._cut_tool.freeze_drag(False)
        direction = window.direction()
        window.deleteLater()
        if accepted and direction is not None:
            if self._cut_tool.dragging:
                self._cut_tool.continue_drag_without_button()  # its button was released meanwhile
            self._cut_tool.lock_slope(direction)
        elif self._cut_tool.dragging:
            self._cut_tool.cancel_drag()
        return accepted

    def open_origin_window(self, vertex: Vec) -> bool:
        """The window for the drawn point `vertex` (sheet coordinates); whether the coordinates were given (the origin
        moves only if they differ from the point's coordinates now)."""
        origin = self._cut_tool.editor.origin
        window = MoveOriginWindow(origin.shown(vertex), self._view.window())
        self._view.follow_cursor(window)
        try:
            accepted = window.exec() == MoveOriginWindow.DialogCode.Accepted
        finally:
            self._view.follow_cursor(None)
        coordinates = window.coordinates()
        window.deleteLater()
        if accepted and coordinates is not None:
            self._cut_tool.move_origin(origin.moved(vertex, coordinates, self.point_name(vertex)))
        return accepted
