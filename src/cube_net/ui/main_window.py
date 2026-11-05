"""Main application window."""

from PyQt6.QtWidgets import QLabel, QMainWindow, QWidget

APP_TITLE = "Cube Net"


class MainWindow(QMainWindow):
    """Top-level window. For now (M0) only an empty central area and a status bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.setCentralWidget(QWidget(self))
        self.coords_label = QLabel("x: -, y: -", self)
        self.statusBar().addPermanentWidget(self.coords_label)
        self._resize_to_screen()

    def _resize_to_screen(self, fraction: float = 0.8) -> None:
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.resize(int(available.width() * fraction), int(available.height() * fraction))
