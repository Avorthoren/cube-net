"""`CutTool`: turns mouse input on the sheet into editor actions for the cut line (docs/idea.txt).

- A click on a perimeter vertex (inside its circle) or on a cut (inside its hitbox) starts the cut line there, or
  ends it there while cutting. A vertex wins over a cut.
- While cutting, a click inside the net adds a point (on a fold line, if clicked in its hitbox); a thin line follows the
  mouse from the last point (hidden while the ruler is active, which then takes the clicks).
- In CUT_EDITING, a click on a segment's hollow middle circle adds a point there; Shift+click on an inner point deletes
  it (on release, if the mouse has hardly moved: Shift+drag moves it); dragging a point moves it, and it's checked when
  the mouse is released. An endpoint walks along the perimeter and
  snaps to perimeter vertices. An inner point snaps to fold lines, and may not be released in a hitbox of the perimeter.
- A fold line is highlighted while the mouse is in its hitbox, whenever that means a point would land on it: while
  cutting, and while dragging an inner point.
- In CUT_EDITING, perimeter vertices mean nothing to the mouse, so they don't highlight; the exception is the one a
  dragged endpoint would snap to (never a counterpart image: an endpoint can't snap to those).
- In CUT_EDITING, a click on a cut of the perimeter (not on a vertex, not on the new line) moves the half with its
  counterpart onto it: CUT_APPROVING.
- In CUT_APPROVING, a round button in the middle of the chosen segment approves the rearrangement, if it's valid. If
  it isn't, the button undoes the rearrangement.
- While SHIFT is held, the segment being made (while cutting) or the one from the previous point to the dragged point
  (not for the first point) is horizontal or vertical. It takes effect at once, even if the mouse stays where it is.
- Anything that breaks the rules shows the offending segments in black for 200 ms and changes nothing.
"""

import math
from collections.abc import Callable

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from cube_net.core.cutting import CutPoint, straighten
from cube_net.core.editor import Editor, EditorState, Rejection
from cube_net.core.geometry import Vec, quantize
from cube_net.core.net import HalfEdge, NetVertex, boundary_edge_at
from cube_net.core.sheet import SHEET_MARGIN
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.approve_button_item import ApproveButtonItem
from cube_net.ui.sheet.cut_hover import cut_hitbox, fold_target, perimeter_target
from cube_net.ui.sheet.cut_line_item import CutLineItem
from cube_net.ui.sheet.ruler_tool import RulerTool
from cube_net.ui.sheet.sheet_view import SheetView

# How long a rejected segment stays black (docs/idea.txt).
FLASH_MS = 200


