# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`DemoSheet`: the sheet of an animation. The net, the editor and the tools are the application's own (a
`Workspace`); the mouse input comes from a script (`steps`), sent as real mouse events, so everything reacts as it does
in the app. The user's own mouse and keyboard mean nothing here.

A right click opens the sheet's real menu (`SheetContextMenu`'s items) and Place a vertex its real window, typed into
with real key events. They're shown inside the sheet, under the pointer, rather than as windows of their own (which a
picture of the sheet wouldn't have); they don't wait as they do in the app, so the script goes on meanwhile.
"""

from collections.abc import Iterator, Sequence
from fractions import Fraction as F
from itertools import pairwise

from PyQt6.QtCore import QEvent, QObject, QPoint, QPointF, QSize, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication, QFrame, QLineEdit, QWidget

from cube_net.core.body import CUBE
from cube_net.core.bounding import min_area_rectangle
from cube_net.core.geometry import Box, Vec
from cube_net.core.history import History
from cube_net.core.labels import PointLabels
from cube_net.core.net import default_net
from cube_net.core.project import Project
from cube_net.core.project_settings import ProjectSettings
from cube_net.core.sheet import sheet_box
from cube_net.ui.context_menu import ContextMenu
from cube_net.ui.help.demo.pointer import Pointer
from cube_net.ui.help.demo.steps import Keys, Move, Point, Press, Release, RightClick, Step, ToItem, Type, Wait
from cube_net.ui.sheet.bounding_item import BoundingItem
from cube_net.ui.sheet.cursors import CursorKind
from cube_net.ui.sheet.place_vertex_window import PlaceVertexWindow
from cube_net.ui.sheet.sheet_context_menu import PLACE_VERTEX, SheetContextMenu
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

# The keys of `Type`'s characters that aren't typed as text.
SPECIAL_KEYS = {"\t": Qt.Key.Key_Tab, "\n": Qt.Key.Key_Return}


class DemoSheet(QWidget):
    def __init__(
        self,
        size: QSize,
        shown: Box = AROUND_THE_NET,
        labels: bool = False,
        bounds: bool = False,
        parent: QWidget | None = None,
        project: Project | None = None,
    ) -> None:
        """`shown`: what the view shows (as large as it fits), all the time: it's where the net is in every state of
        the animation. `labels`: whether the vertices have their debug labels (an app setting). `bounds`: whether the
        net's minimum-area bounding rectangle is shown, as the Bounds button shows it (green below the project's target
        area). `project`: what's on the sheet at the start, its origin and its names of points (None: a new project's,
        the default net); its style is the caller's to put in place (it's global)."""
        super().__init__(parent)
        self.setFixedSize(size)
        net = default_net() if project is None else project.state.net
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
        if project is not None:
            self.workspace.editor.load(project.state, History())
            tool.reload()
        tool.approve_clicked.connect(tool.approve)  # what the main window's actions do for these buttons
        tool.undo_clicked.connect(tool.undo)
        # The names of the points made on the way (I, J, ...), as in a new project, or the project's own.
        self._names = PointLabels(CUBE) if project is None else project.labels
        # The target area the bounding rectangle is green below.
        self._threshold = (ProjectSettings() if project is None else project.settings).area_threshold
        # The right click's menu and the window of its Place a vertex, while they're open.
        self._context_menu = SheetContextMenu(self.view, tool)
        self.menu: ContextMenu | None = None
        self.place_window: PlaceVertexWindow | None = None
        self._menu_at: Point | None = None
        self._labels = labels
        tool.line_changed.connect(self._show_labels)
        self.workspace.net_changed.connect(self._show_labels)
        self._show_labels()
        self.bounding_item: BoundingItem | None = None
        if bounds:
            self.bounding_item = BoundingItem()
            scene = self.view.scene()
            assert scene is not None
            scene.addItem(self.bounding_item)
            self.workspace.net_changed.connect(self._show_bounds)
            self._show_bounds()
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

    def _show_bounds(self) -> None:
        """The rectangle of the net on display (the rearranged one while it's approved or not), as the app does."""
        assert self.bounding_item is not None
        rectangle = min_area_rectangle(v.position for v in self.workspace.net.vertices)
        self.bounding_item.set_rectangle(rectangle.corners, rectangle.area < self._threshold)

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
                    if not instant:
                        self.pointer.ripple()
                    if self.menu is None:
                        self._pressed = True
                        self._send(QEvent.Type.MouseButtonPress, self._here())
                case Release():
                    if self.menu is not None:
                        self._choose()
                    else:
                        self._pressed = False
                        self._send(QEvent.Type.MouseButtonRelease, self._here())
                case RightClick():
                    if not instant:
                        self.pointer.ripple()
                    self._open_menu()
                case ToItem(item, ms):
                    yield from self._move([self._item_point(item)], ms, instant)
                case Type(text, ms):
                    for char in text:
                        self._type(char)
                        if not instant:
                            yield ms
                case Keys(modifiers):
                    self._modifiers = modifiers
                    self._send(QEvent.Type.MouseMove, self._here())  # the view learns about them from the mouse
                case Wait(ms):
                    if not instant:
                        yield ms

    def _open_menu(self) -> None:
        """The right click's menu, where the mouse is (as `SheetContextMenu` does it)."""
        x, y = self._menu_at = self._here()
        viewport = self.view.viewport()
        assert viewport is not None
        self.menu = ContextMenu(viewport, self._context_menu.items_at(x, y))
        self.menu.move(self.menu.place(self.view.from_sheet(QPointF(x, y)).toPoint()))
        self.menu.show()
        self.pointer.raise_()
        self.workspace.cut_tool.freeze_drag(True)
        self._show_pointer()

    def _item_point(self, item: int) -> Point:
        """The sheet point a little in from the left of the open menu's item `item` (where the mouse goes to it)."""
        assert self.menu is not None, "an item is chosen from an open menu"
        rect = self.menu.item_rect(item)
        at = self.menu.mapToParent(QPoint(rect.left() + rect.height(), rect.center().y()))
        p = self.view.to_sheet(QPointF(at))
        return p.x(), p.y()

    def _choose(self) -> None:
        """A click on the open menu: it closes, and its item under the mouse (if any) does what it does."""
        assert self.menu is not None and self._menu_at is not None
        menu, self.menu = self.menu, None
        item = menu.item_at(menu.mapFromParent(self.view.from_sheet(QPointF(*self._here())).toPoint()))
        menu.hide()
        menu.deleteLater()
        self.workspace.cut_tool.freeze_drag(False)
        if item == PLACE_VERTEX and menu.items[item].enabled:
            self._open_place_window(*self._menu_at)
        self._show_pointer()

    def _open_place_window(self, x: float, y: float) -> None:
        """Place a vertex's window for what a click at (x, y) would make, in the middle of the sheet (as the app's is
        in the middle of its window)."""
        tool = self.workspace.cut_tool
        placement = tool.placement_at(x, y)
        assert placement is not None
        viewport = self.view.viewport()
        assert viewport is not None
        window = PlaceVertexWindow(placement, lambda p: tool.place(placement, p), origin=tool.editor.origin)
        focused = window.focusWidget()
        window.setParent(viewport, Qt.WindowType.Widget)
        window.setAutoFillBackground(True)  # a window has its background filled by the system
        window.adjustSize()
        window.move((viewport.width() - window.width()) // 2, (viewport.height() - window.height()) // 2)
        window.show()
        if focused is not None:
            focused.setFocus()
        self.pointer.raise_()
        tool.freeze_drag(True)
        tool.set_placing(placement)
        self.place_window = window

        def closed(result: int) -> None:
            tool.set_placing(None)
            tool.freeze_drag(False)
            if result != PlaceVertexWindow.DialogCode.Accepted:
                tool.unlock_slope()
            window.deleteLater()
            self.place_window = None
            self._show_pointer()

        window.finished.connect(closed)

    def _type(self, char: str) -> None:
        """A key pressed and released in the open window, where its focus is."""
        assert self.place_window is not None, "keys are typed into an open window"
        target = self.place_window.focusWidget() or self.place_window
        key = SPECIAL_KEYS.get(char)
        text = "" if key is not None else char
        code = key if key is not None else Qt.Key(ord(char.upper()))
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            self._sending = True
            try:
                QApplication.sendEvent(target, QKeyEvent(kind, code, Qt.KeyboardModifier.NoModifier, text))
            finally:
                self._sending = False
        if key is Qt.Key.Key_Tab and isinstance(field := self.place_window.focusWidget(), QLineEdit):
            field.selectAll()  # as Tab does, but it doesn't where the window isn't active (no focus event comes then)

    def _over_window(self, at: QPointF) -> bool:
        """Is the viewport point `at` over the open menu or window?"""
        return any(w is not None and w.geometry().contains(at.toPoint()) for w in (self.menu, self.place_window))

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
        if self.menu is not None and kind == QEvent.Type.MouseMove:
            local = QPointF(self.menu.mapFromParent(pos.toPoint()))
            self._sending = True
            try:
                QApplication.sendEvent(
                    self.menu,
                    QMouseEvent(
                        kind,
                        local,
                        viewport.mapToGlobal(pos),
                        Qt.MouseButton.NoButton,
                        Qt.MouseButton.NoButton,
                        self._modifiers,
                    ),
                )
            finally:
                self._sending = False
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
        over = self._over_window(self.view.from_sheet(QPointF(x, y)))
        kind = CursorKind.ARROW if over else self.workspace.cut_tool.cursor_at(x, y)
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
