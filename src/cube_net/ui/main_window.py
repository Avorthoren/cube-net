"""Main application window."""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QMainWindow, QWidget

from cube_net.core.geometry import quantize
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import Net, default_net
from cube_net.core.sheet import sheet_box
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.sheet.sheet_view import SheetView

APP_TITLE = "Cube Net"
NO_COORDINATES = "x: —   y: —"


def format_coordinates(x: float, y: float) -> str:
    return f"x: {x:.3f}   y: {y:.3f}"


class MainWindow(QMainWindow):
    """Top-level window: the sheet view in the middle, mouse coordinates in the status bar."""

    def __init__(self, parent: QWidget | None = None, settings: AppSettings | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.settings = AppSettings() if settings is None else settings
        self.point_labels = PointLabels()

        self.net: Net = default_net()
        net_box = self.net.bounding_box()
        self.sheet_view = SheetView(self)
        self.sheet_view.set_sheet(sheet_box(v.position for v in self.net.vertices))
        self.sheet_view.set_net(self.net)
        self.sheet_view.set_net_hit_test(lambda x, y: self.net.contains(quantize(x, y)))
        self.sheet_view.show_initial_view(net_box)
        self.setCentralWidget(self.sheet_view)

        self.coords_label = QLabel(NO_COORDINATES, self)
        # Wide enough for any value, so the status bar doesn't jump while the mouse moves.
        widest = format_coordinates(-8888.888, -8888.888)
        self.coords_label.setMinimumWidth(self.coords_label.fontMetrics().horizontalAdvance(widest) + 8)
        self.statusBar().addPermanentWidget(self.coords_label)
        self.sheet_view.mouse_moved.connect(lambda x, y: self.coords_label.setText(format_coordinates(x, y)))
        self.sheet_view.mouse_left.connect(lambda: self.coords_label.setText(NO_COORDINATES))

        self._create_menus()
        self._update_vertex_labels()
        self._resize_to_screen()

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()
        assert menu_bar is not None
        view_menu = menu_bar.addMenu("&View")
        assert view_menu is not None
        self.show_labels_action = QAction("Show vertex &labels (development)", self)
        self.show_labels_action.setCheckable(True)
        self.show_labels_action.setChecked(self.settings.show_vertex_labels)
        self.show_labels_action.toggled.connect(self._on_show_labels_toggled)
        view_menu.addAction(self.show_labels_action)

    def _on_show_labels_toggled(self, checked: bool) -> None:
        self.settings.show_vertex_labels = checked
        self._update_vertex_labels()

    def _update_vertex_labels(self) -> None:
        labels = vertex_labels(self.net, self.point_labels) if self.settings.show_vertex_labels else None
        self.sheet_view.set_vertex_labels(labels)

    def _resize_to_screen(self, fraction: float = 0.8) -> None:
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.resize(int(available.width() * fraction), int(available.height() * fraction))
