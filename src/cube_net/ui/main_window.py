"""Main application window."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox, QSizePolicy, QToolBar, QWidget

from cube_net.core.bounding import min_area_rectangle
from cube_net.core.cutting import CutLine
from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels, cut_line_labels, vertex_labels
from cube_net.core.net import Net, default_net
from cube_net.core.project import (
    PROJECT_SUFFIX,
    Project,
    ProjectFileError,
    load_project,
    new_project,
    save_project,
)
from cube_net.core.project_settings import ProjectSettings, format_threshold
from cube_net.core.sheet import sheet_box
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.instruments.bounding_controls import BoundingControls
from cube_net.ui.load_failed_dialog import AfterLoadFailed, ask_after_load_failed
from cube_net.ui.project_settings_dialog import ask_project_settings
from cube_net.ui.save_changes_dialog import SaveChoice, ask_save_changes
from cube_net.ui.session.session_recorder import SessionRecorder
from cube_net.ui.session.snapshots import snapshot_text
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
from cube_net.ui.sheet.counterpart_blink import CounterpartBlink
from cube_net.ui.sheet.cut_hover import CutHover
from cube_net.ui.sheet.cut_tool import CutTool
from cube_net.ui.sheet.ruler_tool import RulerTool
from cube_net.ui.sheet.sheet_view import SheetView

APP_TITLE = "Cube Net"
NO_COORDINATES = "x: —   y: —"
PROJECT_FILES = f"Cube Net projects (*{PROJECT_SUFFIX})"

# What a project is called until it's saved.
UNTITLED = "Untitled"


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
        self.settings = AppSettings() if settings is None else settings
        self.point_labels = PointLabels()
        self.project_settings = ProjectSettings()

        # The file of the project, once it has one.
        self.project_path: Path | None = None

        # The revision of the history when the project was last saved (or created, or opened).
        self._saved_revision = 0

        # The settings as they were then. They aren't part of the history: they have no undo.
        self._saved_settings = self.project_settings
        self.recorder: SessionRecorder | None = None

        self.net: Net = default_net()
        net_box = self.net.bounding_box()
        self.sheet_view = SheetView(self)
        self.sheet_view.set_sheet(sheet_box(v.position for v in self.net.vertices))
        self.sheet_view.set_net(self.net)
        self.cut_hover = CutHover(self.sheet_view, self.net)
        self.counterpart_blink = CounterpartBlink(self.sheet_view)
        self.ruler_tool = RulerTool(self.sheet_view)
        self.ruler_tool.point_added.connect(self._on_ruler_point)
        self.editor = Editor(self.net)
        self.cut_tool = CutTool(self.sheet_view, self.editor, self.ruler_tool)
        self.cut_tool.point_added.connect(self._on_cut_point)
        self.cut_tool.edited.connect(self._on_cut_edited)
        self.cut_tool.line_changed.connect(self._update_vertex_labels)
        self.cut_tool.line_changed.connect(self._update_hover_net)
        self.cut_tool.net_changed.connect(self._on_net_changed)
        self.cut_tool.glued.connect(self._on_glued)
        self.cut_hover.hover_changed.connect(self._update_divided_view)
        self.cut_tool.rejected.connect(self._on_cut_rejected)
        self.cut_hover.set_target(self.cut_tool.hover_target)
        self.sheet_view.set_press_claim(self.cut_tool.claims)
        self.sheet_view.show_initial_view(net_box)
        self.setCentralWidget(self.sheet_view)
        self.sheet_view.setFocus()  # it wants to know about SHIFT even before the first click

        self.coords_label = QLabel(NO_COORDINATES, self)
        # Wide enough for any value, so the status bar doesn't jump while the mouse moves.
        widest = format_coordinates(-8888.888, -8888.888)
        self.coords_label.setMinimumWidth(self.coords_label.fontMetrics().horizontalAdvance(widest) + 8)
        self.statusBar().addPermanentWidget(self.coords_label)
        self.sheet_view.mouse_moved.connect(lambda x, y: self.coords_label.setText(format_coordinates(x, y)))
        self.sheet_view.mouse_left.connect(lambda: self.coords_label.setText(NO_COORDINATES))

        self._create_instruments()
        self._create_menus()
        self._update_title()
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
        # At launch, with a project about to be reopened, the new one the window has for now isn't worth a snapshot:
        # `reopen_last_project` takes care of that.
        reopening = reason == STARTED_AT_LAUNCH and self.settings.last_project is not None
        self._record_state(recorder, snapshot=not reopening)
        self.statusBar().showMessage(f"Recording session to {recorder.log.path}", 15000)

    def stop_recording(self, reason: str) -> None:
        app = QApplication.instance()
        if self.recorder is None or not isinstance(app, QApplication):
            return
        stop_session_recording(app, self.recorder, reason)
        self.recorder = None
        self.statusBar().showMessage("Session recording stopped", 5000)

    def _record_state(self, recorder: SessionRecorder, snapshot: bool = True) -> None:
        """Everything needed to reproduce the session from this point on: the whole project in its snapshot, and what
        isn't part of a project. The rest is there to be read by a person."""
        recorder.note("state", "project", self.project_path if self.project_path is not None else "untitled")
        recorder.note("state", "threshold", format_threshold(self.project_settings.area_threshold))
        if snapshot:
            self._record_snapshot(recorder)
        self._record_net_state(recorder)
        recorder.note("state", "labels", "on" if self.settings.show_vertex_labels else "off")
        recorder.note("state", "window", f"{self.width()}x{self.height()}")
        recorder.note("state", "bounds", "on" if self.bounding.action.isChecked() else "off")
        ruler_points = [format_point(p) for p in self.ruler_tool.ruler.points]
        recorder.note("state", "ruler", "on" if self.ruler_tool.active else "off", *ruler_points)
        line = self.editor.cut_line
        cut_points = [format_point(p.position) + ("p" if p.on_perimeter else "") for p in line.points] if line else []
        recorder.note("state", "cut", self.editor.state.value, *cut_points)  # "p": on the perimeter
        history = self.editor.history
        recorder.note("state", "history", history.done_count, history.undone_count)
        if self.editor.rearranged is not None:
            kept = self.editor.rearranged.kept
            recorder.note("state", "glue", format_point(kept.origin.position), format_point(kept.destination.position))
        recorder.schedule_view_record()  # zoom and position, once the view has been laid out

    def _record_snapshot(self, recorder: SessionRecorder) -> None:
        recorder.note("state", "snapshot", snapshot_text(self._project()))

    def _record_net_state(self, recorder: SessionRecorder) -> None:
        cuts = self.editor.approved_cuts
        recorder.note("state", "net", "default" if cuts == 0 else f"after {cuts} approved cuts")

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

    def _on_approve(self) -> None:
        self.cut_tool.approve()
        if self.recorder is not None:
            self.recorder.note("cut", "approve")

    def _on_undo(self) -> None:
        self.cut_tool.undo()
        if self.recorder is not None:
            self.recorder.note("cut", "undo", self.editor.state.value)

    def _on_redo(self) -> None:
        self.cut_tool.redo()
        if self.recorder is not None:
            self.recorder.note("cut", "redo", self.editor.state.value)

    def _update_edit_actions(self) -> None:
        """Undo and redo need something to undo or redo and no point being dragged; approving needs a valid
        rearrangement."""
        dragging = self.cut_tool.dragging
        self.undo_action.setEnabled(self.editor.history.can_undo and not dragging)
        self.redo_action.setEnabled(self.editor.history.can_redo and not dragging)
        rearranged = self.editor.rearranged
        self.approve_action.setEnabled(rearranged is not None and rearranged.valid)
        for action in (
            self.new_action,
            self.open_action,
            self.save_action,
            self.save_as_action,
            self.project_settings_action,
            self.quit_action,
        ):
            action.setEnabled(not dragging)  # they may ask something, and the mouse button is still down
        self.setWindowModified(self.is_dirty)

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
        self._update_divided_view()
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

    @property
    def is_dirty(self) -> bool:
        """Are there changes that aren't saved? Undo and redo count too: the history is saved with the project."""
        return self.editor.history.revision != self._saved_revision or self.project_settings != self._saved_settings

    def _project_name(self) -> str:
        return UNTITLED if self.project_path is None else self.project_path.name

    def _update_title(self) -> None:
        self.setWindowTitle(f"{self._project_name()}[*] — {APP_TITLE}")

    def _project(self) -> Project:
        return Project(self.editor.snapshot(), self.editor.history, self.project_settings, self.point_labels)

    def save_project_to(self, path: Path) -> bool:
        """Save the project to `path`; from now on that's its file. Tells the user if it fails."""
        try:
            save_project(self._project(), path)
        except ProjectFileError as e:
            QMessageBox.critical(self, APP_TITLE, str(e))
            return False
        self.project_path = path
        self.settings.last_project = path
        self._saved_revision = self.editor.history.revision
        self._saved_settings = self.project_settings
        self._update_title()
        self.setWindowModified(False)
        if self.recorder is not None:
            self.recorder.note("project", "saved", path)
        return True

    def open_project_from(self, path: Path) -> bool:
        """Show the project from `path` instead of the current one. If it fails, tells the user and nothing changes."""
        try:
            self._load_and_show(path)
        except ProjectFileError as e:
            QMessageBox.critical(self, APP_TITLE, str(e))
            return False
        return True

    def _load_and_show(self, path: Path) -> None:
        project = load_project(path)
        self._show_project(project, path)
        self.settings.last_project = path
        if self.recorder is not None:
            self.recorder.note("project", "opened", path)
            self._record_state(self.recorder)

    def reopen_last_project(self) -> None:
        """At start: back to the project the user worked on last, if any (otherwise the window's new one stays)."""
        path = self.settings.last_project
        if path is None:
            return
        try:
            self._load_and_show(path)
        except ProjectFileError as e:
            self.settings.last_project = None  # don't ask about it at every start from now on
            if self.recorder is not None:
                self.recorder.note("project", "reopening failed", path)
            self._offer_another_project(str(e))
            if self.recorder is not None and self.project_path is None:
                self._record_snapshot(self.recorder)  # it's the new project after all

    def _offer_another_project(self, message: str) -> None:
        """The project that should be here can't be loaded: the user decides. The window has a new one until then."""
        while ask_after_load_failed(self, message) is AfterLoadFailed.OPEN_ANOTHER:
            name, _ = QFileDialog.getOpenFileName(self, "Open project", "", PROJECT_FILES)
            if not name:
                return
            try:
                self._load_and_show(Path(name))
            except ProjectFileError as e:
                message = str(e)
            else:
                return

    def start_new_project(self) -> None:
        """Show a new project instead of the current one."""
        self._show_project(new_project(), None)
        if self.recorder is not None:
            self.recorder.note("project", "new")
            self._record_state(self.recorder)

    def _show_project(self, project: Project, path: Path | None) -> None:
        self.editor.load(project.state, project.history)
        self.point_labels = project.labels
        self.project_settings = project.settings
        self.project_path = path
        self._saved_revision = project.history.revision
        self._saved_settings = project.settings
        self._update_title()
        self.cut_tool.reload()
        self.sheet_view.show_initial_view(self.net.bounding_box())

    def _confirm_leaving_project(self) -> bool:
        """The current project is about to go away: can it? If it has unsaved changes, that's up to the user."""
        if not self.is_dirty:
            return True
        choice = ask_save_changes(self, self._project_name())
        if self.recorder is not None:
            self.recorder.note("project", "unsaved changes", choice.value)
        if choice is SaveChoice.SAVE:
            return self._save()
        return choice is SaveChoice.DISCARD

    def _dialog_folder(self) -> str:
        return "" if self.project_path is None else str(self.project_path.parent)

    def _on_new(self) -> None:
        if self._confirm_leaving_project():
            self.start_new_project()

    def _on_open(self) -> None:
        if not self._confirm_leaving_project():
            return
        name, _ = QFileDialog.getOpenFileName(self, "Open project", self._dialog_folder(), PROJECT_FILES)
        if name:
            self.open_project_from(Path(name))

    def _save(self) -> bool:
        """Save to the project's file; a project without one needs a name first. False if it wasn't saved."""
        return self._save_as() if self.project_path is None else self.save_project_to(self.project_path)

    def _save_as(self) -> bool:
        name, _ = QFileDialog.getSaveFileName(self, "Save project as", self._dialog_folder(), PROJECT_FILES)
        if not name:
            return False
        path = Path(name)
        return self.save_project_to(path if path.suffix else path.with_suffix(PROJECT_SUFFIX))

    def _on_project_settings(self) -> None:
        settings = ask_project_settings(self, self.project_settings)
        if settings is None or settings == self.project_settings:
            return
        self.project_settings = settings
        self._update_bounding()
        self.setWindowModified(self.is_dirty)
        if self.recorder is not None:
            self.recorder.note("project", "threshold", format_threshold(settings.area_threshold))

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Closing the window is quitting: the project goes away."""
        if event is None:
            return
        self.cut_tool.cancel_drag()  # the question below would leave the mouse release unnoticed
        if self._confirm_leaving_project():
            event.accept()
        else:
            event.ignore()

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()
        assert menu_bar is not None
        file_menu = menu_bar.addMenu("&File")
        assert file_menu is not None
        self.new_action = QAction("&New", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self._on_new)
        file_menu.addAction(self.new_action)
        self.open_action = QAction("&Open...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self._on_open)
        file_menu.addAction(self.open_action)
        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(lambda: self._save())
        file_menu.addAction(self.save_action)
        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(lambda: self._save_as())
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        self.project_settings_action = QAction("Project se&ttings...", self)
        self.project_settings_action.triggered.connect(self._on_project_settings)
        file_menu.addAction(self.project_settings_action)
        file_menu.addSeparator()
        self.quit_action = QAction("&Quit", self)
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.close)
        file_menu.addAction(self.quit_action)

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

        edit_menu = menu_bar.addMenu("&Edit")
        assert edit_menu is not None
        self.approve_action = QAction("&Approve cut", self)
        self.approve_action.setShortcuts(["Ctrl+Return", "Ctrl+Enter"])  # the main Enter key and the one on the keypad
        self.approve_action.triggered.connect(self._on_approve)
        self.cut_tool.approve_clicked.connect(self.approve_action.trigger)
        edit_menu.addAction(self.approve_action)
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self._on_undo)
        self.cut_tool.undo_clicked.connect(self.undo_action.trigger)
        edit_menu.addAction(self.undo_action)
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(self.redo_action)
        self.cut_tool.line_changed.connect(self._update_edit_actions)
        self._update_edit_actions()

    def _on_net_changed(self) -> None:
        """Show the net the editor has now (the rearranged one in CUT_APPROVING): the sheet, the bounding rectangle
        and the labels follow it, and what's on screen stays where it was."""
        self.net = self.editor.display_net
        self.sheet_view.set_sheet(sheet_box(v.position for v in self.net.vertices))
        self.sheet_view.set_net(self.net)
        rearranged = self.editor.rearranged
        item = self.sheet_view.net_item()
        assert item is not None
        item.set_glue((rearranged.kept, rearranged.moved) if rearranged is not None else ())
        item.set_overlapping(rearranged.overlapping if rearranged is not None else frozenset())
        self._update_bounding()
        self._update_hover_net()
        self._update_vertex_labels()

    def _on_glued(self) -> None:
        rearranged = self.editor.rearranged
        if self.recorder is not None and rearranged is not None:
            kept = rearranged.kept
            ends = format_point(kept.origin.position), format_point(kept.destination.position)
            self.recorder.note("cut", "glue", *ends, "ok" if rearranged.valid else "overlap")

    def _update_divided_view(self) -> None:
        """While the user hovers a perimeter edge in CUT_EDITING (ruler off, nothing being dragged), show which parts
        of the cuts can't be chosen for gluing; if the hovered one can be, its counterpart blinks."""
        item = self.sheet_view.net_item()
        if item is None:
            return
        show = (
            self.editor.state is EditorState.CUT_EDITING
            and not self.ruler_tool.active
            and not self.cut_tool.dragging
            and self.cut_hover.hovered() is not None
        )
        split = self.editor.split() if show else None
        item.set_divided(split)
        hovered = self.cut_hover.hovered()
        if split is None or hovered is None or hovered in split.same_half_cuts:
            self.counterpart_blink.set_cut(None)
        else:
            self.counterpart_blink.set_cut(split.net.counterpart(hovered))

    def _update_hover_net(self) -> None:
        """Which cuts follow the mouse: in CUT_EDITING the parts of the net as divided by the line, because that's what
        a click chooses (the line itself means nothing there); in CUT_APPROVING none, as only the button can be
        clicked."""
        if self.editor.state is EditorState.CUT_EDITING:
            if not self.cut_tool.dragging:
                split = self.editor.split()
                self.cut_hover.set_net(split.net, split.line_edges, vertices=False)
        elif self.editor.state is EditorState.CUT_APPROVING:
            self.cut_hover.set_net(self.net, frozenset(self.net.boundary_edges()), vertices=False)
        else:
            self.cut_hover.set_net(self.net)
        self._update_divided_view()

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
        shown = self.editor.display_net
        self.sheet_view.set_vertex_labels(vertex_labels(shown, self.point_labels) if show else None)
        points = self.cut_tool.item.points()
        try:
            cut_labels = cut_line_labels(self.editor.net, CutLine(list(points)), self.point_labels) if show else []
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
