"""`CutTool`: turns clicks on the sheet into editor actions for the cut line (docs/idea.txt, DEFAULT and CUTTING).

- A click on a perimeter vertex (inside its circle) or on a cut (inside its hitbox) starts the cut line there, or
  ends it there while cutting. A vertex wins over a cut.
- While cutting, a click inside the net adds a point; a thin line follows the mouse from the last point (hidden while
  the ruler is active, which then takes the clicks).
- A click that breaks the rules shows the offending segment in black for 200 ms.
"""

from PyQt6.QtCore import QObject, QRectF, QTimer, pyqtSignal

from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec, quantize
from cube_net.core.net import HalfEdge, NetVertex
from cube_net.core.sheet import SHEET_MARGIN
from cube_net.ui.sheet.cut_hover import perimeter_target
from cube_net.ui.sheet.cut_line_item import CutLineItem
from cube_net.ui.sheet.ruler_tool import RulerTool
from cube_net.ui.sheet.sheet_view import SheetView

# How long a rejected segment stays black (docs/idea.txt).
FLASH_MS = 200


class CutTool(QObject):
    # A point was added to the cut line (its position; the editor's state tells whether it ended the line).
    point_added = pyqtSignal(Vec)

    # A click was rejected (the position of the point that would have been added).
    rejected = pyqtSignal(Vec)

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
        self._flash_timer.timeout.connect(lambda: self.item.set_flash(None))
        view.left_pressed.connect(self._on_left_pressed)
        view.mouse_moved.connect(self._on_mouse_moved)
        view.mouse_left.connect(lambda: self.item.set_rubber_band(None))
        view.zoom_changed.connect(self._update_area)
        ruler.points_changed.connect(lambda: self.item.set_rubber_band(None) if ruler.active else None)
        self._update_area()
        self.refresh()

    @property
    def editor(self) -> Editor:
        return self._editor

    def refresh(self) -> None:
        """Show the editor's current cut line."""
        line = self._editor.cut_line
        self.item.set_points(line.points if line is not None else ())
        if self._editor.state is not EditorState.CUTTING:
            self.item.set_rubber_band(None)

    def _hit(self, x: float, y: float) -> tuple[Vec, HalfEdge | None, NetVertex | None]:
        vertex, cut = perimeter_target(self._view, self._editor.net, x, y)
        return quantize(x, y), cut, vertex

    def _on_left_pressed(self, x: float, y: float) -> None:
        if self._ruler.active:
            return  # the ruler takes the clicks
        p, cut, vertex = self._hit(x, y)
        before = len(self._editor.cut_line.points) if self._editor.cut_line else 0
        rejection = self._editor.click(p, cut, vertex)
        if rejection is not None:
            self.item.set_flash(rejection.segment)
            self._flash_timer.start()
            self.rejected.emit(rejection.segment[1])
            return
        line = self._editor.cut_line
        if line is not None and len(line.points) > before:
            self.refresh()
            self.point_added.emit(line.last.position)

    def _on_mouse_moved(self, x: float, y: float) -> None:
        line = self._editor.cut_line
        if self._editor.state is not EditorState.CUTTING or self._ruler.active or line is None:
            self.item.set_rubber_band(None)
            return
        p, cut, vertex = self._hit(x, y)
        self.item.set_rubber_band((line.last.position, self._editor.candidate(p, cut, vertex).position))

    def _update_area(self, *_: object) -> None:
        # The sheet margin is always enough for the pixel-sized decorations at the allowed zoom levels.
        box = self._editor.net.bounding_box().expanded(SHEET_MARGIN)
        self.item.set_area(QRectF(float(box.lo.x), float(box.lo.y), float(box.width), float(box.height)))
