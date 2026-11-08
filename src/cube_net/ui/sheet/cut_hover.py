"""`CutHover`: highlights the cut or perimeter vertex under the mouse (docs/idea.txt, DEFAULT state, rule 1)."""

from fractions import Fraction

from PyQt6.QtCore import QObject, pyqtSignal

from cube_net.core.geometry import quantize
from cube_net.core.net import HalfEdge, Net, NetVertex, boundary_edge_at, boundary_vertex_at, fold_edge_at
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.sheet_view import SheetView


def cut_hitbox(view: SheetView) -> Fraction:
    """The width of cut hitboxes in sheet units at the view's current zoom."""
    return Fraction(net_style.CUT_HITBOX_PX / view.scale_factor()).limit_denominator(100_000)


def vertex_radius(view: SheetView) -> Fraction:
    """The radius of vertex circles in sheet units at the view's current zoom (clicks inside pick the vertex)."""
    return Fraction(net_style.VERTEX_RADIUS_PX / view.scale_factor()).limit_denominator(100_000)


def perimeter_target(view: SheetView, net: Net, x: float, y: float) -> tuple[NetVertex | None, HalfEdge | None]:
    """What a click at sheet point (x, y) would pick on the perimeter: a vertex (inside its circle) or else a cut
    (inside its hitbox), or nothing."""
    p = quantize(x, y)
    vertex = boundary_vertex_at(net, p, vertex_radius(view))
    if vertex is not None:
        return vertex, None
    return None, boundary_edge_at(net, p, cut_hitbox(view))


def fold_target(view: SheetView, net: Net, x: float, y: float, prefer: HalfEdge | None = None) -> HalfEdge | None:
    """The fold line whose hitbox contains sheet point (x, y), if any; `prefer` wins while (x, y) is in its hitbox."""
    half_width = Fraction(net_style.FOLD_HITBOX_PX / 2 / view.scale_factor()).limit_denominator(100_000)
    return fold_edge_at(net, quantize(x, y), half_width, prefer)


class CutHover(QObject):
    """Follows the mouse over `view` and highlights the cut whose hitbox is under it."""

    # The cut under the mouse changed (it may be none now).
    hover_changed = pyqtSignal()

    def __init__(self, view: SheetView, net: Net) -> None:
        super().__init__(view)
        self._view = view
        self._net = net
        self._ignored: frozenset[HalfEdge] = frozenset()
        self._vertices = True
        view.mouse_moved.connect(self._on_mouse_moved)
        view.mouse_left.connect(self.clear)

    def set_net(self, net: Net, ignored: frozenset[HalfEdge] = frozenset(), vertices: bool = True) -> None:
        """Follow the cuts of `net`; those in `ignored` mean nothing, and don't highlight. Without `vertices`, vertices
        mean nothing either: they don't highlight, and the mouse in a vertex's circle isn't on a cut. If that's what it
        follows already, the mouse is still on the same cut, and nothing changes."""
        if net is self._net and ignored == self._ignored and vertices == self._vertices:
            return
        self._net = net
        self._ignored = ignored
        self._vertices = vertices
        self.clear()
        item = self._view.net_item()
        if item is not None:
            item.set_highlight_vertex(None)

    def hovered(self) -> HalfEdge | None:
        item = self._view.net_item()
        return None if item is None else item.highlight()

    def hovered_vertex(self) -> NetVertex | None:
        item = self._view.net_item()
        return None if item is None else item.highlight_vertex()

    def clear(self) -> None:
        self._set(None, None)

    def update_at(self, x: float, y: float) -> None:
        """Highlight the vertex or the cut at sheet point (x, y), if any."""
        if self._view.is_panning():
            self._set(None, None)
            return
        vertex, cut = perimeter_target(self._view, self._net, x, y)
        self._set(vertex, None if cut in self._ignored else cut)

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self.update_at(x, y)

    def _set(self, vertex: NetVertex | None, cut: HalfEdge | None) -> None:
        item = self._view.net_item()
        if item is not None:
            changed = item.highlight() is not cut
            item.set_highlight(cut)
            if self._vertices:
                item.set_highlight_vertex(vertex)
            if changed:
                self.hover_changed.emit()
