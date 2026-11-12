# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Main application window."""

import datetime
import os
from fractions import Fraction
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QCloseEvent, QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QToolBar,
    QWidget,
)

from cube_net import __version__
from cube_net.core.bounding import min_area_rectangle
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels
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
from cube_net.core.update_policy import due_today, offer_automatically
from cube_net.core.version import newer
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.desktop_integration import AppImage, DesktopEntry, data_home
from cube_net.ui.dialogs.message_window import MessageIcon, tell
from cube_net.ui.help.about_dialog import AboutDialog
from cube_net.ui.help.help_window import HelpWindow
from cube_net.ui.i18n import TRANSLATIONS, Language, bind, tr
from cube_net.ui.i18n.errors import error_text
from cube_net.ui.instruments.bounding_controls import BoundingControls
from cube_net.ui.instruments.button_look import tool_buttons_style
from cube_net.ui.instruments.logging_icons import record_icon, stop_icon
from cube_net.ui.load_failed_dialog import AfterLoadFailed, ask_after_load_failed
from cube_net.ui.menu_entry_dialog import ask_menu_entry, confirm_menu_entry_removal
from cube_net.ui.no_wheel import ignore_wheel
from cube_net.ui.save_changes_dialog import SaveChoice, ask_save_changes
from cube_net.ui.save_state_label import SaveStateLabel
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
from cube_net.ui.settings_panel.panel import SettingsPanel
from cube_net.ui.sheet.bounding_item import BoundingItem
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.sheet.workspace import Workspace
from cube_net.ui.style import Style, apply_style
from cube_net.ui.updates.appimage_update import install_appimage, start_appimage
from cube_net.ui.updates.installation import (
    Installation,
    Kind,
    ManualStepNeeded,
    current_installation,
    download_folder,
)
from cube_net.ui.updates.latest_release import LatestRelease, fetch_latest_release
from cube_net.ui.updates.macos_update import install_macos, open_in_finder
from cube_net.ui.updates.package_download import PackageDownload
from cube_net.ui.updates.update_check import UpdateCheck
from cube_net.ui.updates.update_dialogs import (
    DownloadProgress,
    UpdateChoice,
    ask_update,
    tell_appimage_downloaded,
    tell_check_failed,
    tell_macos_downloaded,
    tell_up_to_date,
    tell_update_failed,
)
from cube_net.ui.updates.windows_update import start_installer

APP_TITLE = "Cube Net"
NO_COORDINATES = "x: —   y: —"

# How long the status bar says a check for updates is under way, at most (ms).
CHECKING_MESSAGE_MS = 20000

# How long the status bar says where the project was saved (ms).
SAVED_MESSAGE_MS = 5000

# What a project is called until it's saved.
UNTITLED = "Untitled"


def format_point(p: Vec) -> str:
    """A point in session recordings: x,y with 3 decimals (the input rounding)."""
    return f"{float(p.x):.3f},{float(p.y):.3f}"


def project_files() -> str:
    """The file dialogs' filter for project files, in the current language."""
    return tr("Cube Net projects (*{suffix})", suffix=PROJECT_SUFFIX)


