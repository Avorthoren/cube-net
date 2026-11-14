# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`ContextMenu`: a context menu drawn inside a window, not as a system popup.

A system popup can't always open: on Wayland, GNOME refuses one while another mouse button is held (during a drag, for
the right click that asks for it), and the menu closes at once. This one is a widget of the window itself, so it opens
wherever the window is: at the mouse, in the window's own coordinates (on Wayland, nothing on the screen is known),
moved left or up as far as needed to fit in the window. It's drawn by the style as a real menu is (its frame, its
items).

`choose` shows it and waits, as `QMenu.exec` does: an item is chosen by a press and a release on it (any button; a
release alone, of a button held before the menu opened, doesn't count), or with the keys (Up, Down, Enter, Space).
Escape, a press anywhere else (which is used up, as with a real menu) and the window losing the focus close it without
a choice. Meanwhile, the rest of the window gets no clicks, no wheel and no keys (no shortcuts either); the mouse's
moves still reach it, so whatever follows the mouse there does as usual.
"""

from dataclasses import dataclass

from PyQt6.QtCore import QEvent, QEventLoop, QObject, QPoint, QRect, QSize, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPalette, QWindow
from PyQt6.QtWidgets import QApplication, QStyle, QStyleOption, QStyleOptionMenuItem, QWidget


@dataclass(frozen=True)
class MenuItem:
    text: str
    enabled: bool = True


class ContextMenu(QWidget):
    def __init__(self, window: QWidget, items: list[MenuItem]) -> None:
        """A menu with `items`, over `window` (a top-level window)."""
        super().__init__(window)
        self._window = window
        self.items = list(items)
        self._current: int | None = None
        self._pressed: int | None = None
        self._chosen: int | None = None
        self._loop: QEventLoop | None = None
        self.setMouseTracking(True)
        self.setAutoFillBackground(False)
        self.resize(self.sizeHint())
        self.hide()

    # --- showing ----------------------------------------------------------------------------------------------------

    def choose(self, at: QPoint) -> int | None:
        """Show the menu at `at` (the window's coordinates) and wait for a choice: the chosen item's index, or None."""
        self._chosen = None
        self._pressed = None
        self._current = None
        self.resize(self.sizeHint())
        self.move(self.place(at))
        self.show()
        self.raise_()
        app = QApplication.instance()
        assert app is not None
        app.installEventFilter(self)
        self._loop = QEventLoop(self)
        try:
            self._loop.exec()
        finally:
            app.removeEventFilter(self)
            self._loop = None
            self.hide()
        return self._chosen

    def place(self, at: QPoint) -> QPoint:
        """Where its top-left corner goes for the mouse at `at`: there, moved left or up as far as needed to fit."""
        size, area = self.size(), self._window.size()
        x = min(at.x(), area.width() - size.width())
        y = min(at.y(), area.height() - size.height())
        return QPoint(max(0, x), max(0, y))

    def close_with(self, index: int | None) -> None:
        """Close the menu: `index` chosen, or nothing (None)."""
        self._chosen = index
        if self._loop is not None:
            self._loop.quit()

    def is_open(self) -> bool:
        return self._loop is not None

    # --- geometry and drawing ---------------------------------------------------------------------------------------

    def _frame_width(self) -> int:
        style = self.style()
        return style.pixelMetric(QStyle.PixelMetric.PM_MenuPanelWidth, None, self) if style is not None else 1

    def _item_option(self, i: int) -> QStyleOptionMenuItem:
        option = QStyleOptionMenuItem()
        option.initFrom(self)
        option.menuItemType = QStyleOptionMenuItem.MenuItemType.Normal
        option.checkType = QStyleOptionMenuItem.CheckType.NotCheckable
        option.text = self.items[i].text
        option.maxIconWidth = 0
        option.reservedShortcutWidth = 0
        option.font = self.font()
        option.menuRect = self.rect()
        option.state = QStyle.StateFlag.State_None
        if self.items[i].enabled:
            option.state |= QStyle.StateFlag.State_Enabled
            if i == self._current:
                option.state |= QStyle.StateFlag.State_Selected
        else:
            option.palette.setCurrentColorGroup(QPalette.ColorGroup.Disabled)  # greyed, as a real menu's
        return option

    def _item_size(self, i: int) -> QSize:
        style = self.style()
        option = self._item_option(i)
        text = self.fontMetrics().size(Qt.TextFlag.TextSingleLine, option.text)
        if style is None:
            return text
        return style.sizeFromContents(QStyle.ContentsType.CT_MenuItem, option, text, self)

    def item_rect(self, i: int) -> QRect:
        """Where item i is, in the menu."""
        frame = self._frame_width()
        width = max(self._item_size(j).width() for j in range(len(self.items)))
        top = frame + sum(self._item_size(j).height() for j in range(i))
        return QRect(frame, top, width, self._item_size(i).height())

    def sizeHint(self) -> QSize:
        frame = self._frame_width()
        sizes = [self._item_size(i) for i in range(len(self.items))]
        width = max((size.width() for size in sizes), default=0)
        return QSize(width + 2 * frame, sum(size.height() for size in sizes) + 2 * frame)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        style = self.style()
        if style is None:
            return
        painter = QPainter(self)
        panel = QStyleOption()
        panel.initFrom(self)
        panel.rect = self.rect()
        style.drawPrimitive(QStyle.PrimitiveElement.PE_PanelMenu, panel, painter, self)
        frame = QStyleOption()
        frame.initFrom(self)
        frame.rect = self.rect()
        style.drawPrimitive(QStyle.PrimitiveElement.PE_FrameMenu, frame, painter, self)
        for i in range(len(self.items)):
            option = self._item_option(i)
            option.rect = self.item_rect(i)
            style.drawControl(QStyle.ControlElement.CE_MenuItem, option, painter, self)
        painter.end()

    def item_at(self, point: QPoint) -> int | None:
        """The item at `point` (the menu's coordinates), if any."""
        return next((i for i in range(len(self.items)) if self.item_rect(i).contains(point)), None)

    def _set_current(self, i: int | None) -> None:
        if i is not None and not self.items[i].enabled:
            i = None
        if i != self._current:
            self._current = i
            self.update()

    def current(self) -> int | None:
        """The item that's highlighted (under the mouse, or reached with the keys)."""
        return self._current

    # --- input ------------------------------------------------------------------------------------------------------

    def mouseMoveEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is not None:
            self._set_current(self.item_at(a0.position().toPoint()))

    def leaveEvent(self, a0: QEvent | None) -> None:
        self._set_current(None)

    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is not None:
            self._pressed = self.item_at(a0.position().toPoint())
            a0.accept()

    def mouseReleaseEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None:
            return
        a0.accept()
        i = self.item_at(a0.position().toPoint())
        if i is not None and i == self._pressed and self.items[i].enabled:
            self.close_with(i)
        self._pressed = None

    def _key(self, event: QKeyEvent) -> None:
        enabled = [i for i, item in enumerate(self.items) if item.enabled]
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close_with(None)
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self._current is not None:
                self.close_with(self._current)
        elif key in (Qt.Key.Key_Down, Qt.Key.Key_Up) and enabled:
            if self._current not in enabled:
                self._set_current(enabled[0] if key == Qt.Key.Key_Down else enabled[-1])
            else:
                step = 1 if key == Qt.Key.Key_Down else -1
                assert self._current is not None
                self._set_current(enabled[(enabled.index(self._current) + step) % len(enabled)])

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        """While it's open: what reaches the rest of the window (see the module's docstring)."""
        watched, event = a0, a1
        if event is None or self._loop is None:
            return False
        kind = event.type()
        if kind == QEvent.Type.ShortcutOverride:
            event.accept()  # no shortcut of the window acts: the key comes as a key press, to the menu
            return True
        if kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease) and isinstance(watched, QWindow):
            if kind == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
                self._key(event)
            return True  # every key goes to the menu, from the window itself (nothing else sees it)
        if kind == QEvent.Type.WindowDeactivate and watched is self._window:
            self.close_with(None)
            return False
        if not isinstance(watched, QWidget) or watched.window() is not self._window:
            return False
        if watched is self or self.isAncestorOf(watched):
            return False  # the menu's own
        if kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
            # Elsewhere: closes the menu, and is used up. (Over the menu but sent elsewhere: a button held before the
            # menu opened keeps the mouse where it was pressed; the menu takes clicks once it's released.)
            if isinstance(event, QMouseEvent) and not self.geometry().contains(self._in_window(watched, event)):
                self.close_with(None)
            return True
        return kind in (
            QEvent.Type.MouseButtonRelease,  # (a held button's: the drag doesn't end, nothing is chosen)
            QEvent.Type.Wheel,
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
            QEvent.Type.ContextMenu,
        )

    def _in_window(self, widget: QWidget, event: QMouseEvent) -> QPoint:
        return widget.mapTo(self._window, event.position().toPoint())
