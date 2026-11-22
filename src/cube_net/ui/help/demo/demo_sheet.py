# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`DemoSheet`: the sheet of an animation. The net, the editor and the tools are the application's own (a
`Workspace`); the mouse input comes from a script (`steps`), sent as real mouse events, so everything reacts as it does
in the app. The user's own mouse and keyboard mean nothing here.

A right click opens the sheet's real menu (`SheetContextMenu`'s items), and its items their real windows (Place a
vertex, Set slope, Move the origin), typed into with real key events. They're shown inside the sheet, under the
pointer, rather than as windows of their own (which a picture of the sheet wouldn't have); they don't wait as they do
in the app, so the script goes on meanwhile.
"""

from collections.abc import Callable, Iterator, Sequence
from fractions import Fraction as F
from itertools import pairwise

from PyQt6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QSize, Qt
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QAbstractButton,
    QAbstractSpinBox,
    QApplication,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLineEdit,
    QWidget,
)

from cube_net.core.body import CUBE
from cube_net.core.bounding import min_area_rectangle
from cube_net.core.cutting import slope_of
from cube_net.core.geometry import Box, Vec
from cube_net.core.history import History
from cube_net.core.net import default_net
from cube_net.core.project import Project, TemplateDocument
from cube_net.core.project_settings import ProjectSettings
from cube_net.core.sheet import TEMPLATE_SHEET_HEIGHT, TEMPLATE_SHEET_WIDTH, sheet_box
from cube_net.core.template import TemplateEditor, ValidationStatus, validate
from cube_net.ui import palette
from cube_net.ui.context_menu import ContextMenu
from cube_net.ui.dialogs.message_window import MessageIcon, MessageWindow
from cube_net.ui.help.demo.pointer import Pointer
from cube_net.ui.help.demo.steps import (
    COLOR_CODE,
    DoubleClick,
    Keys,
    Move,
    Paste,
    Point,
    Press,
    Release,
    RightClick,
    Step,
    ToItem,
    ToWidget,
    Type,
    Wait,
)
from cube_net.ui.help.demo.template_panel import TemplatePanel
from cube_net.ui.i18n import TRANSLATIONS, tr
from cube_net.ui.sheet.bounding_item import BoundingItem
from cube_net.ui.sheet.coordinates_hint import CoordinatesHint
from cube_net.ui.sheet.coordinates_text import coordinate_lines
from cube_net.ui.sheet.cursors import CursorKind
from cube_net.ui.sheet.cut_tool import CutTool
from cube_net.ui.sheet.move_origin_window import MoveOriginWindow
from cube_net.ui.sheet.place_vertex_window import PlaceVertexWindow
from cube_net.ui.sheet.set_slope_window import SetSlopeWindow
from cube_net.ui.sheet.sheet_context_menu import ASSIGN_VERTEX, MOVE_ORIGIN, PLACE_VERTEX, SET_SLOPE, SheetContextMenu
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.sheet.workspace import Workspace
from cube_net.ui.style import DEFAULT_CUBE_LOOK, DEFAULT_STYLE, Look
from cube_net.ui.template.assign_vertex_window import AssignVertexWindow
from cube_net.ui.template.template_tool import TemplateTool
from cube_net.ui.template.validate_button import ValidateButton
from cube_net.ui.template.validation_messages import failure_text, no_problems_text, with_save_question

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

# The template sheet (as `TemplateMode`'s).
TEMPLATE_SHEET = Box(Vec(0, 0), Vec(TEMPLATE_SHEET_WIDTH, TEMPLATE_SHEET_HEIGHT))

# The keys of `Type`'s characters that aren't typed as text.
SPECIAL_KEYS = {"\t": Qt.Key.Key_Tab, "\n": Qt.Key.Key_Return}


class DemoSheet(QWidget):
    def __init__(
        self,
        size: QSize,
        shown: Box = AROUND_THE_NET,
        bounds: bool = False,
        parent: QWidget | None = None,
        project: Project | None = None,
        coordinates: bool = False,
        template: TemplateDocument | None = None,
        panel: bool = False,
    ) -> None:
        """`shown`: what the view shows (as large as it fits), all the time: it's where the net is in every state of
        the animation. `bounds`: whether the net's minimum-area bounding rectangle is shown, as the Bounds button shows
        it (green below the project's target area). `project`: what's on the sheet at the start, its origin and its
        look (None: the built-in Cube's, the default net in the default look). The sheet paints in that look whatever
        the open document's is (`SheetView.set_look`). `coordinates`: whether the coordinates hint is next to the
        pointer, as the app shows it. There are no vertex labels, whatever the app's setting. `template`: a template
        being made instead of a project (`project` is then unused): with its look and its windows (a face's colour,
        Assign label, Validate's messages). `panel`: whether the template's instrument panel is down the left side, as
        the window has it (for an animation that clicks its buttons); `shown` is then right of it."""
        super().__init__(parent)
        self.setFixedSize(size)
        net = default_net() if project is None else project.state.net
        self.view = SheetView(self, follow_keyboard=False)
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.view.setFixedSize(size)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if template is not None:
            self.look = Look(template.style or DEFAULT_STYLE, CUBE.colors, CUBE)
        else:
            self.look = DEFAULT_CUBE_LOOK if project is None else _look(project)
        self.view.set_look(self.look)
        viewport = self.view.viewport()
        assert viewport is not None
        # Buttons over the sheet a click may be on, by name (`ToWidget`).
        self._buttons: dict[str, QAbstractButton] = {}
        with self.look.used():
            self.workspace: Workspace | None = None
            self.panel: TemplatePanel | None = None
            self.validate_button: ValidateButton | None = None
            if template is not None:
                self.tool: CutTool | TemplateTool = self._template_tool(template, shown, viewport, size, panel)
                self._context_menu = SheetContextMenu(self.view, self.tool, assign=lambda _vertex: None)
            else:
                self.view.set_sheet(sheet_box(v.position for v in net.vertices))
                self.view.set_net(net)
                self.view.show_fixed(shown, 1.0)
                self.workspace = Workspace(self.view, net, mouse_cursor=False)
                tool = self.tool = self.workspace.cut_tool
                if project is not None:
                    self.workspace.editor.load(project.state, History())
                    tool.reload()
                tool.approve_clicked.connect(tool.approve)  # what the main window's actions do for these buttons
                tool.undo_clicked.connect(tool.undo)
                self._context_menu = SheetContextMenu(self.view, tool)
            # The target area the bounding rectangle is green below.
            self._threshold = (ProjectSettings() if project is None else project.settings).area_threshold
            # The right click's menu and its windows, while they're open.
            self.menu: ContextMenu | None = None
            self.small_window: QDialog | None = None
            self._menu_at: Point | None = None
            self.bounding_item: BoundingItem | None = None
            if bounds and self.workspace is not None:
                self.bounding_item = BoundingItem()
                scene = self.view.scene()
                assert scene is not None
                scene.addItem(self.bounding_item)
                self.workspace.net_changed.connect(self._show_bounds)
                self._show_bounds()
            self.coordinates_hint = CoordinatesHint(viewport) if coordinates else None
            self.pointer = Pointer(viewport, self.view.from_sheet)
            self.pointer.resize(size)
            self._mouse: Point | None = None
            self._modifiers = Qt.KeyboardModifier.NoModifier
            self._pressed = False
            self._sending = False
            for widget in (self.view, viewport):
                widget.installEventFilter(self)

    def _template_tool(
        self, document: TemplateDocument, shown: Box, viewport: QWidget, size: QSize, panel: bool
    ) -> TemplateTool:
        """A template being made (as `TemplateMode` shows one), with the instrument panel if wanted."""
        self.view.set_sheet(TEMPLATE_SHEET)
        editor = TemplateEditor()
        editor.load(document.state, History())
        tool = TemplateTool(self.view, editor)
        tool.refresh()
        tool.face_double_clicked.connect(self._open_color_window)
        self._shown = shown
        if panel:
            self.panel = TemplatePanel(viewport, size.height())
            self.validate_button = self.panel.validate
            self.validate_button.set_status(document.validation)
            self.validate_button.clicked.connect(self._validate)
            self.panel.draw_hole.clicked.connect(self._start_hole)
            self._buttons = self.panel.buttons
            self.panel.update(tool)
            TRANSLATIONS.changed.connect(self._fit_panel)
        self._show_template(size)
        return tool

    def _show_template(self, size: QSize) -> None:
        """`shown` as large as it fits right of the panel, next to it, in the middle from top to bottom."""
        left = 0 if self.panel is None else self.panel.width()
        box = self._shown
        width, height = size.width() - left, size.height()
        scale = min(width / float(box.width), height / float(box.height))
        room = F(height / scale) - box.height
        start = Vec(box.lo.x - F(left / scale), box.lo.y - room / 2)
        self.view.show_fixed(Box(start, start + Vec(F(size.width() / scale), F(height / scale))), 1.0)

    def _fit_panel(self) -> None:
        """The panel as wide as its texts in the language now, and the template right of it."""
        if self.panel is not None:
            self.panel.fit()
            self._show_template(self.size())

    def _start_hole(self) -> None:
        """Draw hole (as the window's `_on_draw_hole`)."""
        assert isinstance(self.tool, TemplateTool)
        if self.tool.can_start_hole():
            self.tool.start_hole()

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        """Only the script's own events get through."""
        return event is not None and event.type() in USER_INPUT and not self._sending

    def _show_bounds(self) -> None:
        """The rectangle of the net on display (the rearranged one while it's approved or not), as the app does."""
        assert self.bounding_item is not None
        rectangle = min_area_rectangle(v.position for v in self.workspace.net.vertices)
        self.bounding_item.set_rectangle(rectangle.corners, rectangle.area < self._threshold)

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
                    if (button := self._button_here()) is not None:
                        button.setDown(button.isEnabled())
                    elif self._over_small_window():
                        self._click_in_window()
                    elif self.menu is None and not self._over_panel():
                        self._pressed = True
                        self._send(QEvent.Type.MouseButtonPress, self._here())
                case Release():
                    if self.menu is not None:
                        self._choose()
                    elif (button := self._button_here()) is not None:
                        button.setDown(False)
                        with self.look.used():
                            button.click()
                        self._show_pointer()
                    elif self._over_panel() or self._over_small_window():
                        pass
                    else:
                        self._pressed = False
                        self._send(QEvent.Type.MouseButtonRelease, self._here())
                case DoubleClick():
                    if not instant:
                        self.pointer.ripple()
                    for kind in (
                        QEvent.Type.MouseButtonPress,
                        QEvent.Type.MouseButtonRelease,
                        QEvent.Type.MouseButtonDblClick,
                        QEvent.Type.MouseButtonRelease,
                    ):
                        self._pressed = kind != QEvent.Type.MouseButtonRelease
                        self._send(kind, self._here())
                case Paste(text):
                    self._paste(text)
                case ToWidget(name, ms):
                    yield from self._move([self._widget_point(name)], ms, instant)
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
        with self.look.used():
            self._open_menu_here()

    def _open_menu_here(self) -> None:
        x, y = self._menu_at = self._here()
        viewport = self.view.viewport()
        assert viewport is not None
        self.menu = ContextMenu(viewport, self._context_menu.items_at(x, y))
        self.menu.move(self.menu.place(self.view.from_sheet(QPointF(x, y)).toPoint()))
        self.menu.show()
        self.pointer.raise_()
        self.tool.freeze_drag(True)
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
        with self.look.used():
            self._choose_here()

    def _choose_here(self) -> None:
        assert self.menu is not None and self._menu_at is not None
        menu, self.menu = self.menu, None
        item = menu.item_at(menu.mapFromParent(self.view.from_sheet(QPointF(*self._here())).toPoint()))
        menu.hide()
        menu.deleteLater()
        tool = self.tool
        tool.freeze_drag(False)
        x, y = self._menu_at
        if item is None or not menu.items[item].enabled:
            pass
        elif item == PLACE_VERTEX:
            self._open_place_window(x, y)
        elif item == SET_SLOPE:
            self._open_slope_window(x, y)
        elif item == MOVE_ORIGIN:
            self._open_origin_window(x, y)
        elif item == ASSIGN_VERTEX:
            self._open_assign_window(x, y)
        self._show_pointer()

    def _open_place_window(self, x: float, y: float) -> None:
        """Place a vertex's window for what a click at (x, y) would make (as `SheetContextMenu.open_window`)."""
        tool = self.tool
        placement = tool.placement_at(x, y)
        assert placement is not None
        window = PlaceVertexWindow(placement, lambda p: tool.place(placement, p), origin=tool.editor.origin)
        tool.freeze_drag(True)
        tool.set_placing(placement)

        def closed(result: int) -> None:
            tool.set_placing(None)
            tool.freeze_drag(False)
            if result != PlaceVertexWindow.DialogCode.Accepted:
                tool.unlock_slope()

        self._open(window, closed)

    def _open_slope_window(self, x: float, y: float) -> None:
        """Set slope's window for the segment a click at (x, y) would make (as `SheetContextMenu.open_slope_window`):
        accepted, the slope is locked."""
        tool = self.tool
        slope = tool.slope_at(x, y)
        assert slope is not None
        window = SetSlopeWindow(*slope_of(slope))
        tool.freeze_drag(True)

        def closed(result: int) -> None:
            tool.freeze_drag(False)
            direction = window.direction()
            if result == SetSlopeWindow.DialogCode.Accepted and direction is not None:
                if tool.dragging:
                    tool.continue_drag_without_button()
                tool.lock_slope(direction)
            elif tool.dragging:
                tool.cancel_drag()

        self._open(window, closed)

    def _open_origin_window(self, x: float, y: float) -> None:
        """Move the origin's window for the drawn point at (x, y) (as `SheetContextMenu.open_origin_window`)."""
        tool = self.tool
        vertex = tool.vertex_at(x, y)
        assert vertex is not None
        origin = tool.editor.origin
        window = MoveOriginWindow(origin.shown(vertex))

        def closed(result: int) -> None:
            coordinates = window.coordinates()
            if result == MoveOriginWindow.DialogCode.Accepted and coordinates is not None:
                tool.move_origin(origin.moved(vertex, coordinates, None))

        self._open(window, closed)

    def _open_assign_window(self, x: float, y: float) -> None:
        """Assign label's window for the template's vertex at (x, y) (as `TemplateMode` opens it)."""
        assert isinstance(self.tool, TemplateTool)
        tool = self.tool
        template = tool.editor.template
        position = tool.vertex_at(x, y)
        vertex = next(v for v in template.all_vertices if v.position == position)
        window = AssignVertexWindow(
            vertex.label,
            lambda label: (owner := template.label_owner(label)) is not None and owner.id != vertex.id,
            template.first_free_index,
        )

        def closed(result: int) -> None:
            if result == AssignVertexWindow.DialogCode.Accepted:
                tool.set_label(vertex.id, window.label())
                self._template_changed()

        self._open(window, closed)

    def _open_color_window(self, face: int) -> None:
        """A face's colour window (as `TemplateMode` opens it; `Paste` gives it a colour)."""
        assert isinstance(self.tool, TemplateTool)
        tool = self.tool
        picker = QColorDialog()
        picker.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)
        picker.setCurrentColor(QColor(tool.editor.template.faces[face].color or palette.WHITE.name()))
        picker.setWindowTitle(tr("Face color"))

        def closed(result: int) -> None:
            if result == QColorDialog.DialogCode.Accepted:
                tool.set_face_color(face, picker.currentColor().name().upper())
                self._template_changed()

        self._open(picker, closed)

    def _validate(self) -> None:
        """Validate (as `TemplateMode.validate`): the first problem in a message; or that there's none, and whether to
        save the template (an animation has no file: either answer just closes it)."""
        assert isinstance(self.tool, TemplateTool) and self.validate_button is not None
        failure = validate(self.tool.editor.template)
        buttons = QDialogButtonBox.StandardButton
        if failure is None:
            self.tool.align_hatches()  # the pieces of each face hatched alike
            self.validate_button.set_status(ValidationStatus.VALID)
            window = MessageWindow("Cube Net", with_save_question(no_problems_text()), icon=MessageIcon.QUESTION)
            yes = window.add_standard(buttons.Yes)
            no = window.add_standard(buttons.No)
            window.set_default(yes)  # (as `ask_yes_no`)
            window.set_escape(no)
        else:
            self.validate_button.set_status(ValidationStatus.INVALID)
            window = MessageWindow("Cube Net", failure_text(failure), icon=MessageIcon.WARNING)
            ok = window.add_standard(buttons.Ok)
            window.set_default(ok)
            window.set_escape(ok)
        window.adjustSize()
        self._open(window, lambda _result: None)

    def _template_changed(self) -> None:
        """The template isn't the one validated any more."""
        if self.validate_button is not None:
            self.validate_button.set_status(ValidationStatus.UNDEFINED)

    def _paste(self, text: str) -> None:
        """`text` pasted into the open window: a colour window takes it as its colour; elsewhere, the field with the
        focus."""
        window = self.small_window
        assert window is not None, "text is pasted into an open window"
        with self.look.used():
            if isinstance(field := window.focusWidget(), QLineEdit):
                field.insert(text)  # (in place of what's selected; the colour window's code: its colour)
            elif isinstance(window, QColorDialog):
                window.setCurrentColor(QColor(text))

    def _button_here(self) -> QAbstractButton | None:
        """The button over the sheet the mouse is on, if any."""
        at = self.view.from_sheet(QPointF(*self._here())).toPoint()
        return next((b for b in self._buttons.values() if b.isVisible() and self._area(b).contains(at)), None)

    def _over_panel(self) -> bool:
        """Is the mouse over the instrument panel?"""
        at = self.view.from_sheet(QPointF(*self._here())).toPoint()
        return self.panel is not None and self.panel.area().contains(at)

    def _widget_point(self, name: str) -> Point:
        """The sheet point in the middle of the widget `name`: a button on the panel, or the colour window's code."""
        if name == COLOR_CODE:
            assert isinstance(self.small_window, QColorDialog), "the colour's code is the colour window's"
            widget: QWidget = next(f for f in self.small_window.findChildren(QLineEdit) if f.text().startswith("#"))
        else:
            widget = self._buttons[name]
        p = self.view.to_sheet(QPointF(self._area(widget).center()))
        return p.x(), p.y()

    def _over_small_window(self) -> bool:
        at = self.view.from_sheet(QPointF(*self._here())).toPoint()
        return self.small_window is not None and self.small_window.geometry().contains(at)

    def _click_in_window(self) -> None:
        """A click in the open window: a text field under the mouse gets the focus (its text cursor at its end)."""
        assert self.small_window is not None
        at = self.view.from_sheet(QPointF(*self._here())).toPoint()
        field = self.small_window.childAt(self.small_window.mapFromParent(at))
        if isinstance(field, QLineEdit):
            field.setFocus()
            field.deselect()
            field.end(False)

    def _area(self, widget: QWidget) -> QRect:
        """Where a widget over the sheet is, in the viewport's pixels."""
        viewport = self.view.viewport()
        assert viewport is not None
        return QRect(widget.mapTo(viewport, QPoint(0, 0)), widget.size())

    def _open(self, window: QDialog, closed: Callable[[int], None]) -> None:
        """Show `window` in the middle of the sheet (as the app's are in the middle of its window), with the focus
        where it puts it; `closed` gets its result when it closes."""
        viewport = self.view.viewport()
        assert viewport is not None
        focused = window.focusWidget()
        window.setParent(viewport, Qt.WindowType.Widget)
        window.setAutoFillBackground(True)  # a window has its background filled by the system
        window.adjustSize()
        left = 0 if self.panel is None else self.panel.width()  # (in the middle of the sheet right of the panel)
        window.move(left + (viewport.width() - left - window.width()) // 2, (viewport.height() - window.height()) // 2)
        window.show()
        if focused is not None:
            focused.setFocus()
        self.pointer.raise_()
        self.small_window = window

        def finished(result: int) -> None:
            with self.look.used():
                closed(result)
            window.deleteLater()
            self.small_window = None
            self._show_pointer()

        window.finished.connect(finished)

    def _type(self, char: str) -> None:
        """A key pressed and released in the open window, where its focus is."""
        with self.look.used():
            self._type_here(char)

    def _type_here(self, char: str) -> None:
        assert self.small_window is not None, "keys are typed into an open window"
        target = self.small_window.focusWidget() or self.small_window
        key = SPECIAL_KEYS.get(char)
        ctrl = bool(self._modifiers & Qt.KeyboardModifier.ControlModifier)
        text = "" if key is not None or ctrl else char
        code = key if key is not None else Qt.Key(ord(char.upper()))
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            self._sending = True
            try:
                QApplication.sendEvent(target, QKeyEvent(kind, code, self._modifiers, text))
            finally:
                self._sending = False
        field = self.small_window.focusWidget() if self.small_window is not None else None  # (Enter closes it)
        if key is Qt.Key.Key_Tab and isinstance(field, QLineEdit | QAbstractSpinBox):
            field.selectAll()  # as Tab does, but it doesn't where the window isn't active (no focus event comes then)

    def _over_window(self, at: QPointF) -> bool:
        """Is the viewport point `at` over the open menu or window, or the instrument panel?"""
        windows = [w.geometry() for w in (self.menu, self.small_window) if w is not None]
        if self.panel is not None:
            windows.append(self.panel.area())
        return any(area.contains(at.toPoint()) for area in windows)

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
        with self.look.used():
            self._show_pointer_at(x, y)

    def _show_pointer_at(self, x: float, y: float) -> None:
        if self.panel is not None and isinstance(self.tool, TemplateTool):
            self.panel.update(self.tool)
            self.panel.hover(self._button_here())
        over = self._over_window(self.view.from_sheet(QPointF(x, y)))
        kind = CursorKind.ARROW if over else self.tool.cursor_at(x, y)
        ctrl = bool(self._modifiers & Qt.KeyboardModifier.ControlModifier)
        self.pointer.set_state(QPointF(x, y), kind, ctrl)
        if self.coordinates_hint is not None:
            tool = self.tool
            point = None if over else tool.coordinates_at(x, y)
            if point is None:
                self.coordinates_hint.hide()
            else:
                lines = coordinate_lines(tool.editor.origin.shown(point))
                self.coordinates_hint.show_at(lines, self.view.from_sheet(QPointF(x, y)).toPoint())
                self.pointer.raise_()


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


def _look(project: Project) -> Look:
    """The look of `project`: its style and face colours (the default style and its body's own colours, where it has
    none)."""
    settings, body = project.settings, project.state.net.body
    return Look(settings.style or DEFAULT_STYLE, settings.face_colors or body.colors, body)