class CutTool(QObject):
    # A point was added to the cut line (its position; the editor's state tells whether it ended the line).
    point_added = pyqtSignal(Vec)

    # An action was rejected (the position of the point it was about).
    rejected = pyqtSignal(Vec)

    # The line was edited: "insert", "delete" or "move", the point's index, its position.
    edited = pyqtSignal(str, int, Vec)

    # The user clicked the approve button (it's up to the window to approve, as with the keyboard shortcut).
    approve_clicked = pyqtSignal()

    # The user clicked the button of a rearrangement that can't be approved (it's up to the window to undo, as with the
    # keyboard shortcut).
    undo_clicked = pyqtSignal()

    # The halves were rearranged (not by undo or redo).
    glued = pyqtSignal()

    # The net to show has changed.
    net_changed = pyqtSignal()

    # The line on display changed in any way, including while a point is being dragged.
    line_changed = pyqtSignal()

    def __init__(self, view: SheetView, editor: Editor, ruler: RulerTool) -> None:
        super().__init__(view)
        self._view = view
        self._editor = editor
        self._ruler = ruler
        self.item = CutLineItem(editor.net)
        scene = view.scene()
        assert scene is not None
        scene.addItem(self.item)
        self.approve_button = ApproveButtonItem()
        scene.addItem(self.approve_button)
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.setInterval(FLASH_MS)
        self._flash_timer.timeout.connect(self._end_flash)
        self._drag_index: int | None = None
        self._drag_target: CutPoint | None = None
        self._drag_over_perimeter = False

        # Where (in window pixels) Shift+press hit an inner point, until it's clear whether that's a click or a drag.
        self._delete_press: QPointF | None = None
        self._mouse: tuple[float, float] | None = None
        view.left_pressed.connect(self._on_left_pressed)
        view.left_released.connect(self._on_left_released)
        view.mouse_moved.connect(self._on_mouse_moved)
        view.mouse_left.connect(self._on_mouse_left)
        view.zoom_changed.connect(self._update_area)
        self.net_changed.connect(self._update_area)
        view.shift_changed.connect(self._on_shift_changed)
        ruler.points_changed.connect(self._on_ruler_changed)
        self._update_area()
        self.refresh()

    @property
    def editor(self) -> Editor:
        return self._editor

    @property
    def dragging(self) -> bool:
        return self._drag_index is not None

    def approve(self) -> None:
        """Glue the rearranged halves for good; from now on the tool works on the new net."""
        self._editor.approve()
        self.item.set_net(self._editor.net)
        self.refresh()
        self.net_changed.emit()

    def reload(self) -> None:
        """The editor got a whole new state (a project was opened): forget everything that was going on."""
        self._drag_index, self._drag_target, self._drag_over_perimeter = None, None, False
        self._delete_press = None
        self._flash_timer.stop()
        self.item.set_flash(None)
        self.item.set_net(self._editor.net)
        self.item.set_rubber_band(None)
        self.refresh()
        self.net_changed.emit()

    def undo(self) -> None:
        """Undo the last action (not while a point is being dragged)."""
        if not self.dragging:
            self._after_history_step(self._editor.undo)

    def redo(self) -> None:
        """Redo one undone action (not while a point is being dragged)."""
        if not self.dragging:
            self._after_history_step(self._editor.redo)

    def _after_history_step(self, step: Callable[[], bool]) -> None:
        shown = self._editor.display_net
        if not step():
            return
        self.item.set_net(self._editor.net)
        self.item.set_rubber_band(None)  # it may start at a point that's gone; the next mouse move draws it again
        self.refresh()
        if self._editor.display_net is not shown:
            self.net_changed.emit()

    def refresh(self) -> None:
        """Show the editor's current cut line (with the point being dragged at its current place)."""
        line = self._editor.cut_line
        approving = self._editor.state is EditorState.CUT_APPROVING  # the line is part of the shown net by then
        points = list(line.points) if line is not None and not approving else []
        if self._drag_index is not None and self._drag_target is not None:
            points[self._drag_index] = self._drag_target
        self.item.set_points(points)
        self.item.set_show_midpoints(self._editor.state is EditorState.CUT_EDITING)
        rearranged = self._editor.rearranged
        if rearranged is None:
            self.approve_button.set_state(None, False)
        else:
            kept = rearranged.kept
            middle = (kept.origin.position + kept.destination.position) / 2
            self.approve_button.set_state(middle, rearranged.valid)
        if self._editor.state is not EditorState.CUTTING:
            self.item.set_rubber_band(None)
            if self._drag_index is None:
                self._highlight_fold(None)
        self.line_changed.emit()

    def claims(self, x: float, y: float) -> bool:
        """Would a press at sheet point (x, y) mean something in the current state? Anywhere else it pans the sheet."""
        if self._ruler.active:
            return False
        state = self._editor.state
        if state is EditorState.CUT_APPROVING:
            return self._on_approve_button(x, y)
        if state is EditorState.CUT_EDITING:
            return (
                self._point_at(x, y) is not None
                or self._midpoint_at(x, y) is not None
                or self._glue_target(x, y) is not None
            )
        net = self._editor.net
        vertex, cut = perimeter_target(self._view, net, x, y)
        if state is EditorState.CUTTING:
            p, _, near, _ = self._hit(x, y)
            return near is not None or net.contains(p)  # a click on the net adds a point
        return vertex is not None or cut is not None  # DEFAULT: only the perimeter can start a line

    def _on_approve_button(self, x: float, y: float) -> bool:
        position = self.approve_button.position()
        if position is None:
            return False
        return self._closest(x, y, [position], net_style.APPROVE_BUTTON_RADIUS_PX) is not None

    def _hit(self, x: float, y: float) -> tuple[Vec, HalfEdge | None, NetVertex | None, HalfEdge | None]:
        """What's under the mouse: the point, then a cut or a perimeter vertex, or else a fold line. While cutting with
        SHIFT held, that's about where the mouse brings the end of the straight segment."""
        line = self._editor.cut_line
        if self._view.shift_held() and line is not None and not line.closed:
            return self._straight_hit(line.last.position, x, y)
        vertex, cut = perimeter_target(self._view, self._editor.net, x, y)
        on_perimeter = vertex is not None or cut is not None
        fold = None if on_perimeter else fold_target(self._view, self._editor.net, x, y)
        return quantize(x, y), cut, vertex, fold

    def _straight_hit(
        self, anchor: Vec, x: float, y: float, prefer: HalfEdge | None = None
    ) -> tuple[Vec, HalfEdge | None, NetVertex | None, HalfEdge | None]:
        """Like `_hit` for the end of a straight segment from `anchor`: a vertex counts only if it's on its line."""
        net = self._editor.net
        p = straighten(anchor, quantize(x, y))
        px, py = float(p.x), float(p.y)
        vertex, cut = perimeter_target(self._view, net, px, py)
        fold = None if vertex is not None or cut is not None else fold_target(self._view, net, px, py, prefer)
        if vertex is not None and (p - anchor).cross(vertex.position - anchor) != 0:
            vertex, cut = None, boundary_edge_at(net, quantize(px, py), cut_hitbox(self._view))
        return p, cut, vertex, fold

    def hover_target(self, x: float, y: float) -> tuple[NetVertex | None, HalfEdge | None] | None:
        """While cutting with SHIFT held, what highlights is what the straight segment would end on (see `CutHover`)."""
        line = self._editor.cut_line
        if self._ruler.active or not self._view.shift_held() or line is None or line.closed:
            return None
        _, cut, vertex, _ = self._hit(x, y)
        return vertex, cut

    def _on_shift_changed(self) -> None:
        if self._mouse is not None:
            self._on_mouse_moved(*self._mouse)

    def _on_left_pressed(self, x: float, y: float) -> None:
        self._mouse = x, y
        if self._ruler.active:
            return  # the ruler takes the clicks
        if self._editor.state is EditorState.CUT_EDITING:
            self._press_while_editing(x, y)
            return
        if self._editor.state is EditorState.CUT_APPROVING:
            if self._on_approve_button(x, y):
                if self.approve_button.enabled():
                    self.approve_clicked.emit()
                else:
                    self.undo_clicked.emit()
            return
        p, cut, vertex, fold = self._hit(x, y)
        before = len(self._editor.cut_line.points) if self._editor.cut_line else 0
        straight = self._view.shift_held() and self._editor.state is EditorState.CUTTING
        rejection = self._editor.click(p, cut, vertex, fold, straight)
        if rejection is not None:
            self._reject(rejection, rejection.segment[1])
            return
        line = self._editor.cut_line
        if line is not None and len(line.points) > before:
            self.refresh()
            self.point_added.emit(line.last.position)

    def _press_while_editing(self, x: float, y: float) -> None:
        line = self._editor.cut_line
        assert line is not None
        i = self._point_at(x, y)
        if i is not None:
            self._drag_index, self._drag_target, self._drag_over_perimeter = i, None, False
            inner = 0 < i < len(line.points) - 1
            shift = self._view.press_modifiers() & Qt.KeyboardModifier.ShiftModifier
            self._delete_press = self._view.from_sheet(QPointF(x, y)) if inner and shift else None
            self.line_changed.emit()
            return
        segment = self._midpoint_at(x, y)
        if segment is not None:
            rejection = self._editor.insert_midpoint(segment)
            if rejection is not None:
                self._reject(rejection, (rejection.segment[0] + rejection.segment[1]) / 2)
            else:
                self.refresh()
                self.edited.emit("insert", segment + 1, line.points[segment + 1].position)
            return
        self._press_on_cut(x, y)

    def _glue_target(self, x: float, y: float) -> HalfEdge | None:
        """The part of a cut that a press at (x, y) in CUT_EDITING would choose: not in a vertex's circle, not the new
        line itself. It may still get rejected."""
        split = self._editor.split()
        vertex, cut = perimeter_target(self._view, split.net, x, y)
        return None if vertex is not None or cut in split.line_edges else cut

    def _press_on_cut(self, x: float, y: float) -> None:
        cut = self._glue_target(x, y)
        if cut is None:
            return
        rejection = self._editor.glue(cut)
        if rejection is not None:
            self._reject(rejection, (rejection.segment[0] + rejection.segment[1]) / 2)
        elif self._editor.state is EditorState.CUT_APPROVING:
            self.refresh()
            self.net_changed.emit()
            self.glued.emit()

    def _on_left_released(self, x: float, y: float) -> None:
        i, target = self._drag_index, self._drag_target
        self._drag_index, self._drag_target = None, None
        self._highlight_fold(None)
        self._highlight_vertex(None)
        if i is None:
            return
        if self._delete_press is not None:
            self._delete_press = None
            self._delete_point(i)
            return
        if target is None:  # pressed and released without moving
            self.line_changed.emit()
            return
        rejection = self._editor.move_point(i, target, self._drag_over_perimeter)
        self.refresh()
        if rejection is not None:
            self._reject(rejection, target.position)
        else:
            self.edited.emit("move", i, target.position)

    def _delete_point(self, i: int) -> None:
        line = self._editor.cut_line
        assert line is not None
        position = line.points[i].position
        rejection = self._editor.delete_point(i)
        self.refresh()
        if rejection is not None:
            self._reject(rejection, position)
        else:
            self.edited.emit("delete", i, position)

    def _reject(self, rejection: Rejection, position: Vec) -> None:
        """Show the offending segments in black for a moment (with the rejection's preview of the line, if any)."""
        self.item.set_flash(rejection.segments)
        if rejection.preview is not None:
            self.item.set_points(rejection.preview)
            self.item.set_show_midpoints(False)
        self._flash_timer.start()
        self.rejected.emit(position)

    def _end_flash(self) -> None:
        self.item.set_flash(None)
        self.refresh()

    def _point_at(self, x: float, y: float) -> int | None:
        """The index of the cut line's point whose circle contains sheet point (x, y); the closest one wins."""
        line = self._editor.cut_line
        positions = [p.position for p in line.points] if line is not None else []
        return self._closest(x, y, positions, net_style.VERTEX_RADIUS_PX)

    def _midpoint_at(self, x: float, y: float) -> int | None:
        """The index of the segment whose middle circle contains sheet point (x, y); the closest one wins."""
        radius = net_style.VERTEX_RADIUS_PX * net_style.MIDPOINT_RADIUS_FACTOR
        return self._closest(x, y, self.item.midpoints(), radius)

    def _closest(self, x: float, y: float, positions: list[Vec], radius_px: float) -> int | None:
        mouse = self._view.from_sheet(QPointF(x, y))
        best: tuple[float, int] | None = None
        for i, position in enumerate(positions):
            d = self._view.from_sheet(to_qpointf(position)) - mouse
            distance = math.hypot(d.x(), d.y())
            if distance <= radius_px and (best is None or distance < best[0]):
                best = (distance, i)
        return None if best is None else best[1]

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self._mouse = x, y
        if self._drag_index is not None:
            self._drag_to(x, y)
            return
        line = self._editor.cut_line
        if self._editor.state is not EditorState.CUTTING or self._ruler.active or line is None:
            self.item.set_rubber_band(None)
            self._highlight_fold(None)
            return
        p, cut, vertex, fold = self._hit(x, y)
        target = self._editor.candidate(p, cut, vertex, fold, self._view.shift_held())
        self.item.set_rubber_band((line.last.position, target.position))
        self._highlight_fold(target.fold)

    def _on_mouse_left(self) -> None:
        if self._drag_index is None:
            self._mouse = None
        self.item.set_rubber_band(None)
        self._highlight_fold(None)
        if self._drag_index is not None:
            self._highlight_vertex(None)

    def _on_ruler_changed(self) -> None:
        if self._ruler.active:
            self.item.set_rubber_band(None)
            self._highlight_fold(None)

    def _highlight_fold(self, fold: HalfEdge | None) -> None:
        net_item = self._view.net_item()
        if net_item is not None:
            net_item.set_highlight_fold(fold)

    def _highlight_vertex(self, vertex: NetVertex | None) -> None:
        net_item = self._view.net_item()
        if net_item is not None:
            net_item.set_highlight_vertex(vertex)

    def _drag_to(self, x: float, y: float) -> None:
        i = self._drag_index
        line = self._editor.cut_line
        assert i is not None and line is not None
        if self._delete_press is not None:
            moved = self._view.from_sheet(QPointF(x, y)) - self._delete_press
            if moved.manhattanLength() < QApplication.startDragDistance():
                return  # still a click
            self._delete_press = None
        net = self._editor.net
        original = line.points[i]
        straight = self._view.shift_held() and i > 0
        if original.on_perimeter:
            vertex, _ = perimeter_target(self._view, net, x, y)
            target = self._editor.drag_target(
                i, quantize(x, y), vertex=vertex, current=self._drag_target, straight=straight
            )
            self._drag_target = target
            self._highlight_vertex(vertex if target.vertex is vertex else None)
        else:
            on_fold = (self._drag_target or original).fold
            if straight:
                p, _, _, fold = self._straight_hit(line.points[i - 1].position, x, y, on_fold)
                vertex, cut = perimeter_target(self._view, net, float(p.x), float(p.y))
            else:
                p = quantize(x, y)
                vertex, cut = perimeter_target(self._view, net, x, y)
                fold = fold_target(self._view, net, x, y, prefer=on_fold)
            self._drag_over_perimeter = vertex is not None or cut is not None
            self._drag_target = self._editor.drag_target(i, p, fold=fold, straight=straight)
            self._highlight_fold(None if self._drag_over_perimeter else self._drag_target.fold)
        self.refresh()

    def _update_area(self, *_: object) -> None:
        # The sheet margin is always enough for the pixel-sized decorations at the allowed zoom levels.
        box = self._editor.display_net.bounding_box().expanded(SHEET_MARGIN)
        area = QRectF(float(box.lo.x), float(box.lo.y), float(box.width), float(box.height))
        self.item.set_area(area)
        self.approve_button.set_area(area)
