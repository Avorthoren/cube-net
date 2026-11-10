"""`Workspace`: a sheet view with the net and the tools that work on it, wired together.

The main window has one; so does every animation of Help -> Help, which plays the real tools with scripted input. What
the cuts do under the mouse follows what the line allows: in CUT_EDITING only the cuts of the net as divided by the line
can be chosen (the line itself means nothing there), and the counterpart of a choosable one blinks; in CUT_APPROVING
nothing follows the mouse but the button.
"""

from PyQt6.QtCore import QObject, pyqtSignal

from cube_net.core.cutting import CutLine
from cube_net.core.editor import Editor, EditorState
from cube_net.core.labels import PointLabels, cut_line_labels, vertex_labels
from cube_net.core.net import Net
from cube_net.core.sheet import sheet_box
from cube_net.ui.sheet.counterpart_blink import CounterpartBlink
from cube_net.ui.sheet.cut_hover import CutHover
from cube_net.ui.sheet.cut_tool import CutTool
from cube_net.ui.sheet.ruler_tool import RulerTool
from cube_net.ui.sheet.sheet_cursor import SheetCursor
from cube_net.ui.sheet.sheet_view import SheetView


class Workspace(QObject):
    # The editor's net changed (a rearrangement, an approval, undo, redo) and the view shows the new one now.
    net_changed = pyqtSignal()

    def __init__(self, view: SheetView, net: Net, mouse_cursor: bool = True) -> None:
        """`mouse_cursor`: whether the mouse pointer over the view shows what a click would do (not for animations,
        where the real mouse means nothing)."""
        super().__init__(view)
        self.view = view
        self.cut_hover = CutHover(view, net)
        self.counterpart_blink = CounterpartBlink(view)
        self.ruler_tool = RulerTool(view)
        self.editor = Editor(net)
        self.cut_tool = CutTool(view, self.editor, self.ruler_tool)
        self.cut_tool.line_changed.connect(self.update_hover_net)
        self.cut_tool.net_changed.connect(self._on_net_changed)
        self.cut_hover.hover_changed.connect(self.update_divided_view)
        self.cut_hover.set_target(self.cut_tool.hover_target)
        view.set_press_claim(self.cut_tool.claims)
        self.sheet_cursor = SheetCursor(view, self.cut_tool, self.ruler_tool) if mouse_cursor else None

    @property
    def net(self) -> Net:
        """The net on display (the rearranged one in CUT_APPROVING)."""
        return self.editor.display_net

    def show_labels(self, names: PointLabels | None) -> None:
        """The debug labels of the shown net's vertices and of the cut line's new points and images, with `names`
        (None: no labels)."""
        self.view.set_vertex_labels(vertex_labels(self.net, names) if names is not None else None)
        points = self.cut_tool.item.points()
        try:
            cut_labels = cut_line_labels(self.editor.net, CutLine(list(points)), names) if names is not None else []
        except ValueError:  # a point is being dragged off the net: it has no cube point to name for now
            cut_labels = []
        self.cut_tool.item.set_labels(cut_labels)

    def _on_net_changed(self) -> None:
        """Show the net the editor has now: the sheet follows it, and what's on screen stays where it was."""
        net = self.net
        self.view.set_sheet(sheet_box(v.position for v in net.vertices))
        self.view.set_net(net)
        rearranged = self.editor.rearranged
        item = self.view.net_item()
        assert item is not None
        item.set_glue((rearranged.kept, rearranged.moved) if rearranged is not None else ())
        item.set_overlapping(rearranged.overlapping if rearranged is not None else frozenset())
        self.update_hover_net()
        self.net_changed.emit()

    def update_divided_view(self) -> None:
        """While a perimeter edge is hovered in CUT_EDITING (ruler off, nothing being dragged), show which parts of the
        cuts can't be chosen for gluing; if the hovered one can be, its counterpart blinks."""
        item = self.view.net_item()
        if item is None:
            return
        show = (
            self.editor.state is EditorState.CUT_EDITING
            and not self.ruler_tool.active
            and not self.cut_tool.dragging
            and self.cut_hover.hovered() is not None
        )
        split = self.editor.split() if show else None
        item.set_divided(split)
        hovered = self.cut_hover.hovered()
        if split is None or hovered is None or hovered in split.same_half_cuts:
            self.counterpart_blink.set_cut(None)
        else:
            self.counterpart_blink.set_cut(split.net.counterpart(hovered))

    def update_hover_net(self) -> None:
        """Which cuts follow the mouse (see the module's docstring)."""
        net = self.net
        if self.editor.state is EditorState.CUT_EDITING:
            if not self.cut_tool.dragging:
                split = self.editor.split()
                self.cut_hover.set_net(split.net, split.line_edges, vertices=False)
        elif self.editor.state is EditorState.CUT_APPROVING:
            self.cut_hover.set_net(net, frozenset(net.boundary_edges()), vertices=False)
        else:
            self.cut_hover.set_net(net)
        self.update_divided_view()