def format_style(style: Style) -> str:
    """The style in session recordings, in one word."""
    return (
        f"faces={'/'.join(style.face_colors)};tiling={style.hatch_columns}x{style.hatch_rows};"
        f"dashes={style.dashes_per_edge};edge={style.edge_width};radius={style.vertex_radius};"
        f"grid={style.grid_color}/{style.grid_width}"
    )


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
        appimage: AppImage | None = None,
        desktop_entry: DesktopEntry | None = None,
    ) -> None:
        """`session_dir`: where session recordings go (default: the app data folder). `appimage`: the AppImage the
        app runs from, if it does (Linux), and `desktop_entry` where its applications menu's entry goes (default: the
        user's data folder)."""
        super().__init__(parent)
        self.settings = AppSettings() if settings is None else settings
        self.appimage = appimage
        self.desktop_entry = desktop_entry if desktop_entry is not None else DesktopEntry(data_home())
        apply_style(self.settings.style)  # before anything gets drawn
        TRANSLATIONS.set_language(self.settings.language)  # before any text is set
        self.point_labels = PointLabels()
        self.project_settings = ProjectSettings()

        # The file of the project, once it has one.
        self.project_path: Path | None = None

        # The revision of the history when the project was last saved (or created, or opened).
        self._saved_revision = 0

        # The settings as they were then. They aren't part of the history: they have no undo.
        self._saved_settings = self.project_settings
        self.recorder: SessionRecorder | None = None

        # Help -> Help, once it has been opened.
        self.help_window: HelpWindow | None = None

        # The check for updates under way, or the last one; and the update's download.
        self._update_check: UpdateCheck | None = None
        self._download: PackageDownload | None = None

        # Quitting for an update: what happens to unsaved changes is decided already.
        self._leaving_decided = False

        self.net: Net = default_net()
        net_box = self.net.bounding_box()
        self.sheet_view = SheetView(self)
        self.sheet_view.set_max_zoom(self.settings.max_zoom)
        self.sheet_view.set_sheet(sheet_box(v.position for v in self.net.vertices))
        self.sheet_view.set_net(self.net)
        self.workspace = Workspace(self.sheet_view, self.net)
        self.cut_hover = self.workspace.cut_hover
        self.counterpart_blink = self.workspace.counterpart_blink
        self.ruler_tool = self.workspace.ruler_tool
        self.ruler_tool.point_added.connect(self._on_ruler_point)
        self.editor = self.workspace.editor
        self.cut_tool = self.workspace.cut_tool
        self.cut_tool.point_added.connect(self._on_cut_point)
        self.cut_tool.edited.connect(self._on_cut_edited)
        self.cut_tool.line_changed.connect(self._update_vertex_labels)
        self.workspace.net_changed.connect(self._on_net_changed)
        self.cut_tool.glued.connect(self._on_glued)
        self.cut_tool.rejected.connect(self._on_cut_rejected)
        assert self.workspace.sheet_cursor is not None
        self.sheet_cursor = self.workspace.sheet_cursor
        self.sheet_view.show_initial_view(net_box)
        self.setCentralWidget(self.sheet_view)
        self.sheet_view.setFocus()  # it wants to know about SHIFT even before the first click

        self.coords_label = QLabel(NO_COORDINATES, self)
        # Wide enough for any value, so the status bar doesn't jump while the mouse moves.
        widest = format_coordinates(-8888.888, -8888.888)
        self.coords_label.setMinimumWidth(self.coords_label.fontMetrics().horizontalAdvance(widest) + 8)
        self.statusBar().addPermanentWidget(self.coords_label)
        self.save_state = SaveStateLabel(self)
        self.statusBar().addPermanentWidget(self.save_state)
        self.sheet_view.mouse_moved.connect(lambda x, y: self.coords_label.setText(format_coordinates(x, y)))
        self.sheet_view.mouse_left.connect(lambda: self.coords_label.setText(NO_COORDINATES))

        self._create_instruments()
        self._create_menus()
        TRANSLATIONS.changed.connect(self._update_title)  # "Untitled" is in the current language
        TRANSLATIONS.changed.connect(self._on_texts_changed)
        fields = [*self.findChildren(QAbstractSpinBox), *self.findChildren(QComboBox)]
        ignore_wheel(fields, self)  # every number field and drop-down list of the window
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
        self.statusBar().showMessage(tr("Recording session to {path}", path=recorder.log.path), 15000)
        self._update_logging_action()

    def stop_recording(self, reason: str) -> None:
        app = QApplication.instance()
        if self.recorder is None or not isinstance(app, QApplication):
            return
        stop_session_recording(app, self.recorder, reason)
        self.recorder = None
        self.statusBar().showMessage(tr("Session recording stopped"), 5000)
        self._update_logging_action()

    def _record_state(self, recorder: SessionRecorder, snapshot: bool = True) -> None:
        """Everything needed to reproduce the session from this point on: the whole project in its snapshot, and what
        isn't part of a project. The rest is there to be read by a person."""
        recorder.note("state", "project", self.project_path if self.project_path is not None else "untitled")
        recorder.note("state", "threshold", format_threshold(self.project_settings.area_threshold))
        if snapshot:
            self._record_snapshot(recorder)
        self._record_net_state(recorder)
        recorder.note("state", "labels", "on" if self.settings.show_vertex_labels else "off")
        recorder.note("state", "language", self.settings.language.value)
        recorder.note("state", "blink", "on" if self.settings.blink_on_success else "off")
        recorder.note("state", "max_zoom", self.settings.max_zoom)
        recorder.note("state", "style", format_style(self.settings.style))
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
        toolbar = QToolBar(self)
        bind(toolbar, toolbar.setWindowTitle, "Instruments")
        toolbar.setObjectName("instruments")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(tool_buttons_style())  # its buttons look like buttons
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
        self.ruler_action = QAction(self)
        bind(self.ruler_action, self.ruler_action.setText, "Ruler")
        self.ruler_action.setCheckable(True)
        self.ruler_action.setShortcut("R")
        bind(
            self.ruler_action,
            self.ruler_action.setToolTip,
            "Ruler (R): click on the sheet to measure; turn off to clear",
        )
        self.ruler_action.toggled.connect(self._on_ruler_toggled)
        toolbar.addAction(self.ruler_action)
        self.ruler_total_label = QLabel(self)
        bind(self.ruler_total_label, self.ruler_total_label.setToolTip, "Total length of the placed ruler segments")
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
        self.bounding.set_target(self.project_settings.area_threshold)
        self.bounding.set_blink_enabled(self.settings.blink_on_success)
        self.bounding.target_changed.connect(self._on_target_changed)
        self._update_bounding()

        spacer = QWidget(toolbar)  # pushes what follows to the bottom of the panel
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)
        self.logging_action = QAction(self)  # just an icon: record, or stop
        self.logging_action.triggered.connect(self._on_logging_clicked)
        TRANSLATIONS.changed.connect(self._update_logging_action)
        toolbar.addAction(self.logging_action)
        self._update_logging_action()
        self.open_logs_action = QAction(self)
        bind(self.open_logs_action, self.open_logs_action.setText, "Logs")
        bind(self.open_logs_action, self.open_logs_action.setToolTip, "Open the folder with session logs")
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
        dragging = self.cut_tool.busy  # a point is being dragged, or a button of the line is pressed
        self.undo_action.setEnabled(self.editor.history.can_undo and not dragging)
        self.redo_action.setEnabled(self.editor.history.can_redo and not dragging)
        rearranged = self.editor.rearranged
        self.approve_action.setEnabled(rearranged is not None and rearranged.valid)
        for action in (
            self.new_action,
            self.open_action,
            self.save_action,
            self.save_as_action,
            self.quit_action,
        ):
            action.setEnabled(not dragging)  # they may ask something, and the mouse button is still down
        self._update_saved_state()

    def _on_open_logs(self) -> None:
        if not open_session_log_folder(self._session_dir):
            self.statusBar().showMessage(tr("Could not open the folder with session logs"), 5000)

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
        self.workspace.update_divided_view()
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
        return tr(UNTITLED) if self.project_path is None else self.project_path.name

    def _update_title(self) -> None:
        # "[*]": a "*" before the name while there are unsaved changes (on macOS a dot in the close button instead).
        self.setWindowTitle(f"[*]{self._project_name()} — {APP_TITLE}")

    def _update_saved_state(self) -> None:
        """The title's "*" and the status bar's word: whether there are unsaved changes."""
        dirty = self.is_dirty
        self.setWindowModified(dirty)
        self.save_state.set_state(dirty, self.project_path is not None)

    def _project(self) -> Project:
        return Project(self.editor.snapshot(), self.editor.history, self.project_settings, self.point_labels)

    def save_project_to(self, path: Path) -> bool:
        """Save the project to `path`; from now on that's its file. Tells the user if it fails."""
        try:
            save_project(self._project(), path)
        except ProjectFileError as e:
            tell(self, APP_TITLE, error_text(e), icon=MessageIcon.ERROR)
            return False
        self.project_path = path
        self.settings.last_project = path
        self._saved_revision = self.editor.history.revision
        self._saved_settings = self.project_settings
        self._update_title()
        self._update_saved_state()
        self.statusBar().showMessage(tr("Saved to {path}", path=path), SAVED_MESSAGE_MS)  # Ctrl+S did something
        if self.recorder is not None:
            self.recorder.note("project", "saved", path)
        return True

    def open_project_from(self, path: Path) -> bool:
        """Show the project from `path` instead of the current one. If it fails, tells the user and nothing changes."""
        try:
            self._load_and_show(path)
        except ProjectFileError as e:
            tell(self, APP_TITLE, error_text(e), icon=MessageIcon.ERROR)
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
            self._offer_another_project(error_text(e))
            if self.recorder is not None and self.project_path is None:
                self._record_snapshot(self.recorder)  # it's the new project after all

    # --- updates -------------------------------------------------------------------------------------------------

    def check_for_updates_at_start(self, today: datetime.date | None = None) -> None:
        """At start: the daily check, if it's on and today's hasn't worked yet (it runs in the background)."""
        if self.settings.check_updates and due_today(self.settings.last_update_check, today or datetime.date.today()):
            self.check_for_updates(manual=False)

    def check_for_updates(self, manual: bool) -> None:
        """Ask GitHub for the latest release, in the background; the answer comes to `_on_update_found` (or
        `_on_update_check_failed`). One check at a time."""
        if self._update_check is not None and self._update_check.running():
            return
        check = UpdateCheck(lambda: fetch_latest_release(), self)
        check.found.connect(lambda release: self._on_update_found(release, manual))
        check.failed.connect(lambda problem: self._on_update_check_failed(problem, manual))
        self._update_check = check
        if manual:
            self.statusBar().showMessage(tr("Checking for updates..."), CHECKING_MESSAGE_MS)
        check.start()

    def _on_update_found(self, release: LatestRelease | None, manual: bool) -> None:
        if self.recorder is not None:
            self.recorder.note("updates", "manual" if manual else "auto", release.version if release else "none")
        if not manual:
            self.settings.last_update_check = datetime.date.today()  # it worked: not again today
            if release is None or not offer_automatically(release.version, __version__, self.settings.skipped_update):
                return
        elif release is None or not newer(release.version, __version__):
            self.statusBar().clearMessage()
            tell_up_to_date(self, __version__)
            return
        self.statusBar().clearMessage()
        installation = current_installation()
        can_update = installation is not None and release.package() is not None
        if ask_update(self, release, __version__, can_update, automatic=not manual) is UpdateChoice.DOWNLOAD:
            if installation is not None and can_update:
                self._update_to(release, installation)
            else:
                QDesktopServices.openUrl(QUrl(release.page))  # run from the source: it can't update itself
        elif not manual:
            self.settings.skipped_update = release.version  # turned down: the daily check won't offer it again

    def _update_to(self, release: LatestRelease, installation: Installation) -> None:
        """Download this system's package of `release` (unsaved changes are asked about first: the application
        restarts at the end), check it, and have it take this installation's place."""
        package = release.package()
        if package is None or not self._confirm_leaving_project():
            return
        name, file = package
        download = PackageDownload(name, file, release.checksums(), download_folder(installation), self)
        progress = DownloadProgress(release.version, self)
        download.progress.connect(progress.show_progress)
        progress.canceled.connect(download.cancel)
        download.cancelled.connect(progress.finish)
        download.finished.connect(lambda path: (progress.finish(), self._install_update(release, installation, path)))
        download.failed.connect(lambda problem: (progress.finish(), self._update_failed(release, problem)))
        self._download = download
        if self.recorder is not None:
            self.recorder.note("updates", "download", release.version)
        download.start()
        progress.show()

    def _install_update(self, release: LatestRelease, installation: Installation, package: Path) -> None:
        """The checked package takes this installation's place, the new version starts, and this one quits (or the
        user finishes it, where the application can't)."""
        try:
            if installation.kind is Kind.WINDOWS:
                start_installer(package)
            elif installation.kind is Kind.APPIMAGE:
                start_appimage(install_appimage(package, installation.path))
            else:
                install_macos(package, installation.path, os.getpid())
        except ManualStepNeeded as step:
            if installation.kind is Kind.APPIMAGE:
                if tell_appimage_downloaded(self, release.version, step.downloaded, step.target):
                    start_appimage(step.downloaded)
                    self._quit_for_update()
            else:
                open_in_finder(step.downloaded)
                tell_macos_downloaded(self, release.version)
            return
        except OSError as error:
            self._update_failed(release, str(error))
            return
        if self.recorder is not None:
            self.recorder.note("updates", "installed", release.version)
        self._quit_for_update()

    def _quit_for_update(self) -> None:
        """Quit for the new version: unsaved changes were asked about before the download."""
        self._leaving_decided = True
        self.close()

    def _update_failed(self, release: LatestRelease, problem: str) -> None:
        if self.recorder is not None:
            self.recorder.note("updates", "failed", release.version)
        if tell_update_failed(self, problem):
            QDesktopServices.openUrl(QUrl(release.page))

    def _on_update_check_failed(self, problem: str, manual: bool) -> None:
        """Said only when the user asked; the daily check tries again at the next start (it's not done today)."""
        if self.recorder is not None:
            self.recorder.note("updates", "manual" if manual else "auto", "failed")
        if manual:
            self.statusBar().clearMessage()
            tell_check_failed(self, problem)

    def _on_check_updates_changed(self, checked: bool) -> None:
        self.settings.check_updates = checked
        if self.recorder is not None:
            self.recorder.note("settings", "check_updates", "on" if checked else "off")

    def offer_menu_entry(self) -> None:
        """At start, from an AppImage: the first time, ask whether to add Cube Net to the applications menu; once the
        user wants it, keep the entry pointing at this AppImage (it may have been moved since, or be another copy)."""
        if self.appimage is None:
            return
        wanted = self.settings.menu_entry
        if wanted is None:
            self._set_menu_entry(ask_menu_entry(self))
        elif wanted:
            try:
                if self.desktop_entry.refresh(self.appimage) and self.recorder is not None:
                    self.recorder.note("settings", "menu_entry", "moved", self.appimage.path)
            except OSError as error:
                self._menu_entry_failed(error)

    def _on_menu_entry_toggled(self, checked: bool) -> None:
        if checked == (self.settings.menu_entry is True):
            return
        if not checked and not confirm_menu_entry_removal(self):
            self._show_menu_entry_later(True)  # it stays
            return
        self._set_menu_entry(checked)

    def _show_menu_entry_later(self, shown: bool) -> None:
        """Set the switch back, once its own signal has reached everything (set back at once, the checkbox would
        still get the switch's change after it, and change it again)."""
        QTimer.singleShot(0, lambda: self.menu_entry_action and self.menu_entry_action.setChecked(shown))

    def _set_menu_entry(self, wanted: bool) -> None:
        """Install or remove the entry, and remember the choice (unless that failed: then nothing changed)."""
        assert self.appimage is not None
        try:
            if wanted:
                self.desktop_entry.install(self.appimage)
            else:
                self.desktop_entry.remove()
        except OSError as error:
            self._menu_entry_failed(error)
            self._show_menu_entry_later(self.settings.menu_entry is True)  # as it was
            return
        self.settings.menu_entry = wanted
        if self.recorder is not None:
            self.recorder.note("settings", "menu_entry", "on" if wanted else "off")
        if self.menu_entry_action is not None:
            self.menu_entry_action.setChecked(wanted)  # the checkbox follows; the setting is already what it says

    def _menu_entry_failed(self, error: OSError) -> None:
        tell(
            self,
            APP_TITLE,
            tr("Couldn't change the applications menu: {problem}", problem=error),
            icon=MessageIcon.WARNING,
        )

    def open_project_at_start(self, path: Path) -> None:
        """At start, with a project file to open (double-clicked, or given on the command line): that one instead of
        the last one. If it can't be loaded, the user decides, as when the last one can't."""
        try:
            self._load_and_show(path)
        except ProjectFileError as e:
            if self.recorder is not None:
                self.recorder.note("project", "opening failed", path)
            self._offer_another_project(error_text(e))

    def open_project_requested(self, path: Path) -> None:
        """The system asks to open a project file while the app runs (macOS sends double-clicked files that way):
        like File -> Open, unsaved changes are asked about first. The same project just comes to the front."""
        self.raise_()
        self.activateWindow()
        if self.project_path is not None and self.project_path.resolve() == path.resolve():
            return
        if self.cut_tool.busy or not self._confirm_leaving_project():
            return
        self.open_project_from(path)

    def _offer_another_project(self, message: str) -> None:
        """The project that should be here can't be loaded: the user decides. The window has a new one until then."""
        while ask_after_load_failed(self, message) is AfterLoadFailed.OPEN_ANOTHER:
            name, _ = QFileDialog.getOpenFileName(self, tr("Open project"), "", project_files())
            if not name:
                return
            try:
                self._load_and_show(Path(name))
            except ProjectFileError as e:
                message = error_text(e)
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
        self.bounding.set_target(project.settings.area_threshold)
        self.project_path = path
        self._saved_revision = project.history.revision
        self._saved_settings = project.settings
        self._update_title()
        self._update_saved_state()
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
        name, _ = QFileDialog.getOpenFileName(self, tr("Open project"), self._dialog_folder(), project_files())
        if name:
            self.open_project_from(Path(name))

    def _save(self) -> bool:
        """Save to the project's file; a project without one needs a name first. False if it wasn't saved."""
        return self._save_as() if self.project_path is None else self.save_project_to(self.project_path)

    def _save_as(self) -> bool:
        name, _ = QFileDialog.getSaveFileName(self, tr("Save project as"), self._dialog_folder(), project_files())
        if not name:
            return False
        path = Path(name)
        return self.save_project_to(path if path.suffix else path.with_suffix(PROJECT_SUFFIX))

    def _on_settings_tab_changed(self) -> None:
        self.settings.settings_tab = self.settings_panel.tab_name()

    def _on_language_changed(self, language: Language) -> None:
        self.settings.language = language
        TRANSLATIONS.set_language(language)
        if self.recorder is not None:
            self.recorder.note("settings", "language", language.value)

    def _on_blink_changed(self, blink: bool) -> None:
        self.settings.blink_on_success = blink
        self.bounding.set_blink_enabled(blink)
        if self.recorder is not None:
            self.recorder.note("settings", "blink", "on" if blink else "off")

    def _on_max_zoom_changed(self, max_zoom: int) -> None:
        self.settings.max_zoom = max_zoom
        self.sheet_view.set_max_zoom(max_zoom)
        if self.recorder is not None:
            self.recorder.note("settings", "max_zoom", max_zoom)

    def show_help(self) -> None:
        """Help -> Help: one window, brought to the front if it's open already."""
        if self.help_window is None:
            self.help_window = HelpWindow(self, self.settings.show_vertex_labels)
        self.help_window.show()
        self.help_window.raise_()
        self.help_window.activateWindow()

    def _on_style_changed(self, style: Style) -> None:
        self.settings.style = style
        apply_style(style)
        item = self.sheet_view.net_item()
        if item is not None:
            item.restyle()
        if self.help_window is not None:
            self.help_window.restyle()
        scene = self.sheet_view.scene()
        if scene is not None:
            scene.update()
        if self.recorder is not None:
            self.recorder.note("settings", "style", format_style(style))

    def _on_target_changed(self, threshold: Fraction) -> None:
        if threshold == self.project_settings.area_threshold:
            return
        self.project_settings = ProjectSettings(threshold)
        self._update_bounding()
        self._update_saved_state()
        if self.recorder is not None:
            self.recorder.note("project", "threshold", format_threshold(threshold))

    def _place_settings_panel(self) -> None:
        screen = self.screen()
        width = screen.geometry().width() if screen is not None else 1920
        self.settings_panel.place_over(self.sheet_view.geometry(), width)

    def _on_texts_changed(self) -> None:
        """Texts of another length: the settings panel takes the width it needs now (still at most its share)."""
        if not self.settings_panel.isHidden():
            self._place_settings_panel()

    def _on_settings_toggled(self, shown: bool) -> None:
        if shown:
            self._place_settings_panel()
        self.settings_panel.setVisible(shown)
        self.settings.settings_open = shown

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        """The settings panel follows the sheet view when it moves or changes its size."""
        if (
            watched is self.sheet_view
            and event is not None
            and event.type() in (QEvent.Type.Resize, QEvent.Type.Move)
            and not self.settings_panel.isHidden()  # switched on (not yet visible while the window is being shown)
        ):
            self._place_settings_panel()
        return super().eventFilter(watched, event)

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Closing the window is quitting: the project goes away."""
        if event is None:
            return
        self.cut_tool.cancel_drag()  # the question below would leave the mouse release unnoticed
        if self._leaving_decided or self._confirm_leaving_project():
            event.accept()
        else:
            event.ignore()

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()
        assert menu_bar is not None
        file_menu = menu_bar.addMenu("")
        assert file_menu is not None
        bind(file_menu, file_menu.setTitle, "&File")
        self.new_action = QAction(self)
        bind(self.new_action, self.new_action.setText, "&New")
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self._on_new)
        file_menu.addAction(self.new_action)
        self.open_action = QAction(self)
        bind(self.open_action, self.open_action.setText, "&Open...")
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self._on_open)
        file_menu.addAction(self.open_action)
        self.save_action = QAction(self)
        bind(self.save_action, self.save_action.setText, "&Save")
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(lambda: self._save())
        file_menu.addAction(self.save_action)
        self.save_as_action = QAction(self)
        bind(self.save_as_action, self.save_as_action.setText, "Save &As...")
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(lambda: self._save_as())
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        self.quit_action = QAction(self)
        bind(self.quit_action, self.quit_action.setText, "&Quit")
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.close)
        file_menu.addAction(self.quit_action)

        # The switches of the Preferences tab of the settings panel.
        self.show_labels_action = QAction(self)
        bind(self.show_labels_action, self.show_labels_action.setText, "Show vertex labels")
        self.show_labels_action.setCheckable(True)
        self.show_labels_action.setChecked(self.settings.show_vertex_labels)
        self.show_labels_action.toggled.connect(self._on_show_labels_toggled)
        self.auto_log_action = QAction(self)
        bind(self.auto_log_action, self.auto_log_action.setText, "Auto-start logging")
        self.auto_log_action.setCheckable(True)
        self.auto_log_action.setChecked(self.settings.record_session)
        self.auto_log_action.toggled.connect(self._on_auto_log_toggled)

        edit_menu = menu_bar.addMenu("")

        assert edit_menu is not None

        bind(edit_menu, edit_menu.setTitle, "&Edit")
        self.approve_action = QAction(self)
        bind(self.approve_action, self.approve_action.setText, "&Approve cut")
        self.approve_action.setShortcuts(["Ctrl+Return", "Ctrl+Enter"])  # the main Enter key and the one on the keypad
        self.approve_action.triggered.connect(self._on_approve)
        self.cut_tool.approve_clicked.connect(self.approve_action.trigger)
        edit_menu.addAction(self.approve_action)
        self.undo_action = QAction(self)
        bind(self.undo_action, self.undo_action.setText, "&Undo")
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self._on_undo)
        self.cut_tool.undo_clicked.connect(self.undo_action.trigger)
        edit_menu.addAction(self.undo_action)
        self.redo_action = QAction(self)
        bind(self.redo_action, self.redo_action.setText, "&Redo")
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(self.redo_action)

        # The applications menu's entry: only for an AppImage (the installers of the other systems make their own).
        self.menu_entry_action: QAction | None = None
        if self.appimage is not None:
            self.menu_entry_action = QAction(self)
            self.menu_entry_action.setCheckable(True)
            self.menu_entry_action.setChecked(self.settings.menu_entry is True)
            self.menu_entry_action.toggled.connect(self._on_menu_entry_toggled)
        self.settings_panel = SettingsPanel(
            self.show_labels_action,
            self.auto_log_action,
            self.settings.blink_on_success,
            self.settings.max_zoom,
            self.settings.style,
            self,
            self.settings.language,
            self.menu_entry_action,
            self.settings.check_updates,
        )
        self.settings_panel.preferences.check_updates_changed.connect(self._on_check_updates_changed)
        self.settings_panel.preferences.language_changed.connect(self._on_language_changed)
        self.settings_panel.preferences.blink_changed.connect(self._on_blink_changed)
        self.settings_panel.show_tab(self.settings.settings_tab)  # the one the user looked at last, even last time
        self.settings_panel.tabs.currentChanged.connect(self._on_settings_tab_changed)
        self.settings_panel.preferences.max_zoom_changed.connect(self._on_max_zoom_changed)
        self.settings_panel.style_tab.style_changed.connect(self._on_style_changed)
        self.sheet_view.installEventFilter(self)
        self.settings_action = QAction(self)
        bind(self.settings_action, self.settings_action.setText, "&Settings")
        self.settings_action.setCheckable(True)
        bind(self.settings_action, self.settings_action.setToolTip, "Settings of the application (not of the project)")
        self.settings_action.toggled.connect(self._on_settings_toggled)
        menu_bar.addAction(self.settings_action)
        help_menu = menu_bar.addMenu("")
        assert help_menu is not None
        bind(help_menu, help_menu.setTitle, "&Help")
        self.about_action = QAction(self)
        bind(self.about_action, self.about_action.setText, "&About")
        self.about_action.triggered.connect(lambda: AboutDialog(self).exec())
        help_menu.addAction(self.about_action)
        self.help_action = QAction(self)
        bind(self.help_action, self.help_action.setText, "&Help")
        self.help_action.setShortcut("F1")
        self.help_action.triggered.connect(self.show_help)
        help_menu.addAction(self.help_action)
        self.updates_action = QAction(self)
        bind(self.updates_action, self.updates_action.setText, "Check for &updates")
        self.updates_action.triggered.connect(lambda: self.check_for_updates(manual=True))
        help_menu.addAction(self.updates_action)
        self.settings_panel.hide_requested.connect(lambda: self.settings_action.setChecked(False))
        # Open as the user left it. It gets its place when the window is laid out (the view's first resize).
        self.settings_action.setChecked(self.settings.settings_open)
        self.cut_tool.line_changed.connect(self._update_edit_actions)
        self._update_edit_actions()

    def _on_net_changed(self) -> None:
        """The view shows the editor's new net (the rearranged one in CUT_APPROVING): the bounding rectangle and the
        labels follow it."""
        self.net = self.editor.display_net
        self._update_bounding()
        self._update_vertex_labels()

    def _on_glued(self) -> None:
        rearranged = self.editor.rearranged
        if self.recorder is not None and rearranged is not None:
            kept = rearranged.kept
            ends = format_point(kept.origin.position), format_point(kept.destination.position)
            self.recorder.note("cut", "glue", *ends, "ok" if rearranged.valid else "overlap")

    def _on_show_labels_toggled(self, checked: bool) -> None:
        self.settings.show_vertex_labels = checked
        self._update_vertex_labels()
        if self.help_window is not None:
            self.help_window.set_labels_shown(checked)
        if self.recorder is not None:
            self.recorder.note("labels", "on" if checked else "off")

    def _on_auto_log_toggled(self, checked: bool) -> None:
        """Only whether logging starts by itself next time: it doesn't start or stop it now (the button does)."""
        self.settings.record_session = checked
        if self.recorder is not None:
            self.recorder.note("settings", "auto_log", "on" if checked else "off")

    def _on_logging_clicked(self) -> None:
        if self.recorder is None:
            self.start_recording(STARTED_BY_USER)
        else:
            self.stop_recording(STOPPED_BY_USER)

    def _update_logging_action(self) -> None:
        """Record while not logging, stop while logging."""
        action = self.logging_action
        if self.recorder is None:
            action.setIcon(record_icon())
            action.setToolTip(tr("Start logging"))
        else:
            action.setIcon(stop_icon())
            action.setToolTip(tr("Stop logging"))

    def _update_vertex_labels(self) -> None:
        """Debug labels of the net's vertices and of the cut line's new points and images (if switched on)."""
        self.workspace.show_labels(self.point_labels if self.settings.show_vertex_labels else None)

    def _resize_to_screen(self, fraction: float = 0.8) -> None:
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.resize(int(available.width() * fraction), int(available.height() * fraction))


def _end_recording(app: QApplication, recorder: SessionRecorder) -> None:
    if not recorder.log.closed:
        stop_session_recording(app, recorder, WINDOW_CLOSED)
