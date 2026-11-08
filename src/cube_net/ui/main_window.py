"""Main application window."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QSizePolicy, QToolBar, QWidget

from cube_net.core.bounding import min_area_rectangle
from cube_net.core.cutting import CutLine
from cube_net.core.editor import Editor
from cube_net.core.geometry import Vec, quantize
from cube_net.core.labels import PointLabels, cut_line_labels, vertex_labels
from cube_net.core.net import Net, boundary_vertex_at, default_net
from cube_net.core.project_settings import ProjectSettings
from cube_net.core.sheet import sheet_box
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.instruments.bounding_controls import BoundingControls
from cube_net.ui.session.session_recorder import SessionRecorder
from cube_net.ui.session.start import (
    STARTED_AT_LAUNCH,
    STARTED_BY_USER,
    STOPPED_BY_USER,
    WINDOW_CLOSED,
    open_session_log_folder,
    start_session_recording,
    stop_session_recording,
)
from cube_net.ui.sheet.bounding_item import BoundingItem
from cube_net.ui.sheet.cut_hover import CutHover, vertex_radius
from cube_net.ui.sheet.cut_tool import CutTool
from cube_net.ui.sheet.ruler_tool import RulerTool
from cube_net.ui.sheet.sheet_view import SheetView

APP_TITLE = "Cube Net"
NO_COORDINATES = "x: —   y: —"


def format_point(p: Vec) -> str:
    """A point in session recordings: x,y with 3 decimals (the input rounding)."""
    return f"{float(p.x):.3f},{float(p.y):.3f}"


def format_ruler_total(total: float | None) -> str:
    return "Σ —" if total is None else f"Σ {total:.3f}"


def format_coordinates(x: float, y: float) -> str:
    return f"x: {x:.3f}   y: {y:.3f}"


class MainWindow(QMainWindow):
    """Top-level window: the sheet view in the middle, mouse coordinates in the status bar."""

    def __init__(
        self,
        parent: QWidget | None = None,
        settings: AppSettings | None = None,
        session_dir: Path | None = None,
    ) -> None:
        """`session_dir`: where session recordings go (default: the app data folder)."""
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.settings = AppSettings() if settings is None else settings
        self.point_labels = PointLabels()
        self.project_settings = ProjectSettings()
        self.recorder: SessionRecorder | None = None

        self.net: Net = default_net()
        net_box = self.net.bounding_box()
        self.sheet_view = SheetView(self)
        self.sheet_view.set_sheet(sheet_box(v.position for v in self.net.vertices))
        self.sheet_view.set_net(self.net)
        self.cut_hover = CutHover(self.sheet_view, self.net)
        self.ruler_tool = RulerTool(self.sheet_view)
        self.ruler_tool.point_added.connect(self._on_ruler_point)
        self.editor = Editor(self.net)
        self.cut_tool = CutTool(self.sheet_view, self.editor, self.ruler_tool)
        self.cut_tool.point_added.connect(self._on_cut_point)
        self.cut_tool.edited.connect(self._on_cut_edited)
        self.cut_tool.line_changed.connect(self._update_vertex_labels)
        self.cut_tool.rejected.connect(self._on_cut_rejected)
        self.sheet_view.set_net_hit_test(self._is_on_net)
        self.sheet_view.show_initial_view(net_box)
        self.setCentralWidget(self.sheet_view)

        self.coords_label = QLabel(NO_COORDINATES, self)
        # Wide enough for any value, so the status bar doesn't jump while the mouse moves.
        widest = format_coordinates(-8888.888, -8888.888)
        self.coords_label.setMinimumWidth(self.coords_label.fontMetrics().horizontalAdvance(widest) + 8)
        self.statusBar().addPermanentWidget(self.coords_label)
        self.sheet_view.mouse_moved.connect(lambda x, y: self.coords_label.setText(format_coordinates(x, y)))
        self.sheet_view.mouse_left.connect(lambda: self.coords_label.setText(NO_COORDINATES))

        self._create_instruments()
        self._create_menus()
        self._update_vertex_labels()
        self._resize_to_screen()

        self._session_dir = session_dir
        if self.settings.record_session:
            self.start_recording(STARTED_AT_LAUNCH)

    # --- session recording ----------------------------------------------------------------------------------------

    def start_recording(self, reason: str) -> None:
        """Start a new session file and write the current state into it."""
        app = QApplication.instance()
        if self.recorder is not None or not isinstance(app, QApplication):
            return
        recorder = start_session_recording(app, reason, self._session_dir)
        recorder.watch_sheet(self.sheet_view)
        recorder.watch_main_window(self)
        self.recorder = recorder
        # If the window goes away before the app quits, its recording ends with it (only `app` and `recorder` are
        # captured: the window itself is already gone when this runs).
        self.destroyed.connect(lambda: _end_recording(app, recorder))
        self._record_state(recorder)
        self.statusBar().showMessage(f"Recording session to {recorder.log.path}", 15000)

    def stop_recording(self, reason: str) -> None:
        app = QApplication.instance()
        if self.recorder is None or not isinstance(app, QApplication):
            return
        stop_session_recording(app, self.recorder, reason)
        self.recorder = None
        self.statusBar().showMessage("Session recording stopped", 5000)

    def _record_state(self, recorder: SessionRecorder) -> None:
        """Everything needed to reproduce the session from this point on.

        Until projects can be saved (M9) the only possible net is the default one; then the full project state will
        be written here.
        """
        recorder.note("state", "net", "default")
        recorder.note("state", "labels", "on" if self.settings.show_vertex_labels else "off")
        recorder.note("state", "window", f"{self.width()}x{self.height()}")
        recorder.note("state", "bounds", "on" if self.bounding.action.isChecked() else "off")
        ruler_points = [format_point(p) for p in self.ruler_tool.ruler.points]
        recorder.note("state", "ruler", "on" if self.ruler_tool.active else "off", *ruler_points)
        line = self.editor.cut_line
        cut_points = [format_point(p.position) + ("p" if p.on_perimeter else "") for p in line.points] if line else []
        recorder.note("state", "cut", self.editor.state.value, *cut_points)  # "p": on the perimeter
        recorder.schedule_view_record()  # zoom and position, once the view has been laid out

    def _is_on_net(self, x: float, y: float) -> bool:
        """On the net, or inside a perimeter vertex's circle (which sticks out of the net): no panning there."""
        p = quantize(x, y)
        return (
            self.net.contains(p)
            or boundary_vertex_at(self.net, p, vertex_radius(self.sheet_view)) is not None
            or self.cut_tool.claims(x, y)
        )

    def _create_instruments(self) -> None:
        toolbar = QToolBar("Instruments", self)
        toolbar.setObjectName("instruments")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
        self.ruler_action = QAction("Ruler", self)
        self.ruler_action.setCheckable(True)
        self.ruler_action.setShortcut("R")
        self.ruler_action.setToolTip("Ruler (R): click on the sheet to measure; turn off to clear")
        self.ruler_action.toggled.connect(self._on_ruler_toggled)
        toolbar.addAction(self.ruler_action)
        self.ruler_total_label = QLabel(self)
        self.ruler_total_label.setToolTip("Total length of the placed ruler segments")
        self.ruler_total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ruler_total_action = toolbar.addWidget(self.ruler_total_label)
        self.ruler_tool.points_changed.connect(self._update_ruler_total)
        self._update_ruler_total()

        self.bounding_item = BoundingItem()
        scene = self.sheet_view.scene()
        assert scene is not None
        scene.addItem(self.bounding_item)
        self.bounding = BoundingControls(toolbar, self.bounding_item)
        self.bounding.toggled.connect(self._on_bounding_toggled)
        self._update_bounding()

        spacer = QWidget(toolbar)  # pushes what follows to the bottom of the panel
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)
        self.open_logs_action = QAction("Logs", self)
        self.open_logs_action.setToolTip("Open the folder with session logs")
        self.open_logs_action.triggered.connect(self._on_open_logs)
        toolbar.addAction(self.open_logs_action)

    def _update_bounding(self) -> None:
        """Recompute the minimum-area bounding rectangle of the current net."""
        rectangle = min_area_rectangle(v.position for v in self.net.vertices)
        self.bounding.update(rectangle, self.project_settings.area_threshold)

    def _on_open_logs(self) -> None:
        if not open_session_log_folder(self._session_dir):
            self.statusBar().showMessage("Could not open the folder with session logs", 5000)

    def _on_bounding_toggled(self, checked: bool) -> None:
        if self.recorder is not None:
            self.recorder.note("bounds", "on" if checked else "off")

    def _update_ruler_total(self) -> None:
        """Shown under the ruler button while the ruler is active: Σ of the placed segments, 3 decimals."""
        assert self.ruler_total_action is not None
        self.ruler_total_action.setVisible(self.ruler_tool.active)
        self.ruler_total_label.setText(format_ruler_total(self.ruler_tool.total_length()))

    def _on_ruler_toggled(self, checked: bool) -> None:
        self.ruler_tool.set_active(checked)
        if self.recorder is not None:
            self.recorder.note("ruler", "on" if checked else "off")

    def _on_cut_point(self, point: Vec) -> None:
        if self.recorder is not None:
            self.recorder.note("cut", self.editor.state.value, format_point(point))

    def _on_cut_edited(self, action: str, index: int, point: Vec) -> None:
        if self.recorder is not None:
            self.recorder.note("cut", action, index, format_point(point))

    def _on_cut_rejected(self, point: Vec) -> None:
        if self.recorder is not None:
            self.recorder.note("cut", "rejected", format_point(point))

    def _on_ruler_point(self, point: Vec) -> None:
        if self.recorder is not None:
            self.recorder.note("ruler", format_point(point))

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

        self.record_session_action = QAction("&Record session (development)", self)
        self.record_session_action.setCheckable(True)
        self.record_session_action.setChecked(self.settings.record_session)
        self.record_session_action.toggled.connect(self._on_record_session_toggled)
        view_menu.addAction(self.record_session_action)

    def _on_show_labels_toggled(self, checked: bool) -> None:
        self.settings.show_vertex_labels = checked
        self._update_vertex_labels()
        if self.recorder is not None:
            self.recorder.note("labels", "on" if checked else "off")

    def _on_record_session_toggled(self, checked: bool) -> None:
        self.settings.record_session = checked
        if checked:
            self.start_recording(STARTED_BY_USER)
        else:
            self.stop_recording(STOPPED_BY_USER)

    def _update_vertex_labels(self) -> None:
        """Debug labels of the net's vertices and of the cut line's new points and images (if switched on)."""
        show = self.settings.show_vertex_labels
        self.sheet_view.set_vertex_labels(vertex_labels(self.net, self.point_labels) if show else None)
        points = self.cut_tool.item.points()
        try:
            cut_labels = cut_line_labels(self.net, CutLine(list(points)), self.point_labels) if show else []
        except ValueError:  # a point is being dragged off the net: it has no cube point to name for now
            cut_labels = []
        self.cut_tool.item.set_labels(cut_labels)

    def _resize_to_screen(self, fraction: float = 0.8) -> None:
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.resize(int(available.width() * fraction), int(available.height() * fraction))


def _end_recording(app: QApplication, recorder: SessionRecorder) -> None:
    if not recorder.log.closed:
        stop_session_recording(app, recorder, WINDOW_CLOSED)
