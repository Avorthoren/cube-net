"""`CutTool`: turns mouse input on the sheet into editor actions for the cut line (docs/idea.txt).

- A click on a perimeter vertex (inside its circle) or on a cut (inside its hitbox) starts the cut line there, or
  ends it there while cutting. A vertex wins over a cut.
- While cutting, a click inside the net adds a point (on a fold line, if clicked in its hitbox); a thin line follows the
  mouse from the last point (hidden while the ruler is active, which then takes the clicks).
- In CUT_EDITING, a click on a segment's hollow middle circle adds a point there; Shift+click on an inner point deletes
  it; dragging a point moves it, and it's checked when the mouse is released. An endpoint walks along the perimeter and
  snaps to perimeter vertices. An inner point snaps to fold lines, and may not be released in a hitbox of the perimeter.
- A fold line is highlighted while the mouse is in its hitbox, whenever that means a point would land on it: while
  cutting, and while dragging an inner point.
- In CUT_EDITING, a click on a cut of the perimeter (not on a vertex, not on the new line) moves the half with its
  counterpart onto it: CUT_APPROVING.
- Anything that breaks the rules shows the offending segments in black for 200 ms and changes nothing.
"""

import math

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, pyqtSignal

from cube_net.core.cutting import CutPoint
from cube_net.core.editor import Editor, EditorState, Rejection
from cube_net.core.geometry import Vec, quantize
from cube_net.core.net import HalfEdge, NetVertex
from cube_net.core.sheet import SHEET_MARGIN
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.cut_hover import fold_target, perimeter_target
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

    # The halves were rearranged, or that was cancelled: the net to show has changed.
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
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.setInterval(FLASH_MS)
        self._flash_timer.timeout.connect(self._end_flash)
        self._drag_index: int | None = None
        self._drag_target: CutPoint | None = None
        self._drag_over_perimeter = False
        view.left_pressed.connect(self._on_left_pressed)
        view.left_released.connect(self._on_left_released)
        view.mouse_moved.connect(self._on_mouse_moved)
        view.mouse_left.connect(self._on_mouse_left)
        view.zoom_changed.connect(self._update_area)
        ruler.points_changed.connect(self._on_ruler_changed)
        self._update_area()
        self.refresh()

    @property
    def editor(self) -> Editor:
        return self._editor

    @property
    def dragging(self) -> bool:
        return self._drag_index is not None

    def cancel_rearrangement(self) -> None:
        """Back from CUT_APPROVING to CUT_EDITING."""
        self._editor.cancel_rearrangement()
        self.refresh()
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
        if self._editor.state is not EditorState.CUTTING:
            self.item.set_rubber_band(None)
            if self._drag_index is None:
                self._highlight_fold(None)
        self.line_changed.emit()

    def claims(self, x: float, y: float) -> bool:
        """Would a press at sheet point (x, y) act on the cut line's points? (It must not start panning then.)"""
        return (
            not self._ruler.active
            and self._editor.state is EditorState.CUT_EDITING
            and (self._point_at(x, y) is not None or self._midpoint_at(x, y) is not None)
        )

    def _hit(self, x: float, y: float) -> tuple[Vec, HalfEdge | None, NetVertex | None, HalfEdge | None]:
        """What's under the mouse: the point, then a cut or a perimeter vertex, or else a fold line."""
        vertex, cut = perimeter_target(self._view, self._editor.net, x, y)
        on_perimeter = vertex is not None or cut is not None
        fold = None if on_perimeter else fold_target(self._view, self._editor.net, x, y)
        return quantize(x, y), cut, vertex, fold

    def _on_left_pressed(self, x: float, y: float) -> None:
        if self._ruler.active:
            return  # the ruler takes the clicks
        if self._editor.state is EditorState.CUT_EDITING:
            self._press_while_editing(x, y)
            return
        p, cut, vertex, fold = self._hit(x, y)
        before = len(self._editor.cut_line.points) if self._editor.cut_line else 0
        rejection = self._editor.click(p, cut, vertex, fold)
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
            if not self._view.press_modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._drag_index, self._drag_target, self._drag_over_perimeter = i, None, False
                self.line_changed.emit()
            elif 0 < i < len(line.points) - 1:
                position = line.points[i].position
                rejection = self._editor.delete_point(i)
                if rejection is not None:
                    self._reject(rejection, position)
                else:
                    self.refresh()
                    self.edited.emit("delete", i, position)
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

    def _press_on_cut(self, x: float, y: float) -> None:
        split = self._editor.split()
        vertex, cut = perimeter_target(self._view, split.net, x, y)
        if vertex is not None or cut is None:
            return
        rejection = self._editor.glue(cut)
        if rejection is not None:
            self._reject(rejection, (rejection.segment[0] + rejection.segment[1]) / 2)
        elif self._editor.state is EditorState.CUT_APPROVING:
            self.refresh()
            self.net_changed.emit()

    def _on_left_released(self, x: float, y: float) -> None:
        i, target = self._drag_index, self._drag_target
        self._drag_index, self._drag_target = None, None
        self._highlight_fold(None)
        if i is None or target is None:
            return
        rejection = self._editor.move_point(i, target, self._drag_over_perimeter)
        self.refresh()
        if rejection is not None:
            self._reject(rejection, target.position)
        else:
            self.edited.emit("move", i, target.position)

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
        if self._drag_index is not None:
            self._drag_to(x, y)
            return
        line = self._editor.cut_line
        if self._editor.state is not EditorState.CUTTING or self._ruler.active or line is None:
            self.item.set_rubber_band(None)
            self._highlight_fold(None)
            return
        p, cut, vertex, fold = self._hit(x, y)
        self.item.set_rubber_band((line.last.position, self._editor.candidate(p, cut, vertex, fold).position))
        self._highlight_fold(fold)

    def _on_mouse_left(self) -> None:
        self.item.set_rubber_band(None)
        self._highlight_fold(None)

    def _on_ruler_changed(self) -> None:
        if self._ruler.active:
            self.item.set_rubber_band(None)
            self._highlight_fold(None)

    def _highlight_fold(self, fold: HalfEdge | None) -> None:
        net_item = self._view.net_item()
        if net_item is not None:
            net_item.set_highlight_fold(fold)

    def _drag_to(self, x: float, y: float) -> None:
        i = self._drag_index
        line = self._editor.cut_line
        assert i is not None and line is not None
        net = self._editor.net
        vertex, cut = perimeter_target(self._view, net, x, y)
        original = line.points[i]
        if original.on_perimeter:
            self._drag_target = self._editor.drag_target(i, quantize(x, y), vertex=vertex, current=self._drag_target)
        else:
            self._drag_over_perimeter = vertex is not None or cut is not None
            on_fold = (self._drag_target or original).fold
            fold = fold_target(self._view, net, x, y, prefer=on_fold)
            self._drag_target = self._editor.drag_target(i, quantize(x, y), fold=fold)
            self._highlight_fold(None if self._drag_over_perimeter else fold)
        self.refresh()

    def _update_area(self, *_: object) -> None:
        # The sheet margin is always enough for the pixel-sized decorations at the allowed zoom levels.
        box = self._editor.display_net.bounding_box().expanded(SHEET_MARGIN)
        self.item.set_area(QRectF(float(box.lo.x), float(box.lo.y), float(box.width), float(box.height)))
