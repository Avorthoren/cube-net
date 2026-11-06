"""Main application window."""

from PyQt6.QtWidgets import QLabel, QMainWindow, QWidget

from cube_net.core.cube import CUBE, FACES, LOCAL_CORNERS
from cube_net.core.geometry import Box, quantize
from cube_net.core.sheet import sheet_box
from cube_net.ui.sheet.sheet_view import SheetView

APP_TITLE = "Cube Net"
NO_COORDINATES = "x: —   y: —"


def _default_net_squares() -> list[Box]:
    """The 6 face squares of the default net on the sheet.

    Temporary (M2 step 2): stands in for the net model until it exists (M2 step 3).
    """
    return [Box.around(CUBE.default_placement(f).apply(c) for c in LOCAL_CORNERS) for f in FACES]


def format_coordinates(x: float, y: float) -> str:
    return f"x: {x:.3f}   y: {y:.3f}"


class MainWindow(QMainWindow):
    """Top-level window: the sheet view in the middle, mouse coordinates in the status bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)

        squares = _default_net_squares()
        net_box = Box.around(p for square in squares for p in (square.lo, square.hi))
        self.sheet_view = SheetView(self)
        self.sheet_view.set_sheet(sheet_box([net_box.lo, net_box.hi]))
        self.sheet_view.set_net_hit_test(lambda x, y: any(s.contains(quantize(x, y)) for s in squares))
        self.sheet_view.show_initial_view(net_box)
        self.setCentralWidget(self.sheet_view)

        self.coords_label = QLabel(NO_COORDINATES, self)
        # Wide enough for any value, so the status bar doesn't jump while the mouse moves.
        widest = format_coordinates(-8888.888, -8888.888)
        self.coords_label.setMinimumWidth(self.coords_label.fontMetrics().horizontalAdvance(widest) + 8)
        self.statusBar().addPermanentWidget(self.coords_label)
        self.sheet_view.mouse_moved.connect(lambda x, y: self.coords_label.setText(format_coordinates(x, y)))
        self.sheet_view.mouse_left.connect(lambda: self.coords_label.setText(NO_COORDINATES))

        self._resize_to_screen()

    def _resize_to_screen(self, fraction: float = 0.8) -> None:
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.resize(int(available.width() * fraction), int(available.height() * fraction))
