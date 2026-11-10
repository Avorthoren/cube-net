# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`SessionRecorder`: an application-wide event filter that writes user input into a `SessionLog`.

Line format (after the time in seconds since start):

    press L 11.250,12.500 [S]      mouse button on the sheet, in sheet coordinates; [C]trl [S]hift [A]lt [M]eta
    release L 11.250,12.500
    dblclick L 11.250,12.500
    drag 11.300,12.600             mouse moved with a button held (at most every 50 ms)
    wheel +1 11.250,12.500         wheel notches (positive = scroll up / zoom in) at a sheet point
    view 135.000 11.500,12.000     zoom (px per unit) and the sheet point at the view's center, whenever it changed
    key Ctrl+Z                     key press (no auto-repeat, no lone modifier keys)
    shortcut R                     key press that triggered a menu/toolbar shortcut (no plain key press then)
    press L QMenu"View" 12,40      mouse input outside the sheet: widget and pixel position in it
    menu "Show vertex labels (development)"   menu item chosen with the mouse
    resize 1600x900                main window size

Mouse moves without buttons are not recorded. Anything else worth recording can be added with `note()`. `state ...`
lines tell the state a recording starts from; `state snapshot` holds the whole project (see `snapshots`).
"""

from __future__ import annotations

import time

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QObject, QPointF, Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QKeySequence, QMouseEvent, QShortcutEvent, QWheelEvent
from PyQt6.QtWidgets import QAbstractButton, QMenu, QWidget

from cube_net.ui.session.session_log import SessionLog
from cube_net.ui.sheet.sheet_view import SheetView

# Mouse moves with a button held are recorded at most this often (seconds).
DRAG_INTERVAL = 0.05

_BUTTONS = {
    Qt.MouseButton.LeftButton: "L",
    Qt.MouseButton.RightButton: "R",
    Qt.MouseButton.MiddleButton: "M",
}
_MODIFIERS = (
    (Qt.KeyboardModifier.ControlModifier, "C"),
    (Qt.KeyboardModifier.ShiftModifier, "S"),
    (Qt.KeyboardModifier.AltModifier, "A"),
    (Qt.KeyboardModifier.MetaModifier, "M"),
)
_MODIFIER_KEYS = {
    Qt.Key.Key_Control,
    Qt.Key.Key_Shift,
    Qt.Key.Key_Alt,
    Qt.Key.Key_Meta,
    Qt.Key.Key_AltGr,
    Qt.Key.Key_CapsLock,
}
_MOUSE_KINDS = {
    QEvent.Type.MouseButtonPress: "press",
    QEvent.Type.MouseButtonRelease: "release",
    QEvent.Type.MouseButtonDblClick: "dblclick",
}


def format_point(p: QPointF) -> str:
    return f"{p.x():.3f},{p.y():.3f}"


def format_modifiers(modifiers: Qt.KeyboardModifier) -> list[str]:
    letters = "".join(letter for flag, letter in _MODIFIERS if modifiers & flag)
    return [f"[{letters}]"] if letters else []


class SessionRecorder(QObject):
    def __init__(self, log: SessionLog, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._log = log
        self._sheet: SheetView | None = None
        self._main_window: QWidget | None = None
        self._last_event: tuple[object, ...] | None = None
        self._last_drag = -1.0
        self._last_view: str | None = None

    @property
    def log(self) -> SessionLog:
        return self._log

    def watch_sheet(self, view: SheetView) -> None:
        """Record positions over this view in sheet coordinates, and record its zoom/scroll state."""
        self._sheet = view
        view.destroyed.connect(self._forget_sheet)

    def watch_main_window(self, window: QWidget) -> None:
        """Record this window's size changes."""
        self._main_window = window
        window.destroyed.connect(self._forget_main_window)

    def detach(self) -> None:
        """Stop watching the sheet and the window (when the recording ends)."""
        for widget, slot in ((self._sheet, self._forget_sheet), (self._main_window, self._forget_main_window)):
            if widget is not None and not sip.isdeleted(widget):
                widget.destroyed.disconnect(slot)
        self._sheet = None
        self._main_window = None

    def schedule_view_record(self) -> None:
        """Record the view state once pending events (zooming, scrolling) have been handled."""
        QTimer.singleShot(0, lambda: self.record_view())  # a lambda: safe even if this recorder is gone by then

    def _forget_sheet(self) -> None:
        self._sheet = None

    def _forget_main_window(self) -> None:
        self._main_window = None

    def note(self, kind: str, *fields: object) -> None:
        """Record something the application did (not direct user input)."""
        self._log.write(kind, *fields)

    def record_view(self) -> None:
        """Record the sheet's zoom and center if they changed since the last record."""
        if self._log.closed or self._sheet is None or sip.isdeleted(self._sheet):
            return
        center = self._sheet.to_sheet(QPointF(self._sheet.viewport().rect().center()))
        state = f"{self._sheet.scale_factor():.3f} {format_point(center)}"
        if state != self._last_view:
            self._last_view = state
            self._log.write("view", state)

    # --- event filter -----------------------------------------------------------------------------------------------

    def eventFilter(self, obj: QObject | None, event: QEvent | None) -> bool:
        if event is None:
            return False
        if event.type() == QEvent.Type.Shortcut and isinstance(event, QShortcutEvent):
            self._shortcut(event)  # delivered to the QAction, which is not a widget
            return False
        if not isinstance(obj, QWidget):
            return False
        kind = event.type()
        if kind in _MOUSE_KINDS and isinstance(event, QMouseEvent):
            if self._first_time(event):
                self._mouse(obj, event, _MOUSE_KINDS[kind])
        elif kind == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
            if event.buttons() != Qt.MouseButton.NoButton and self._first_time(event):
                self._drag(obj, event)
        elif kind == QEvent.Type.Wheel and isinstance(event, QWheelEvent):
            if self._first_time(event):
                self._wheel(obj, event)
        elif kind == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            if self._first_time(event):
                self._key(event)
        elif kind == QEvent.Type.Resize and obj is self._main_window:
            self._log.write("resize", f"{obj.width()}x{obj.height()}")
        return False  # never consume events: recording must not change behaviour

    # --- recording --------------------------------------------------------------------------------------------------

    def _first_time(self, event: QMouseEvent | QWheelEvent | QKeyEvent) -> bool:
        """Qt offers an unhandled event to the parent widgets too; record it only once.

        The same event object comes back with the same content, so it's identified by object id plus content (ids of
        deleted events can be reused, and synthesized events may all have timestamp 0)."""
        if isinstance(event, QKeyEvent):
            detail: tuple[object, ...] = (event.key(), int(event.modifiers().value))
        elif isinstance(event, QWheelEvent):
            detail = (event.angleDelta().y(), event.globalPosition().x(), event.globalPosition().y())
        else:
            detail = (int(event.button().value), event.globalPosition().x(), event.globalPosition().y())
        key = (id(event), int(event.type().value), event.timestamp(), *detail)
        if key == self._last_event:
            return False
        self._last_event = key
        return True

    def _where(self, obj: QWidget, pos: QPointF) -> list[str]:
        if self._sheet is not None and obj is self._sheet.viewport():
            return [format_point(self._sheet.to_sheet(pos))]
        name = type(obj).__name__
        text = obj.title() if isinstance(obj, QMenu) else obj.text() if isinstance(obj, QAbstractButton) else ""
        label = f'{name}"{text}"' if text else name
        return [label, f"{round(pos.x())},{round(pos.y())}"]

    def _mouse(self, obj: QWidget, event: QMouseEvent, kind: str) -> None:
        button = _BUTTONS.get(event.button(), str(int(event.button().value)))
        self._log.write(kind, button, *self._where(obj, event.position()), *format_modifiers(event.modifiers()))
        if kind == "release" and isinstance(obj, QMenu):
            action = obj.actionAt(event.position().toPoint())
            if action is not None and action.isEnabled() and not action.isSeparator():
                self._log.write("menu", f'"{action.text().replace("&", "")}"')
        self._after_input(obj)

    def _drag(self, obj: QWidget, event: QMouseEvent) -> None:
        now = self._log_clock()
        if now - self._last_drag < DRAG_INTERVAL:
            return
        self._last_drag = now
        self._log.write("drag", *self._where(obj, event.position()), *format_modifiers(event.modifiers()))

    def _wheel(self, obj: QWidget, event: QWheelEvent) -> None:
        notches = event.angleDelta().y() / 120
        amount = f"{notches:+.0f}" if notches == int(notches) else f"{notches:+.2f}"
        self._log.write("wheel", amount, *self._where(obj, event.position()), *format_modifiers(event.modifiers()))
        self._after_input(obj)

    def _key(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat() or Qt.Key(event.key()) in _MODIFIER_KEYS:
            return
        self._log.write("key", QKeySequence(event.keyCombination()).toString() or f"0x{event.key():x}")
        self.schedule_view_record()

    def _shortcut(self, event: QShortcutEvent) -> None:
        # Shortcut events go to one action only (they are not offered to parents), so no de-duplication.
        self._log.write("shortcut", event.key().toString())
        self.schedule_view_record()

    def _after_input(self, obj: QWidget) -> None:
        if self._sheet is not None and obj is self._sheet.viewport():
            self.schedule_view_record()  # after the view has handled the event

    @staticmethod
    def _log_clock() -> float:
        return time.monotonic()
