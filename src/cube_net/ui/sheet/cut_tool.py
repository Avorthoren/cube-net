# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`CutTool`: turns mouse input on the sheet into editor actions for the cut line (docs/idea.txt).

- A click on a perimeter vertex (inside its circle) or on a cut (inside its hitbox) starts the cut line there, or
  ends it there while cutting. A vertex wins over a cut.
- While cutting, a click inside the net adds a point (on a fold line, if clicked in its hitbox); so does a click off
  the net (outside it, or in a hole: a press there still pans the sheet if the mouse moves before it's released). A
  thin line follows the mouse from the last point (hidden while the ruler is active, which then takes the clicks). The
  line ends by itself where it divides the net in two (docs/template_plan.md §8.2).
- In CUT_EDITING, a click on a segment's hollow middle circle adds a point there; Ctrl+click on an inner point deletes
  it (on release on the same point; while CTRL is held over it the mouse shows a red x); dragging a point moves it
  (with SHIFT too: see below), and it's checked when the mouse is released. An endpoint walks along the perimeter and
  snaps to perimeter vertices. An inner point snaps to fold lines, and may not be released in a hitbox of the perimeter.
- A fold line is highlighted while the mouse is in its hitbox, whenever that means a point would land on it: while
  cutting, and while dragging an inner point.
- In CUT_EDITING, perimeter vertices mean nothing to the mouse, so they don't highlight; the exception is the one a
  dragged endpoint would snap to (never a counterpart image: an endpoint can't snap to those).
- In CUT_EDITING, a click on a cut of the perimeter (not on a vertex, not on the new line) moves the half with its
  counterpart onto it: CUT_APPROVING.
- In CUT_APPROVING, a round button in the middle of the chosen segment approves the rearrangement, if it's valid. If
  it isn't, the button undoes the rearrangement.
- That button and the middle circles act like buttons: a press only shows them pressed; they act when the mouse button
  is released on them. Moved off before that, they don't (they look pressed again if it comes back).
- While SHIFT is held, the segment being made (while cutting) or the one from the previous point to the dragged point
  (not for the first point) is horizontal or vertical. It takes effect at once, even if the mouse stays where it is.
- Anything that breaks the rules shows the offending segments in black for 200 ms and changes nothing.
"""

import math
from collections.abc import Callable, Sequence

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, pyqtSignal

from cube_net.core.cutting import CutPoint, TooLong, straighten
from cube_net.core.cutting.placement import (
    Action,
    Constraint,
    LineKind,
    Placement,
    Problem,
    fold_through,
    perimeter_edge_through,
)
from cube_net.core.editor import Editor, EditorState, Rejection
from cube_net.core.geometry import Vec, quantize
from cube_net.core.net import HalfEdge, NetVertex, boundary_edge_at
from cube_net.core.origin import Origin
from cube_net.core.sheet import SHEET_MARGIN
from cube_net.ui.i18n import tr
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.approve_button_item import ApproveButtonItem
from cube_net.ui.sheet.cursors import CursorKind
from cube_net.ui.sheet.cut_hover import cut_hitbox, fold_target, perimeter_target
from cube_net.ui.sheet.cut_line_item import CutLineItem
from cube_net.ui.sheet.ruler_tool import RulerTool
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.too_long_message import REJECTED

# How long a rejected segment stays black (docs/idea.txt).
FLASH_MS = 200


class CutTool(QObject):
    # A point was added to the cut line (its position; the editor's state tells whether it ended the line).
    point_added = pyqtSignal(Vec)

    # An action was rejected (the position of the point it was about).
    rejected = pyqtSignal(Vec)

    # An action was rejected because a point it would make has a number too long: what to tell the user.
    too_long = pyqtSignal(str)

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

    # The locked slope changed: the direction (a Vec), or None when it's unlocked (right click -> Set slope).
    slope_changed = pyqtSignal(object)

    # The origin of the coordinates shown and typed changed (moved, undone, redone, another project).
    origin_changed = pyqtSignal()

    def __init__(self, view: SheetView, editor: Editor, ruler: RulerTool) -> None:
        super().__init__(view)
        self._view = view
        self._editor = editor
        self._ruler = ruler
        # What to tell the user about a point whose number is too long (the main window's: it knows the names).
        self.describe_too_long: Callable[[TooLong], str] = lambda found: tr(REJECTED)

        # Points drawn by others whose coordinates the hint shows too, as for vertices (the bounding rectangle's
        # corners, while it's shown): see `coordinates_at`.
        self.hint_points: Callable[[], Sequence[Vec]] = tuple

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

        # A window (Place a vertex) is open: a point being dragged stays where it is, whatever the mouse does.
        self._drag_frozen = False

        # The line's next point being placed in that window, if it's bound to a line: the dashed line from the last
        # point follows the mouse only along that line.
        self._placing: Placement | None = None

        # The locked slope (a direction, not zero), until the point is placed or the drag ends (right click -> Set
        # slope): the current segment goes that way, whatever the mouse, SHIFT or snapping would do.
        self._slope: Vec | None = None

        # The drag goes on without a button (it was released while a window was open): the next press or release
        # ends it, as the release would have.
        self._drag_free = False

        self._mouse: tuple[float, float] | None = None

        # A button that's pressed: ("approve", 0), ("midpoint", its segment) or ("delete", the point pressed with CTRL).
        # It acts if released on it.
        self._armed: tuple[str, int] | None = None
        view.left_pressed.connect(self._on_left_pressed)
        view.left_released.connect(self._on_left_released)
        view.pan_clicked.connect(self._on_pan_clicked)
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

    def slope(self) -> Vec | None:
        """The locked slope's direction, if a slope is locked."""
        return self._slope

    def lock_slope(self, direction: Vec) -> None:
        """Lock the current segment's slope (`direction`, not zero): until the point is placed (CUTTING) or the drag
        ends."""
        self._slope = direction
        self.slope_changed.emit(direction)
        self._follow_mouse()

    def unlock_slope(self) -> None:
        if self._slope is None:
            return
        self._end_slope()
        self._follow_mouse()

    def _end_slope(self) -> None:
        """The lock is over (its point placed, its drag ended, its CUTTING gone)."""
        if self._slope is not None:
            self._slope = None
            self.slope_changed.emit(None)

    def continue_drag_without_button(self) -> None:
        """The drag's button was released while a window was open: the drag goes on, and the next press or release
        ends it there."""
        self._drag_free = True

    def _follow_mouse(self) -> None:
        """What follows the mouse (the dashed line, a dragged point) is worked out again, without a move."""
        if self._mouse is not None:
            self._on_mouse_moved(*self._mouse)

    def _straight(self) -> bool:
        """SHIFT's horizontal or vertical: only while no slope is locked (the locked one wins)."""
        return self._view.shift_held() and self._slope is None

    def slope_at(self, x: float, y: float) -> Vec | None:
        """The direction of the current segment, as it's shown for the mouse at (x, y): the one a click there would
        make (CUTTING), or the dragged point's segment from the point before it. None: there's none (DEFAULT, the
        first point dragged, the ruler on, the mouse right on the previous point)."""
        if self._ruler.active:
            return None
        line = self._editor.cut_line
        if self._drag_index is not None and line is not None:
            i = self._drag_index
            if i == 0:
                return None
            direction = (self._drag_target or line.points[i]).position - line.points[i - 1].position
        elif self._editor.state is EditorState.CUTTING and line is not None:
            p, cut, vertex, fold = self._hit(x, y)
            target = self._editor.candidate(p, cut, vertex, fold, self._straight(), self._slope)
            direction = target.position - line.last.position
        else:
            return None
        return None if direction == Vec(0, 0) else direction

    def set_placing(self, placement: Placement | None) -> None:
        """While the window for `placement` is open (None: closed). A point the line would add that's bound to a line
        (an edge, a fold, SHIFT's): the dashed line to the mouse ends at the point of that line closest to the mouse,
        and never beyond an edge's or a fold's ends."""
        self._placing = placement

    def freeze_drag(self, frozen: bool) -> None:
        """While a window is open over a drag (Place a vertex), the dragged point doesn't follow the mouse, and the
        hints describe what's under the mouse, as when nothing is dragged."""
        self._drag_frozen = frozen

    @property
    def busy(self) -> bool:
        """The mouse button is down on something of the line (a point, a button): nothing else should change now."""
        return self.dragging or self._armed is not None

    def approve(self) -> None:
        """Glue the rearranged halves for good; from now on the tool works on the new net."""
        self._editor.approve()
        self.item.set_net(self._editor.net)
        self.refresh()
        self.net_changed.emit()

    def reload(self) -> None:
        """The editor got a whole new state (a project was opened): forget everything that was going on."""
        self._drag_index, self._drag_target, self._drag_over_perimeter = None, None, False
        self._disarm()
        self._flash_timer.stop()
        self.item.set_flash(None)
        self.item.set_net(self._editor.net)
        self.item.set_rubber_band(None)
        self.refresh()
        self.net_changed.emit()
        self.origin_changed.emit()

    def cancel_drag(self) -> None:
        """Forget the point being dragged (it stays where it was), or the button being pressed (it doesn't act)."""
        if self._armed is not None:
            self._disarm()
            self.line_changed.emit()
        if self._drag_index is None:
            return
        self._drag_index, self._drag_target, self._drag_over_perimeter = None, None, False
        self._drag_free = False
        self._end_slope()
        self._highlight_fold(None)
        self._highlight_vertex(None)
        self.refresh()

    def undo(self) -> None:
        """Undo the last action (not while a point is being dragged)."""
        if not self.busy:
            self._after_history_step(self._editor.undo)

    def redo(self) -> None:
        """Redo one undone action (not while a point is being dragged)."""
        if not self.busy:
            self._after_history_step(self._editor.redo)

    def _after_history_step(self, step: Callable[[], bool]) -> None:
        shown = self._editor.display_net
        origin = self._editor.origin
        if not step():
            return
        if self._editor.origin != origin:
            self.origin_changed.emit()
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
        if self._drag_index is None and self._editor.state is not EditorState.CUTTING:
            self._end_slope()  # its CUTTING is over (the line closed, or undone)
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
        if self._drag_index is not None:
            return True  # a drag without its button (after Set slope): any press ends it, wherever it is
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

    def cursor_at(self, x: float, y: float) -> CursorKind:
        """What the mouse at sheet point (x, y) shows: what a click there would do (docs/idea.txt). Nothing special
        while the ruler is active, which takes the clicks."""
        if self._ruler.active:
            return CursorKind.ARROW
        if self.dragging:
            return CursorKind.PENCIL
        state = self._editor.state
        if state is EditorState.CUT_APPROVING:
            return CursorKind.BUTTON if self._on_approve_button(x, y) else CursorKind.ARROW
        if state is EditorState.CUT_EDITING:
            if self._armed is not None and self._armed[0] == "delete":  # released off the point, it stays
                return CursorKind.DELETE if self._on_armed(x, y) else CursorKind.ARROW
            if self._midpoint_at(x, y) is not None:
                return CursorKind.PLUS
            i = self._point_at(x, y)
            if i is not None:
                return CursorKind.DELETE if self._view.ctrl_held() and self._is_inner(i) else CursorKind.PENCIL
            cut = self._glue_target(x, y)
            choosable = cut is not None and cut not in self._editor.split().same_half_cuts
            return CursorKind.GLUE if choosable else CursorKind.ARROW
        return CursorKind.SCISSORS if self.claims(x, y) else CursorKind.ARROW  # DEFAULT and CUTTING

    def tooltip_at(self, x: float, y: float) -> str:
        """The tooltip of what's under the mouse: the approve button tells what it does."""
        if self._ruler.active or not self._on_approve_button(x, y):
            return ""
        return tr("Approve") if self.approve_button.enabled() else tr("Cancel")

    def coordinates_at(self, x: float, y: float) -> Vec | None:
        """The point whose exact coordinates the hint shows for the mouse at sheet point (x, y), if any (docs/idea.txt).
        Where they're not just the mouse's (the footer's), as the points have hitboxes, and so do the perimeter and the
        fold lines:
        - over the approve button: none (its own tooltip says what it does);
        - while a point is dragged: where it is, while it's snapped (to the perimeter, a vertex, a fold line);
        - over a point (in its circle): that point. Any drawn point: the net's vertices, the cut line's points, its
          small dots (crossings with fold lines, the endpoints' counterpart images);
        - over one of `hint_points` (in a circle as big as a vertex's, though none is drawn): that point (they come
          after the drawn ones: where one is on a vertex, it's that vertex anyway);
        - else, while a click would make a point (the line's first, or the next one): that point, if it would be
          snapped to the perimeter or (while cutting) to a fold line."""
        if self._on_approve_button(x, y):
            return None
        if self._drag_index is not None and self._drag_target is not None and not self._drag_frozen:
            target = self._drag_target
            snapped = target.on_perimeter or (target.fold is not None and not self._drag_over_perimeter)
            return target.position if snapped else None
        point = self._drawn_point_at(x, y)
        if point is not None:
            return point
        others = list(self.hint_points())
        i = self._closest(x, y, others, net_style.VERTEX_RADIUS_PX)
        if i is not None:
            return others[i]
        state = self._editor.state
        if self._ruler.active or state not in (EditorState.DEFAULT, EditorState.CUTTING):
            return None
        p, cut, vertex, fold = self._hit(x, y)
        cutting = state is EditorState.CUTTING
        target = self._editor.candidate(p, cut, vertex, fold, self._straight(), self._slope if cutting else None)
        if target.on_perimeter or (cutting and target.fold is not None):
            return target.position
        return None

    def vertex_at(self, x: float, y: float) -> Vec | None:
        """The drawn point under the mouse at sheet point (x, y) (in its circle), the hint's, whose coordinates can be
        set by moving the origin (right click -> Move the origin): none while a point is dragged, nor over the approve
        button."""
        if self._drag_index is not None or self._on_approve_button(x, y):
            return None
        return self._drawn_point_at(x, y)

    def _drawn_point_at(self, x: float, y: float) -> Vec | None:
        """Any drawn point under the mouse (in its circle): the net's vertices, the cut line's points, its small dots
        (crossings with fold lines, the endpoints' counterpart images)."""
        positions = [point.position for point in self.item.points()] + self.item.crossings() + self.item.images()
        positions += [entry.position for entry in self.item.entries()]
        positions += [vertex.position for vertex in self._editor.display_net.vertices]
        i = self._closest(x, y, positions, net_style.VERTEX_RADIUS_PX)
        return None if i is None else positions[i]

    def move_origin(self, origin: Origin) -> None:
        """Show and take the coordinates from `origin` (an action, if it moved)."""
        before = self._editor.origin
        rejection = self._editor.move_origin(origin)
        if rejection is not None and rejection.too_long is not None:
            self.too_long.emit(self.describe_too_long(rejection.too_long))
        if self._editor.origin != before:
            self.origin_changed.emit()

    def placement_at(self, x: float, y: float) -> Placement | None:
        """What a right click at sheet point (x, y) offers to place at typed coordinates: the point a left click there
        would make (DEFAULT, CUTTING), or where the dragged point is now (CUT_EDITING), with what it's snapped to
        (docs/idea.txt). None where there's nothing to place or nothing to type: no point would be made, or it would be
        a vertex of the perimeter (both its coordinates are fixed)."""
        if self._ruler.active:
            return None
        line = self._editor.cut_line
        straight = self._straight()
        slope = self._slope
        if self._drag_index is not None and line is not None:
            i = self._drag_index
            target = self._drag_target or line.points[i]
            if slope is not None and i > 0:
                return Placement(Action.MOVE, target.position, self._sloped(target, line.points[i - 1].position), i)
            if target.vertex is not None:
                return None
            if target.edge is not None:
                return Placement(Action.MOVE, target.position, Constraint.on_edge(target.edge), i)
            if straight and i > 0:
                anchor = line.points[i - 1].position
                constraint = Constraint.straight(anchor, horizontal=target.position.y == anchor.y)
            elif target.fold is not None and not self._drag_over_perimeter:
                constraint = Constraint.on_fold(target.fold)
            else:
                constraint = Constraint.free()
            return Placement(Action.MOVE, target.position, constraint, i)
        state = self._editor.state
        if state not in (EditorState.DEFAULT, EditorState.CUTTING):
            return None
        p, cut, vertex, fold = self._hit(x, y)
        cutting = state is EditorState.CUTTING
        target = self._editor.candidate(p, cut, vertex, fold, straight, slope if cutting else None)
        action = Action.START if state is EditorState.DEFAULT else Action.ADD
        if cutting and slope is not None and line is not None:
            return Placement(action, target.position, self._sloped(target, line.last.position))
        if target.vertex is not None:
            return None
        if target.edge is not None:  # the edge wins over SHIFT's line
            return Placement(action, target.position, Constraint.on_edge(target.edge))
        if state is EditorState.DEFAULT:
            return None  # a line starts on the perimeter (off the net, a point may go: docs/template_plan.md §8.2)
        if straight and line is not None:
            anchor = line.last.position
            constraint = Constraint.straight(anchor, horizontal=target.position.y == anchor.y)
        elif target.fold is not None:
            constraint = Constraint.on_fold(target.fold)
        else:
            constraint = Constraint.free()
        return Placement(action, target.position, constraint)

    def _sloped(self, target: CutPoint, anchor: Vec) -> Constraint:
        """With a locked slope: a point snapped to something is fixed where the slope's line meets it; otherwise it's
        typed along that line."""
        assert self._slope is not None
        if target.edge is not None:
            return Constraint.on_edge(target.edge).fixed_at(target.position)
        if target.fold is not None and not self._drag_over_perimeter:
            return Constraint.on_fold(target.fold).fixed_at(target.position)
        return Constraint.along(anchor, self._slope)

    def place(self, placement: Placement, p: Vec) -> Problem | str | None:
        """Put the point of `placement` exactly at `p` (typed: nothing is rounded); or why it can't go there, and
        nothing changes (a dragged point stays dragged)."""
        net = self._editor.net
        constraint = placement.constraint
        problem = constraint.problem(net, p)
        # While cutting, a point typed on the perimeter (a free one, or on a line that reaches it) is the line's last
        # point, as a click on the perimeter would make it.
        ending = problem is Problem.ON_PERIMETER and placement.action is Action.ADD
        end_cut = perimeter_edge_through(net, p) if ending else None
        if problem is not None and end_cut is None:
            return problem
        if end_cut is not None:
            point = self._editor.point_on_cut(p, end_cut)
        elif constraint.kind is LineKind.EDGE:
            assert constraint.edge is not None
            point = self._editor.point_on_cut(p, constraint.edge)
        elif constraint.kind is LineKind.FOLD:
            point = CutPoint(p, fold=constraint.edge)
        else:
            point = CutPoint(p, fold=fold_through(net, p))
        if placement.action is Action.START:
            if (rejection := self._editor.start_at(point)) is not None:
                return self._refused(rejection)
        elif placement.action is Action.ADD:
            if self._editor.too_many_points(point):
                return Problem.TOO_MANY_POINTS
            if (rejection := self._editor.add_point(point)) is not None:
                return self._refused(rejection)
        else:
            assert placement.index is not None
            if (rejection := self._editor.move_point(placement.index, point)) is not None:
                return self._refused(rejection)
            self._drag_index, self._drag_target, self._drag_over_perimeter = None, None, False
            self._drag_free = False
            self._end_slope()
            self._highlight_fold(None)
            self._highlight_vertex(None)
            self.refresh()
            self.edited.emit("move", placement.index, p)
            return None
        self._end_slope()  # placed: the lock was for this point
        self.refresh()
        self.point_added.emit(p)
        return None

    def _on_approve_button(self, x: float, y: float) -> bool:
        position = self.approve_button.position()
        if position is None:
            return False
        return self._closest(x, y, [position], net_style.APPROVE_BUTTON_RADIUS_PX) is not None

    def _hit(self, x: float, y: float) -> tuple[Vec, HalfEdge | None, NetVertex | None, HalfEdge | None]:
        """What's under the mouse: the point, then a cut or a perimeter vertex, or else a fold line. While cutting with
        SHIFT held, that's about where the mouse brings the end of the straight segment."""
        line = self._editor.cut_line
        if self._straight() and line is not None and self._editor.state is EditorState.CUTTING:
            return self._straight_hit(line.last.position, x, y)
        vertex, cut = perimeter_target(self._view, self._editor.net, x, y)
        on_perimeter = vertex is not None or cut is not None
        fold = None if on_perimeter else fold_target(self._view, self._editor.net, x, y)
        return self._editor.origin.quantize(x, y), cut, vertex, fold

    def _straight_hit(
        self, anchor: Vec, x: float, y: float, prefer: HalfEdge | None = None
    ) -> tuple[Vec, HalfEdge | None, NetVertex | None, HalfEdge | None]:
        """Like `_hit` for the end of a straight segment from `anchor`: a vertex counts only if it's on its line."""
        net = self._editor.net
        p = straighten(anchor, self._editor.origin.quantize(x, y))
        px, py = float(p.x), float(p.y)
        vertex, cut = perimeter_target(self._view, net, px, py)
        fold = None if vertex is not None or cut is not None else fold_target(self._view, net, px, py, prefer)
        if vertex is not None and (p - anchor).cross(vertex.position - anchor) != 0:
            vertex, cut = None, boundary_edge_at(net, quantize(px, py), cut_hitbox(self._view))
        return p, cut, vertex, fold

    def hover_target(self, x: float, y: float) -> tuple[NetVertex | None, HalfEdge | None] | None:
        """While cutting with SHIFT held, what highlights is what the straight segment would end on (see `CutHover`)."""
        line = self._editor.cut_line
        if self._ruler.active or not self._straight() or line is None or self._editor.state is not EditorState.CUTTING:
            return None
        _, cut, vertex, _ = self._hit(x, y)
        return vertex, cut

    def _is_inner(self, i: int) -> bool:
        """Is point i of the cut line neither its first nor its last?"""
        line = self._editor.cut_line
        return line is not None and 0 < i < len(line.points) - 1

    def _on_shift_changed(self) -> None:
        if self._mouse is not None:
            self._on_mouse_moved(*self._mouse)

    def _on_left_pressed(self, x: float, y: float) -> None:
        self._mouse = x, y
        if self._drag_free and self._drag_index is not None:
            self._on_left_released(x, y)  # the drag without a button: this press ends it
            return
        if self._ruler.active:
            return  # the ruler takes the clicks
        if self._editor.state is EditorState.CUT_EDITING:
            self._press_while_editing(x, y)
            return
        if self._editor.state is EditorState.CUT_APPROVING:
            if self._on_approve_button(x, y):
                self._arm(("approve", 0))
            return
        p, cut, vertex, fold = self._hit(x, y)
        before = len(self._editor.cut_line.points) if self._editor.cut_line else 0
        cutting = self._editor.state is EditorState.CUTTING
        straight = self._straight() and cutting
        rejection = self._editor.click(p, cut, vertex, fold, straight, self._slope if cutting else None)
        if rejection is not None:
            self._reject(rejection, rejection.segment[1])
            return
        line = self._editor.cut_line
        if line is not None and len(line.points) > before:
            self.unlock_slope()  # placed: the lock was for this point
            self.refresh()
            self.point_added.emit(line.last.position)

    def _on_pan_clicked(self, x: float, y: float) -> None:
        """A click off the net (a press there pans the sheet, unless it's released where it was pressed): while
        cutting, a new point there (the line may go outside the net, or through a hole: docs/template_plan.md §8.2)."""
        if self._editor.state is EditorState.CUTTING and not self._ruler.active and self._drag_index is None:
            self._on_left_pressed(x, y)

    def _press_while_editing(self, x: float, y: float) -> None:
        line = self._editor.cut_line
        assert line is not None
        i = self._point_at(x, y)
        if i is not None and self._is_inner(i) and self._view.press_modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._arm(("delete", i))
            return
        if i is not None:
            self._drag_index, self._drag_target, self._drag_over_perimeter = i, None, False
            self.line_changed.emit()
            return
        segment = self._midpoint_at(x, y)
        if segment is not None:
            self._arm(("midpoint", segment))
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

    def _arm(self, button: tuple[str, int]) -> None:
        self._armed = button
        self._show_pressed(True)
        self.line_changed.emit()

    def _on_armed(self, x: float, y: float) -> bool:
        """Is the mouse on the pressed button?"""
        assert self._armed is not None
        kind, segment = self._armed
        if kind == "approve":
            return self._editor.state is EditorState.CUT_APPROVING and self._on_approve_button(x, y)
        if kind == "delete":
            return self._editor.state is EditorState.CUT_EDITING and self._point_at(x, y) == segment
        return self._editor.state is EditorState.CUT_EDITING and self._midpoint_at(x, y) == segment

    def _show_pressed(self, pressed: bool) -> None:
        assert self._armed is not None
        kind, segment = self._armed
        if kind == "approve":
            self.approve_button.set_pressed(pressed)
        elif kind == "midpoint":
            self.item.set_pressed_midpoint(segment if pressed else None)

    def _disarm(self) -> None:
        if self._armed is not None:
            self._show_pressed(False)
            self._armed = None

    def _release_armed(self, x: float, y: float) -> None:
        """The mouse button is up: the pressed button acts if it's still under the mouse."""
        assert self._armed is not None
        kind, segment = self._armed
        on_it = self._on_armed(x, y)
        self._disarm()
        self.line_changed.emit()
        if not on_it:
            return
        if kind == "approve":
            if self.approve_button.enabled():
                self.approve_clicked.emit()
            else:
                self.undo_clicked.emit()
            return
        if kind == "delete":
            self._delete_point(segment)
            return
        line = self._editor.cut_line
        assert line is not None
        rejection = self._editor.insert_midpoint(segment)
        if rejection is not None:
            self._reject(rejection, (rejection.segment[0] + rejection.segment[1]) / 2)
        else:
            self.refresh()
            self.edited.emit("insert", segment + 1, line.points[segment + 1].position)

    def _on_left_released(self, x: float, y: float) -> None:
        if self._armed is not None:
            self._release_armed(x, y)
            return
        i, target = self._drag_index, self._drag_target
        self._drag_index, self._drag_target = None, None
        self._drag_free = False
        self._highlight_fold(None)
        self._highlight_vertex(None)
        if i is None:
            return
        self._end_slope()  # the lock was for this drag
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

    def _refused(self, rejection: Rejection) -> Problem | str:
        """What Place a vertex says about a refused point: the rules it breaks, or the whole message about a number
        too long."""
        return Problem.BREAKS_LINE if rejection.too_long is None else self.describe_too_long(rejection.too_long)

    def _reject(self, rejection: Rejection, position: Vec) -> None:
        """Show the offending segments in black for a moment (with the rejection's preview of the line, if any); a
        point whose number is too long is told about instead (`too_long`)."""
        if rejection.too_long is not None:
            self.rejected.emit(position)
            self.too_long.emit(self.describe_too_long(rejection.too_long))
            return
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
        radius = net_style.midpoint_radius()
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
        if self._armed is not None:
            self._show_pressed(self._on_armed(x, y))  # pressed while the mouse is on it
            return
        if self._drag_index is not None:
            if not self._drag_frozen:
                self._drag_to(x, y)
            return
        line = self._editor.cut_line
        if self._editor.state is not EditorState.CUTTING or self._ruler.active or line is None:
            self.item.set_rubber_band(None)
            self._highlight_fold(None)
            return
        placing = self._placing
        if placing is not None and placing.action is Action.ADD and placing.constraint.bound:
            constraint = placing.constraint
            self.item.set_rubber_band((line.last.position, constraint.nearest(self._editor.origin.quantize(x, y))))
            self._highlight_fold(constraint.edge if constraint.kind is LineKind.FOLD else None)
            return
        p, cut, vertex, fold = self._hit(x, y)
        target = self._editor.candidate(p, cut, vertex, fold, self._straight(), self._slope)
        self.item.set_rubber_band((line.last.position, target.position))
        self._highlight_fold(target.fold)

    def _on_mouse_left(self) -> None:
        if self._armed is not None:
            self._show_pressed(False)
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
        net = self._editor.net
        original = line.points[i]
        straight = self._straight() and i > 0
        slope = self._slope if i > 0 else None
        if original.on_perimeter:
            vertex, _ = perimeter_target(self._view, net, x, y)
            target = self._editor.drag_target(
                i,
                self._editor.origin.quantize(x, y),
                vertex=vertex,
                current=self._drag_target,
                straight=straight,
                slope=slope,
            )
            self._drag_target = target
            self._highlight_vertex(vertex if target.vertex is vertex else None)
        else:
            on_fold = (self._drag_target or original).fold
            if straight:
                p, _, _, fold = self._straight_hit(line.points[i - 1].position, x, y, on_fold)
                vertex, cut = perimeter_target(self._view, net, float(p.x), float(p.y))
            else:
                p = self._editor.origin.quantize(x, y)
                vertex, cut = perimeter_target(self._view, net, x, y)
                fold = fold_target(self._view, net, x, y, prefer=on_fold)
            self._drag_over_perimeter = vertex is not None or cut is not None
            self._drag_target = self._editor.drag_target(i, p, fold=fold, straight=straight, slope=slope)
            self._highlight_fold(None if self._drag_over_perimeter else self._drag_target.fold)
        self.refresh()

    def _update_area(self, *_: object) -> None:
        # The sheet margin is always enough for the pixel-sized decorations at the allowed zoom levels.
        box = self._editor.display_net.bounding_box().expanded(SHEET_MARGIN)
        area = QRectF(float(box.lo.x), float(box.lo.y), float(box.width), float(box.height))
        self.item.set_area(area)
        self.approve_button.set_area(area)
