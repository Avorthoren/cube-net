# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`SheetCursor`: the mouse cursor and tooltip over the sheet follow what a click would do there (`CutTool.cursor_at`).

They're worked out again when the mouse moves, and when what's under it changes without a move (a click changed the
state, the ruler was switched, SHIFT). While the sheet is being dragged, the view shows its own closed hand.

The tooltip is shown here, not with `setToolTip`: a graphics view asks its scene for tooltips, which only knows those of
items. It appears after `TOOLTIP_DELAY_MS` over the same thing, and goes as soon as the mouse leaves it (`QToolTip`
would linger: see `TooltipLabel`).
"""

from PyQt6.QtCore import QObject, QPointF, QTimer

from cube_net.ui.sheet.cursors import CursorKind, cursor_for
from cube_net.ui.sheet.cut_tool import CutTool
from cube_net.ui.sheet.ruler_tool import RulerTool
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.sheet.tooltip_label import TooltipLabel

# How long the mouse stays over something before its tooltip appears.
TOOLTIP_DELAY_MS = 500


class SheetCursor(QObject):
    def __init__(self, view: SheetView, cut_tool: CutTool, ruler: RulerTool) -> None:
        super().__init__(view)
        self._view = view
        self._cut_tool = cut_tool
        self._mouse: tuple[float, float] | None = None
        self._kind = CursorKind.ARROW
        self._tooltip = ""
        self.tooltip_label = TooltipLabel(view)
        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.setInterval(TOOLTIP_DELAY_MS)
        self._tooltip_timer.timeout.connect(self._show_tooltip)
        view.mouse_moved.connect(self._on_mouse_moved)
        view.mouse_left.connect(self._on_mouse_left)
        view.left_released.connect(lambda *_: self.update())
        view.shift_changed.connect(self.update)
        view.ctrl_changed.connect(self.update)
        cut_tool.line_changed.connect(self.update)
        cut_tool.net_changed.connect(self.update)
        ruler.points_changed.connect(self.update)

    def kind(self) -> CursorKind:
        return self._kind

    def update(self) -> None:
        if self._mouse is None or self._view.is_panning():
            return
        viewport = self._view.viewport()
        assert viewport is not None
        self._kind = self._cut_tool.cursor_at(*self._mouse)
        viewport.setCursor(cursor_for(self._kind))
        self._set_tooltip(self._cut_tool.tooltip_at(*self._mouse))

    def tooltip(self) -> str:
        """The tooltip of what's under the mouse ("": none), shown or about to be."""
        return self._tooltip

    def _set_tooltip(self, text: str) -> None:
        if text == self._tooltip:
            return  # the mouse is still over the same thing: the countdown (or the tooltip) goes on
        self.tooltip_label.hide()
        self._tooltip = text
        if text:
            self._tooltip_timer.start()
        else:
            self._tooltip_timer.stop()

    def _show_tooltip(self) -> None:
        if not self._tooltip or self._mouse is None:
            return
        viewport = self._view.viewport()
        assert viewport is not None
        where = self._view.from_sheet(QPointF(*self._mouse)).toPoint()
        self.tooltip_label.show_at(self._tooltip, viewport.mapToGlobal(where))

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self._mouse = x, y
        self.update()

    def _on_mouse_left(self) -> None:
        self._mouse = None
        self._kind = CursorKind.ARROW
        self._set_tooltip("")
