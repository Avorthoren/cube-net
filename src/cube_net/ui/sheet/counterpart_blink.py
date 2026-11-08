"""`CounterpartBlink`: while the user hovers a cut that can be chosen, its counterpart blinks (docs/idea.txt,
CUT_EDITING): regular and invisible in equal parts, so that it's easy to see which cut would come onto the hovered one.
"""

from PyQt6.QtCore import QObject, QTimer

from cube_net.core.net import HalfEdge
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.sheet_view import SheetView


class CounterpartBlink(QObject):
    def __init__(self, view: SheetView) -> None:
        super().__init__(view)
        self._view = view
        self._cut: HalfEdge | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(net_style.COUNTERPART_BLINK_MS)
        self._timer.timeout.connect(self._toggle)

    def cut(self) -> HalfEdge | None:
        return self._cut

    def set_cut(self, cut: HalfEdge | None) -> None:
        """Blink this cut, starting with it invisible at once (None: nothing blinks, everything is visible)."""
        if cut is self._cut:
            return
        self._cut = cut
        item = self._view.net_item()
        if item is not None:
            item.set_hidden_cut(cut)
        if cut is None:
            self._timer.stop()
        else:
            self._timer.start()

    def _toggle(self) -> None:
        item = self._view.net_item()
        if item is not None:
            item.set_hidden_cut(None if item.hidden_cut() is not None else self._cut)
