# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`SmallWindow`: what the application's small windows have in common (its questions, messages, About, the update's):
their own title bar, with just the title and a close button.

The window manager's title bar can't be used: Ubuntu's GNOME on X11 draws minimize and maximize buttons on every window
(by the desktop's button layout), even when the window says it can't be minimized or maximized; they just do nothing.
So these windows have no frame from the window manager. The title bar here moves the window when dragged, like a real
one (the window manager does the moving), and Escape closes the window.

A window may start with no button selected (`select_no_button`: Enter and Space do nothing until Tab goes to one),
and one that mustn't be closed by the user has no close button and ignores Escape (`make_unclosable`).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QIcon, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cube_net.ui.i18n import bind


class TitleBar(QWidget):
    """The title and the close button; dragging it moves the window."""

    def __init__(self, title: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.title = QLabel(title, self)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.title.font()
        font.setBold(True)
        self.title.setFont(font)
        self.close_button = QToolButton(self)
        style = self.style()
        assert style is not None
        fallback = style.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)
        self.close_button.setIcon(QIcon.fromTheme("window-close-symbolic", QIcon.fromTheme("window-close", fallback)))
        bind(self.close_button, self.close_button.setToolTip, "Close")
        self.close_button.setAutoRaise(True)
        self.close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Tab goes through the window's own buttons
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.addSpacing(self.close_button.sizeHint().width())  # so that the title is in the middle
        layout.addWidget(self.title, 1)
        layout.addWidget(self.close_button)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        window = self.window()
        handle = window.windowHandle() if window is not None else None
        if event is not None and event.button() == Qt.MouseButton.LeftButton and handle is not None:
            handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)


class SmallWindow(QDialog):
    """A small window with its own title bar; what it shows goes into `body`."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(title)
        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)  # a border, since there's no frame around it
        self.title_bar = TitleBar(title, frame)
        self.title_bar.close_button.clicked.connect(self.reject)
        line = QFrame(frame)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.body = QVBoxLayout()
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)
        inner.addWidget(self.title_bar)
        inner.addWidget(line)
        inner.addLayout(self.body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)
        self._no_button_selected = False
        self._closable = True

    def select_no_button(self) -> None:
        """Start with no button selected: Enter and Space do nothing until Tab goes to a button."""
        self._no_button_selected = True
        for button in self.findChildren(QPushButton):
            button.setDefault(False)
        self.setFocus()  # the window itself, so that it doesn't go to the first button when the window is activated

    def make_unclosable(self) -> None:
        """No close button, and Escape does nothing: the window closes itself (`close`, `accept`, `done`...)."""
        self._closable = False
        button = self.title_bar.close_button
        policy = button.sizePolicy()
        policy.setRetainSizeWhenHidden(True)  # the title stays in the middle
        button.setSizePolicy(policy)
        button.hide()

    def setVisible(self, visible: bool) -> None:
        super().setVisible(visible)
        if visible and self._no_button_selected:
            # Shown, QDialog makes the first button the default one when there's none: undone.
            for button in self.findChildren(QPushButton):
                if not button.hasFocus():
                    button.setDefault(False)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is not None and event.key() == Qt.Key.Key_Escape and not self._closable:
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent | None) -> None:
        # The system's ways of closing a window (Alt+F4) don't close an unclosable one either.
        if event is not None and event.spontaneous() and not self._closable:
            event.ignore()
            return
        super().closeEvent(event)
