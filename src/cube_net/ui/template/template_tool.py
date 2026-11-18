# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`TemplateTool`: turns mouse input on the template sheet into template editor actions (docs/template_idea.txt).

- INITIAL and LOOPING: a click puts the loop's next vertex where it is (the mouse is the usual arrow). Only the first
  vertex is active: a click in its circle closes the loop, once that makes 3 segments at least. While SHIFT is held, the
  new segment is horizontal or vertical; a locked slope (right click -> Set slope) holds it to that slope instead.
- FINALIZATION:
  - a vertex can be dragged; a click on one (no drag) starts a fold line, which a click on another vertex ends (a click
    anywhere else, or Escape, gives it up);
  - a click on a side's middle circle inserts a vertex there (on release, like a button);
  - Ctrl+click on a vertex deletes it (and its folds), on a fold deletes the fold;
  - a double click inside a face asks for its colour (`face_double_clicked`); a click there drags the sheet.
- Anything that breaks the rules shows the offending segments in black for a moment and changes nothing; a deletion
  that would leave too few vertices says so (`warned`).

The view, the cursor (`SheetCursor`) and the context menu (`SheetContextMenu`) use it as they use `CutTool`.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QObject, QPointF, Qt, QTimer, pyqtSignal

from cube_net.core.cutting import straighten
from cube_net.core.cutting.placement import Action, Constraint, Placement
from cube_net.core.cutting.straight import along
from cube_net.core.geometry import Vec
from cube_net.core.origin import Origin
from cube_net.core.template import (
    MIN_VERTICES_TO_CLOSE,
    Fold,
    Label,
    TemplateEditor,
    TemplateProblem,
    TemplateRejection,
    TemplateState,
    on_the_sheet,
)
from cube_net.ui.i18n import tr
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.cursors import CursorKind
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.template.corners import owned_arcs, shared, vertex_toward
from cube_net.ui.template.template_item import TemplateItem

# How long a rejected segment stays black (as for cuts).
FLASH_MS = 200

# How far (in pixels) the mouse goes with its button held on a vertex before that's a drag, not a click.
DRAG_START_PX = 3.0


def template_problem_text(problem: TemplateProblem) -> str:
    """What to say when a point can't go there (Place a vertex)."""
    match problem:
        case TemplateProblem.OFF_THE_SHEET:
            return tr("The point is off the sheet.")
        case TemplateProblem.TOO_EARLY_TO_CLOSE:
            return tr("The loop needs 3 segments at least.")
        case TemplateProblem.TURNED_OVER:
            return tr("The loop would turn inside out.")
        case TemplateProblem.APART:
            return tr("The net would come apart: its parts may touch, but it must stay one piece.")
        case TemplateProblem.OUTSIDE_THE_LOOP:
            return tr("A fold would be outside the loop.")
        case _:
            return tr("The loop would touch or cross itself, or a fold.")


