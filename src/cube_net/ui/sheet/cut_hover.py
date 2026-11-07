"""`CutHover`: highlights the cut under the mouse (docs/idea.txt, DEFAULT state, rule 1)."""

from fractions import Fraction

from PyQt6.QtCore import QObject

from cube_net.core.geometry import quantize
from cube_net.core.net import HalfEdge, Net, boundary_edge_at
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.sheet_view import SheetView


class CutHover(QObject):
    """Follows the mouse over `view` and highlights the cut whose hitbox is under it."""

    def __init__(self, view: SheetView, net: Net) -> None:
        super().__init__(view)
        self._view = view
        self._net = net
        view.mouse_moved.connect(self._on_mouse_moved)
        view.mouse_left.connect(self.clear)

    def set_net(self, net: Net) -> None:
        self._net = net
        self.clear()

    def hovered(self) -> HalfEdge | None:
        item = self._view.net_item()
        return None if item is None else item.highlight()

    def clear(self) -> None:
        self._set(None)

    def update_at(self, x: float, y: float) -> None:
        """Highlight the cut at sheet point (x, y), if any."""
        if self._view.is_panning():
            self._set(None)
            return
        max_distance = Fraction(net_style.CUT_HITBOX_PX / self._view.scale_factor()).limit_denominator(100_000)
        self._set(boundary_edge_at(self._net, quantize(x, y), max_distance))

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self.update_at(x, y)

    def _set(self, cut: HalfEdge | None) -> None:
        item = self._view.net_item()
        if item is not None:
            item.set_highlight(cut)
