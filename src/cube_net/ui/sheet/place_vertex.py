# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`PlaceVertex`: a right click on the sheet opens a menu with "Place a vertex" (docs/idea.txt), in DEFAULT and
CUTTING, and while a point is being dragged in CUT_EDITING. Chosen, it opens `PlaceVertexWindow` for the point a click
there would make (where the dragged point is). Where there's nothing to place (no point would be made, or it would be
a vertex, whose coordinates are fixed), the item is there but disabled.

The menu is the application's own (`ContextMenu`), drawn in the window: on Wayland, a system popup can't open while the
drag's button is held. The menu and the window take the mouse, so a drag can't go on after them: placing the point ends
it there, anything else (Cancel, closing the menu or the window) ends it with the point back where it was. Only the main
window has this: the animations of Help -> Help don't.

While the window is open, the mouse over the sheet shows what it always shows (the footer's coordinates, the
coordinates hint): the view follows it (`SheetView.follow_cursor`), as the window keeps the
mouse's real moves from it. A point being dragged stays put meanwhile (`CutTool.freeze_drag`).
"""

from PyQt6.QtCore import QObject, QPointF

from cube_net.core.cutting.placement import Placement
from cube_net.core.editor import EditorState
from cube_net.ui.context_menu import ContextMenu, MenuItem
from cube_net.ui.i18n import tr
from cube_net.ui.sheet.cut_tool import CutTool
from cube_net.ui.sheet.place_vertex_window import PlaceVertexWindow
from cube_net.ui.sheet.sheet_view import SheetView


class PlaceVertex(QObject):
    def __init__(self, view: SheetView, cut_tool: CutTool) -> None:
        super().__init__(view)
        self._view = view
        self._cut_tool = cut_tool
        view.right_pressed.connect(self._on_right_pressed)

    def offered(self) -> bool:
        """Is there a menu now (DEFAULT, CUTTING, or dragging a point in CUT_EDITING)?"""
        state = self._cut_tool.editor.state
        return state in (EditorState.DEFAULT, EditorState.CUTTING) or self._cut_tool.dragging

    def menu(self, placement: Placement | None) -> ContextMenu:
        """The menu: "Place a vertex" (disabled without a placement). The application's own (`ContextMenu`), not a
        system popup: on Wayland, one can't open while the drag's button is held."""
        window = self._view.window()
        assert window is not None
        return ContextMenu(window, [MenuItem(tr("Place a vertex"), placement is not None)])

    def _on_right_pressed(self, x: float, y: float) -> None:
        if not self.offered():
            return
        placement = self._cut_tool.placement_at(x, y)
        menu = self.menu(placement)
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
        if chosen == 0 and placement is not None:
            self.open_window(placement)
        elif self._cut_tool.dragging:
            self._cut_tool.cancel_drag()

    def open_window(self, placement: Placement) -> bool:
        """The window for `placement`; whether the point was placed (if not, a drag ends with the point back)."""
        window = PlaceVertexWindow(placement, lambda p: self._cut_tool.place(placement, p), self._view.window())
        self._cut_tool.freeze_drag(True)
        self._view.follow_cursor(window)
        try:
            placed = window.exec() == PlaceVertexWindow.DialogCode.Accepted
        finally:
            self._view.follow_cursor(None)
            self._cut_tool.freeze_drag(False)
        window.deleteLater()
        if not placed and self._cut_tool.dragging:
            self._cut_tool.cancel_drag()
        return placed
