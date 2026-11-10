"""`SmallWindow`: what the Help menu's small windows have in common: their own title bar, with just the title and a
close button.

The window manager's title bar can't be used: Ubuntu's GNOME on X11 draws minimize and maximize buttons on every window
(by the desktop's button layout), even when the window says it can't be minimized or maximized; they just do nothing.
So these windows have no frame from the window manager. The title bar here moves the window when dragged, like a real
one (the window manager does the moving), and Escape closes the window.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QMouseEvent
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QStyle, QToolButton, QVBoxLayout, QWidget

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