class TemplateTool(QObject):
    # The template changed (an action, undo, redo).
    changed = pyqtSignal()

    # Nothing in the template changed, but what's drawn over it did (a fold being drawn, a drag): for the cursor.
    line_changed = pyqtSignal()

    # Never emitted (there's no net): for `SheetCursor`, as with `CutTool`.
    net_changed = pyqtSignal()

    # The origin moved (an action, undo, redo).
    origin_changed = pyqtSignal()

    # A locked slope (its direction), or None when it's unlocked.
    slope_changed = pyqtSignal(object)

    # An action was rejected: where (sheet coordinates), and the problem.
    rejected = pyqtSignal(Vec, object)

    # An action was done, for the session log: what ("add", "close", "insert", "move", "delete", "fold", "unfold"),
    # and where.
    acted = pyqtSignal(str, Vec)

    # The user clicked inside a face (its index): it's up to the window to ask for a colour.
    face_double_clicked = pyqtSignal(int)

    # A deletion that isn't allowed: what to tell the user.
    warned = pyqtSignal(str)

    def __init__(self, view: SheetView, editor: TemplateEditor) -> None:
        super().__init__(view)
        self._view = view
        self._editor = editor
        self.item = TemplateItem(editor.template)
        scene = view.scene()
        assert scene is not None
        scene.addItem(self.item)
        self._mouse: tuple[float, float] | None = None
        # A vertex pressed on (it may become a drag or a click), and where the press was.
        self._pressed_vertex: tuple[int, tuple[float, float]] | None = None
        # The vertex being dragged and where it is now.
        self._drag: tuple[int, Vec] | None = None
        # The vertex a fold line is being drawn from.
        self._fold_start: int | None = None
        # The middle circle pressed on (the index of its side).
        self._armed_midpoint: int | None = None
        self._slope: Vec | None = None
        self._frozen = False
        self._placing: Placement | None = None
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.setInterval(FLASH_MS)
        self._flash_timer.timeout.connect(lambda: self.item.set_flash(()))
        view.left_pressed.connect(self._on_left_pressed)
        view.left_released.connect(self._on_left_released)
        view.left_double_clicked.connect(self._on_left_double_clicked)
        view.mouse_moved.connect(self._on_mouse_moved)
        view.mouse_left.connect(self._on_mouse_left)
        view.shift_changed.connect(self._follow_mouse)
        view.ctrl_changed.connect(self._follow_mouse)
        view.set_press_claim(self.claims)
        self.refresh()

    # --- what other parts ask ----------------------------------------------------------------------------------------

    @property
    def editor(self) -> TemplateEditor:
        return self._editor

    @property
    def dragging(self) -> bool:
        return self._drag is not None

    @property
    def slope(self) -> Vec | None:
        return self._slope

    def busy(self) -> bool:
        """A drag or a fold line under way (undo and redo wait)."""
        return self._drag is not None or self._fold_start is not None

    def claims(self, x: float, y: float) -> bool:
        """Does a press here mean something (so that it can't start panning)?"""
        if self._editor.state is not TemplateState.FINALIZATION or self._fold_start is not None:
            return True
        return (
            self._vertex_at(x, y) is not None or self._midpoint_at(x, y) is not None or self._fold_at(x, y) is not None
        )

    def cursor_at(self, x: float, y: float) -> CursorKind:
        if self._editor.state is not TemplateState.FINALIZATION:
            return CursorKind.ARROW  # drawing the loop: the usual mouse (docs/template_idea.txt)
        if self._drag is not None or self._fold_start is not None:
            return CursorKind.PENCIL
        ctrl = self._view.ctrl_held()
        if ctrl and (self._vertex_at(x, y) is not None or self._fold_at(x, y) is not None):
            return CursorKind.DELETE
        if self._midpoint_at(x, y) is not None:
            return CursorKind.PLUS
        if self._vertex_at(x, y) is not None:
            return CursorKind.PENCIL
        return CursorKind.ARROW

    def tooltip_at(self, x: float, y: float) -> str:
        return ""

    def coordinates_at(self, x: float, y: float) -> Vec | None:
        """The exact point under the mouse, or the one a click or the drag would make."""
        if self._drag is not None:
            return self._drag[1]
        vertex = self._drawn_vertex_at(x, y)
        if vertex is not None:
            return self._editor.template.position(vertex)
        side = self._midpoint_at(x, y)
        if side is not None:
            a, b = self._editor.template.loop_sides()[side]
            return (self._editor.template.position(a) + self._editor.template.position(b)) / 2
        return self._next_point(x, y)

    def vertex_at(self, x: float, y: float) -> Vec | None:
        """The vertex under the mouse (its position), if any, while the loop is drawn too: for the right click's menu
        (Move the origin; Assign the vertex, once the loop is closed) and the coordinates hint."""
        vertex = self._drawn_vertex_at(x, y)
        return None if vertex is None else self._editor.template.position(vertex)

    def vertex_id_at(self, x: float, y: float) -> int | None:
        return self._drawn_vertex_at(x, y)

    def can_assign(self) -> bool:
        """Can a vertex get a label now (Assign the vertex)? Once the loop is closed (docs/template_idea.txt: the
        second step), and not while a vertex is dragged."""
        return self._editor.state is TemplateState.FINALIZATION and self._drag is None

    def menu_offered(self, vertex: Vec | None) -> bool:
        """Is there a right click menu here (while drawing the loop, dragging, or over a vertex)?"""
        return self._editor.state is not TemplateState.FINALIZATION or self._drag is not None or vertex is not None

    def placement_at(self, x: float, y: float) -> Placement | None:
        """What a click (or the drag) would place here, for Place a vertex."""
        if self._drag is not None:
            vertex_id, position = self._drag
            return Placement(Action.MOVE, position, Constraint.free(), vertex_id)
        if self._editor.state is TemplateState.FINALIZATION:
            return None
        vertices = self._editor.template.vertices
        p = self._next_point(x, y)
        if not vertices:
            return Placement(Action.START, p, Constraint.free())
        if self._closing_at(x, y):
            return None  # the first vertex: nothing to type
        last = vertices[-1].position
        if self._slope is not None:
            return Placement(Action.ADD, p, Constraint.along(last, self._slope))
        if self._view.shift_held():
            return Placement(Action.ADD, p, Constraint.straight(last, p.y == last.y))
        return Placement(Action.ADD, p, Constraint.free())

    def slope_at(self, x: float, y: float) -> Vec | None:
        """The direction of the segment a click would make (while drawing the loop), for Set slope."""
        vertices = self._editor.template.vertices
        if self._editor.state is not TemplateState.LOOPING or not vertices:
            return None
        d = self._next_point(x, y) - vertices[-1].position
        return None if d.is_zero() else d

    def place(self, placement: Placement, p: Vec) -> str | None:
        """Put the point at `p` as `placement` says (Place a vertex); what's wrong, if it can't go there."""
        if placement.action is Action.MOVE:
            assert placement.index is not None
            rejection = self._editor.move_vertex(placement.index, p)
            if rejection is None:
                self._drag = None
                self._pressed_vertex = None
                self._after_action("move", p)
        else:
            rejection = self._editor.add_point(p)
            if rejection is None:
                self.unlock_slope()
                self._after_action("close" if self._editor.template.closed else "add", p)
        if rejection is not None:
            self._show_rejection(rejection, p)
            return template_problem_text(rejection.problem)
        return None

    # --- what other parts tell ---------------------------------------------------------------------------------------

    def refresh(self) -> None:
        """Show the editor's template as it is now."""
        self.item.set_template(self._editor.template)
        self.item.set_midpoints_shown(self._editor.state is TemplateState.FINALIZATION, self._armed_midpoint)
        self._follow_mouse()

    def undo(self) -> None:
        self.cancel()
        if self._editor.undo():
            self._after_history_step()

    def redo(self) -> None:
        self.cancel()
        if self._editor.redo():
            self._after_history_step()

    def cancel(self) -> None:
        """Give up a fold line being drawn or a drag (the vertex goes back), and unlock a locked slope (Escape)."""
        self._fold_start = None
        self._drag = None
        self._pressed_vertex = None
        self._armed_midpoint = None
        self.item.set_moved(None)
        self.unlock_slope()
        self.refresh()

    def cancel_drag(self) -> None:
        self._drag = None
        self._pressed_vertex = None
        self.item.set_moved(None)
        self.refresh()

    def continue_drag_without_button(self) -> None:
        """The drag goes on though its button was released (Set slope during a drag): the next press ends it."""

    def freeze_drag(self, frozen: bool) -> None:
        """While a window is open, a dragged vertex stays where it is."""
        self._frozen = frozen

    def set_placing(self, placement: Placement | None) -> None:
        self._placing = placement

    def lock_slope(self, direction: Vec) -> None:
        self._slope = direction
        self.slope_changed.emit(direction)
        self._follow_mouse()

    def unlock_slope(self) -> None:
        if self._slope is not None:
            self._slope = None
            self.slope_changed.emit(None)
            self._follow_mouse()

    def move_origin(self, origin: Origin) -> None:
        self._editor.move_origin(origin)
        self.origin_changed.emit()
        self.changed.emit()

    def set_face_color(self, face: int, color: str) -> None:
        before = self._editor.template
        self._editor.set_face_color(face, color)
        if self._editor.template is not before:
            self.refresh()
            self.changed.emit()

    def set_label(self, vertex_id: int, label: Label | None) -> None:
        """Give a vertex a label (Assign the vertex): another vertex mustn't have it."""
        rejection = self._editor.set_label(vertex_id, label)
        assert rejection is None, "the window makes sure no other vertex has the label"
        self.refresh()
        self.changed.emit()

    def reindex(self) -> None:
        self._editor.reindex()
        self.refresh()
        self.changed.emit()

    def align_hatches(self) -> None:
        self._editor.align_hatches()
        self.refresh()
        self.changed.emit()

    def restyle(self) -> None:
        self.item.restyle()

    # --- the mouse ----------------------------------------------------------------------------------------------------

    def _on_left_pressed(self, x: float, y: float) -> None:
        self._mouse = x, y
        if self._editor.state is not TemplateState.FINALIZATION:
            p = self._editor.template.vertices[0].position if self._closing_at(x, y) else self._next_point(x, y)
            rejection = self._editor.add_point(p)
            if rejection is not None:
                self._show_rejection(rejection, p)
                return
            self.unlock_slope()
            self._after_action("close" if self._editor.template.closed else "add", p)
            return
        vertex = self._vertex_at(x, y)
        if self._fold_start is not None:
            start, self._fold_start = self._fold_start, None
            self.item.set_rubber(None)
            if vertex is not None and vertex != start:
                rejection = self._editor.add_fold(start, vertex)
                end = self._editor.template.position(vertex)
                if rejection is not None:
                    self._show_rejection(rejection, end)
                else:
                    self._after_action("fold", end)
            self.refresh()
            return
        if self._view.press_modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._delete_at(x, y)
            return
        side = self._midpoint_at(x, y)
        if side is not None:
            self._armed_midpoint = side
            self.item.set_midpoints_shown(True, side)
            return
        if vertex is not None:
            self._pressed_vertex = vertex, (x, y)

    def _on_left_double_clicked(self, x: float, y: float) -> None:
        """Inside a face (not on anything there, nor while a fold or a drag is under way): ask for its colour."""
        if self._editor.state is not TemplateState.FINALIZATION or self.busy() or self.claims(x, y):
            return
        face = self._editor.template.face_at(self._quantize(x, y))
        if face is not None:
            self.face_double_clicked.emit(face)

    def _on_left_released(self, x: float, y: float) -> None:
        self._mouse = x, y
        if self._armed_midpoint is not None:
            side, self._armed_midpoint = self._armed_midpoint, None
            if self._midpoint_at(x, y) == side:
                a, b = self._editor.template.loop_sides()[side]
                self._editor.insert_vertex(a, b)
                self._after_action(
                    "insert", (self._editor.template.position(a) + self._editor.template.position(b)) / 2
                )
            self.refresh()
            return
        if self._drag is not None:
            vertex_id, p = self._drag
            self._drag = None
            self._pressed_vertex = None
            self.item.set_moved(None)
            rejection = self._editor.move_vertex(vertex_id, p)
            if rejection is not None:
                self._show_rejection(rejection, p)
                self.refresh()
            else:
                self._after_action("move", p)
            return
        if self._pressed_vertex is not None:
            vertex_id, _ = self._pressed_vertex
            self._pressed_vertex = None
            self._fold_start = vertex_id  # a click: a fold line starts here
            self._follow_mouse()

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self._mouse = x, y
        if self._pressed_vertex is not None and self._drag is None and not self._frozen:
            vertex_id, (px, py) = self._pressed_vertex
            pressed = self._view.from_sheet(QPointF(px, py))
            now = self._view.from_sheet(QPointF(x, y))
            if math.hypot(now.x() - pressed.x(), now.y() - pressed.y()) > DRAG_START_PX:
                self._drag = vertex_id, self._editor.template.position(vertex_id)
        if self._drag is not None and not self._frozen:
            p = self._quantize(x, y)
            if on_the_sheet(p):
                self._drag = self._drag[0], p
                self.item.set_moved(self._drag)
        self._follow_mouse()

    def _on_mouse_left(self) -> None:
        self._mouse = None
        self._follow_mouse()

    def _follow_mouse(self) -> None:
        """What's drawn after the mouse: the line from the loop's end or a fold's start, and the highlights."""
        template = self._editor.template
        rubber = None
        highlight: int | None = None
        if self._mouse is not None:
            x, y = self._mouse
            if self._editor.state is TemplateState.LOOPING and not self._view.is_panning():
                end = self._placing.position if self._placing is not None else self._next_point(x, y)
                if self._closing_at(x, y):
                    end = template.vertices[0].position
                    highlight = template.vertices[0].id
                rubber = (template.vertices[-1].position, end)
            elif self._fold_start is not None:
                highlight = self._vertex_at(x, y)
                end = template.position(highlight) if highlight is not None else self._quantize(x, y)
                rubber = (template.position(self._fold_start), end)
            elif self._editor.state is TemplateState.FINALIZATION and self._drag is None:
                highlight = self._vertex_at(x, y)
        fold = self._fold_at(*self._mouse) if self._mouse is not None and self._view.ctrl_held() else None
        self.item.set_rubber(rubber)
        if highlight is None:
            self.item.set_highlight_vertex(None)
        else:
            arcs = owned_arcs(template, highlight) if shared(template, highlight) else None
            self.item.set_highlight_vertex(template.position(highlight), arcs)
        self.item.set_highlight_fold(
            None if fold is None else (template.position(fold.start), template.position(fold.end))
        )
        self.line_changed.emit()

    # --- helpers ------------------------------------------------------------------------------------------------------

    def _delete_at(self, x: float, y: float) -> None:
        vertex = self._vertex_at(x, y)
        if vertex is not None:
            p = self._editor.template.position(vertex)
            rejection = self._editor.delete_vertex(vertex)
            if rejection is None:
                self._after_action("delete", p)
            elif rejection.problem is TemplateProblem.TOO_FEW_VERTICES:
                self.rejected.emit(p, rejection.problem)
                self.warned.emit(tr("A loop keeps 6 vertices at least: this one can't be deleted."))
            else:
                self._show_rejection(rejection, p)
            return
        fold = self._fold_at(x, y)
        if fold is not None:
            self._editor.delete_fold(fold)
            self._after_action("unfold", self._editor.template.position(fold.start))

    def _after_action(self, action: str, p: Vec) -> None:
        self.refresh()
        self.acted.emit(action, p)
        self.changed.emit()

    def _after_history_step(self) -> None:
        self.refresh()
        self.origin_changed.emit()
        self.changed.emit()

    def _show_rejection(self, rejection: TemplateRejection, p: Vec) -> None:
        self.item.set_flash(rejection.segments)
        self._flash_timer.start()
        self.rejected.emit(p, rejection.problem)

    def _quantize(self, x: float, y: float) -> Vec:
        return self._editor.origin.quantize(x, y)

    def _next_point(self, x: float, y: float) -> Vec:
        """The loop's next vertex if the mouse were clicked here: SHIFT's or a locked slope's line from the last one."""
        p = self._quantize(x, y)
        vertices = self._editor.template.vertices
        if self._editor.state is not TemplateState.LOOPING or not vertices:
            return p
        last = vertices[-1].position
        if self._slope is not None:
            return along(last, self._slope, p)
        if self._view.shift_held():
            return straighten(last, p)
        return p

    def _closing_at(self, x: float, y: float) -> bool:
        """Is the mouse in the first vertex's circle, where a click closes the loop?"""
        vertices = self._editor.template.vertices
        if self._editor.state is not TemplateState.LOOPING or len(vertices) < MIN_VERTICES_TO_CLOSE:
            return False
        return self._within(x, y, vertices[0].position, net_style.VERTEX_RADIUS_PX)

    def _vertex_at(self, x: float, y: float) -> int | None:
        """The closed loop's vertex whose circle the mouse is in (the nearest one): what a click acts on. (While the
        loop is drawn, a click there doesn't use a vertex: it puts a point, refused unless it closes the loop.)"""
        if self._editor.state is not TemplateState.FINALIZATION:
            return None
        return self._drawn_vertex_at(x, y)

    def _drawn_vertex_at(self, x: float, y: float) -> int | None:
        """The vertex whose circle the mouse is in (the nearest one), whether the loop is closed or not. Where several
        vertices of the closed loop are at one point, the one owning the direction to the mouse (`corners`); none if
        that's outside the net."""
        template = self._editor.template
        best: tuple[float, int] | None = None
        for v in template.vertices:
            d = self._distance_px(x, y, v.position)
            if d <= net_style.VERTEX_RADIUS_PX and (best is None or d < best[0]):
                best = d, v.id
        if best is None or not shared(template, best[1]):
            return None if best is None else best[1]
        q = template.position(best[1])
        candidates = [v.id for v in template.vertices if v.position == q]
        mouse, point = self._view.from_sheet(QPointF(x, y)), self._view.from_sheet(to_qpointf(q))
        direction = (mouse.x() - point.x(), point.y() - mouse.y())  # in the sheet's directions (y up)
        if direction == (0.0, 0.0):
            return candidates[0]
        return vertex_toward(template, candidates, direction)

    def _midpoint_at(self, x: float, y: float) -> int | None:
        """The loop's side whose middle circle the mouse is in."""
        if self._editor.state is not TemplateState.FINALIZATION or self._vertex_at(x, y) is not None:
            return None
        template = self._editor.template
        mouse = self._quantize(x, y)
        found = None
        for i, (a, b) in enumerate(template.loop_sides()):
            pa, pb = template.position(a), template.position(b)
            if self._within(x, y, (pa + pb) / 2, net_style.midpoint_radius()):
                if (pb - pa).cross(mouse - pa) > 0:
                    return i  # on its side of the line (where the net is): two sides may lie on each other
                found = i if found is None else found
        return found

    def _fold_at(self, x: float, y: float) -> Fold | None:
        """The fold line whose hitbox the mouse is in."""
        template = self._editor.template
        mouse = self._view.from_sheet(QPointF(x, y))
        for fold in template.folds:
            a = self._view.from_sheet(to_qpointf(template.position(fold.start)))
            b = self._view.from_sheet(to_qpointf(template.position(fold.end)))
            if _distance_to_segment(mouse, a, b) <= net_style.FOLD_HITBOX_PX / 2:
                return fold
        return None

    def _within(self, x: float, y: float, p: Vec, radius_px: float) -> bool:
        return self._distance_px(x, y, p) <= radius_px

    def _distance_px(self, x: float, y: float, p: Vec) -> float:
        d = self._view.from_sheet(to_qpointf(p)) - self._view.from_sheet(QPointF(x, y))
        return math.hypot(d.x(), d.y())


def _distance_to_segment(p: QPointF, a: QPointF, b: QPointF) -> float:
    d = b - a
    length2 = d.x() ** 2 + d.y() ** 2
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((p.x() - a.x()) * d.x() + (p.y() - a.y()) * d.y()) / length2))
    closest = a + d * t
    return math.hypot(p.x() - closest.x(), p.y() - closest.y())
