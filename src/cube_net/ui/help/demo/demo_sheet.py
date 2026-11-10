"""`DemoSheet`: the sheet of an animation. The net, the editor and the tools are the application's own (a
`Workspace`); the mouse input comes from a script (`steps`), sent as real mouse events, so everything reacts as it does
in the app. The user's own mouse and keyboard mean nothing here.
"""

from collections.abc import Iterator, Sequence
from fractions import Fraction as F
from itertools import pairwise

from PyQt6.QtCore import QEvent, QObject, QPointF, QSize, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication, QFrame, QWidget

from cube_net.core.geometry import Box, Vec
from cube_net.core.labels import PointLabels
from cube_net.core.net import default_net
from cube_net.core.sheet import sheet_box
from cube_net.ui.help.demo.pointer import Pointer
from cube_net.ui.help.demo.steps import Keys, Move, Point, Press, Release, Step, Wait
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.sheet.workspace import Workspace

# What the view shows by default: the default net with some room around it.
AROUND_THE_NET = Box(Vec(9, F(48, 5)), Vec(14, F(72, 5)))

# The time between two mouse moves of a `Move` (ms), and how many moves a segment of a `Move` takes when the script is
# run at once (the points of the line still walk along the perimeter as they do when dragged by hand).
FRAME_MS = 16
INSTANT_MOVES = 8

# The events of the user's own mouse and keyboard, which the sheet doesn't get (but the wheel: the view lets it go to
# the page around, which scrolls).
USER_INPUT = {
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseButtonRelease,
    QEvent.Type.MouseButtonDblClick,
    QEvent.Type.MouseMove,
    QEvent.Type.Enter,
    QEvent.Type.Leave,
    QEvent.Type.HoverEnter,
    QEvent.Type.HoverLeave,
    QEvent.Type.HoverMove,
    QEvent.Type.KeyPress,
    QEvent.Type.KeyRelease,
    QEvent.Type.ContextMenu,
}


class DemoSheet(QWidget):
    def __init__(
        self, size: QSize, shown: Box = AROUND_THE_NET, labels: bool = False, parent: QWidget | None = None
    ) -> None:
        """`shown`: what the view shows (as large as it fits), all the time: it's where the net is in every state of
        the animation. `labels`: whether the vertices have their debug labels (an app setting)."""
        super().__init__(parent)
        self.setFixedSize(size)
        net = default_net()
        self.view = SheetView(self, follow_keyboard=False)
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.view.setFixedSize(size)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.view.set_sheet(sheet_box(v.position for v in net.vertices))
        self.view.set_net(net)
        self.view.show_fixed(shown, 1.0)
        self.workspace = Workspace(self.view, net, mouse_cursor=False)
        tool = self.workspace.cut_tool
        tool.approve_clicked.connect(tool.approve)  # what the main window's actions do for these buttons
        tool.undo_clicked.connect(tool.undo)
        # The names of the points made on the way (I, J, ...), as in a new project.
        self._names = PointLabels()
        self._labels = labels
        tool.line_changed.connect(self._show_labels)
        self.workspace.net_changed.connect(self._show_labels)
        self._show_labels()
        viewport = self.view.viewport()
        assert viewport is not None
        self.pointer = Pointer(viewport, self.view.from_sheet)
        self.pointer.resize(size)
        self._mouse: Point | None = None
        self._modifiers = Qt.KeyboardModifier.NoModifier
        self._pressed = False
        self._sending = False
        for widget in (self.view, viewport):
            widget.installEventFilter(self)

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        """Only the script's own events get through."""
        return event is not None and event.type() in USER_INPUT and not self._sending

    def set_labels_shown(self, shown: bool) -> None:
        self._labels = shown
        self._show_labels()

    def _show_labels(self) -> None:
        self.workspace.show_labels(self._names if self._labels else None)

    def mouse(self) -> Point | None:
        return self._mouse

    def place(self, at: Point) -> None:
        """Put the mouse there without anything happening on the way."""
        self._send(QEvent.Type.MouseMove, at)

    def play(self, steps: Sequence[Step], instant: bool = False) -> Iterator[int]:
        """Do the steps one by one, yielding how long to wait (ms) before going on. `instant`: no waiting, and no
        ring for clicks (for a script whose end is where another animation starts)."""
        for step in steps:
            match step:
                case Move(to, ms, via):
                    yield from self._move([*via, to], ms, instant)
                case Press():
                    self._pressed = True
                    if not instant:
                        self.pointer.ripple()
                    self._send(QEvent.Type.MouseButtonPress, self._here())
                case Release():
                    self._pressed = False
                    self._send(QEvent.Type.MouseButtonRelease, self._here())
                case Keys(modifiers):
                    self._modifiers = modifiers
                    self._send(QEvent.Type.MouseMove, self._here())  # the view learns about them from the mouse
                case Wait(ms):
                    if not instant:
                        yield ms

    def _here(self) -> Point:
        assert self._mouse is not None, "a script starts by moving the mouse somewhere"
        return self._mouse

    def _move(self, points: list[Point], ms: int, instant: bool) -> Iterator[int]:
        start = self._mouse if self._mouse is not None else points[0]
        corners = [start, *points]
        lengths = [_distance(a, b) for a, b in pairwise(corners)]
        total = sum(lengths) or 1.0
        frames = len(lengths) * INSTANT_MOVES if instant else max(1, ms // FRAME_MS)
        for frame in range(1, frames + 1):
            share = frame / frames if instant else _ease(frame / frames)
            self._send(QEvent.Type.MouseMove, _along(corners, lengths, share * total))
            if not instant:
                yield FRAME_MS

    def _send(self, kind: QEvent.Type, at: Point) -> None:
        self._mouse = at
        viewport = self.view.viewport()
        assert viewport is not None
        pos = self.view.from_sheet(QPointF(*at))
        moving = kind == QEvent.Type.MouseMove
        button = Qt.MouseButton.NoButton if moving else Qt.MouseButton.LeftButton
        held = Qt.MouseButton.LeftButton if self._pressed else Qt.MouseButton.NoButton
        event = QMouseEvent(kind, pos, viewport.mapToGlobal(pos), button, held, self._modifiers)
        self._sending = True
        try:
            QApplication.sendEvent(viewport, event)
        finally:
            self._sending = False
        self._show_pointer()

    def _show_pointer(self) -> None:
        if self._mouse is None:
            return
        x, y = self._mouse
        kind = self.workspace.cut_tool.cursor_at(x, y)
        ctrl = bool(self._modifiers & Qt.KeyboardModifier.ControlModifier)
        self.pointer.set_state(QPointF(x, y), kind, ctrl)

    def restyle(self) -> None:
        """The style changed: draw the net anew."""
        item = self.view.net_item()
        if item is not None:
            item.restyle()
        scene = self.view.scene()
        if scene is not None:
            scene.update()


def _distance(a: Point, b: Point) -> float:
    return ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5


def _ease(t: float) -> float:
    """Slow at both ends, like a hand moving the mouse."""
    return t * t * (3 - 2 * t)


def _along(corners: list[Point], lengths: list[float], distance: float) -> Point:
    """The point `distance` along the broken line through `corners`."""
    for (a, b), length in zip(pairwise(corners), lengths, strict=True):
        if distance <= length and length > 0:
            t = distance / length
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        distance -= length
    return corners[-1]
