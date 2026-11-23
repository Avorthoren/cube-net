# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Main application window."""

import datetime
import os
import time
from collections.abc import Sequence
from dataclasses import replace
from enum import Enum
from fractions import Fraction
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QPointF, QRect, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence, QShowEvent
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QSizePolicy,
    QStackedWidget,
    QToolBar,
    QWidget,
)

from cube_net import __version__
from cube_net.core.body import CUBE, Body
from cube_net.core.bounding import min_area_rectangle
from cube_net.core.cutting import TooLong, slope_of
from cube_net.core.editor import EditorSnapshot
from cube_net.core.geometry import Box, Vec
from cube_net.core.history import ActionKind, HistoryEntry
from cube_net.core.labels import PointLabels
from cube_net.core.net import Net, default_net
from cube_net.core.origin import Origin
from cube_net.core.project import (
    PROJECT_SUFFIX,
    TEMPLATE_SUFFIX,
    Project,
    ProjectFileError,
    TemplateDocument,
    load_document,
    restorable,
    restore_document,
    save_project,
)
from cube_net.core.project.from_template import project_from_template
from cube_net.core.project.repair import RepairError, long_vertices, needs_repair, repair_project, vertex_names
from cube_net.core.project.template_repair import (
    needs_template_repair,
    repair_template,
    template_long_vertices,
    template_vertex_names,
)
from cube_net.core.project_settings import ProjectSettings, format_threshold
from cube_net.core.sheet import sheet_box
from cube_net.core.template import template_centroid
from cube_net.core.update_policy import due_today, offer_automatically
from cube_net.core.version import newer
from cube_net.ui import check_on_right_style, palette
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.crash.crash_report import CrashSection, write_error_report
from cube_net.ui.desktop_integration import AppImage, DesktopEntry, data_home
from cube_net.ui.dialogs.message_window import MessageIcon, ask_yes_no, tell
from cube_net.ui.dialogs.new_project_window import NewProjectChoice, Start, builtin_project, choose_new_project
from cube_net.ui.empty_area import EmptyArea
from cube_net.ui.help.about_dialog import AboutDialog
from cube_net.ui.help.help_tab import HelpTab
from cube_net.ui.help.help_window import HelpWindow
from cube_net.ui.i18n import TRANSLATIONS, Language, bind, tr
from cube_net.ui.i18n.errors import error_text
from cube_net.ui.instruments.bounding_controls import BoundingControls
from cube_net.ui.instruments.button_look import tool_buttons_style
from cube_net.ui.instruments.logging_icons import record_icon, stop_icon
from cube_net.ui.key_release_shortcut import KeyReleaseShortcut
from cube_net.ui.load_failed_dialog import AfterLoadFailed, ask_after_load_failed
from cube_net.ui.menu_entry_dialog import ask_menu_entry, confirm_menu_entry_removal
from cube_net.ui.no_wheel import ignore_wheel
from cube_net.ui.origin_moved_message import tell_origin_moved
from cube_net.ui.path_label import PathLabel
from cube_net.ui.repair_messages import (
    repair_failed_text,
    repaired_text,
    template_repair_failed_text,
    template_too_long_question,
    too_long_question,
)
from cube_net.ui.save_changes_dialog import SaveChoice, ask_save_changes
from cube_net.ui.save_state_label import SaveStateLabel
from cube_net.ui.session.recent_lines import RecentLines
from cube_net.ui.session.session_log import SessionLog
from cube_net.ui.session.session_recorder import SessionRecorder
from cube_net.ui.session.snapshots import snapshot_text
from cube_net.ui.session.start import (
    CRASHED,
    STARTED_AT_LAUNCH,
    STARTED_BY_USER,
    STOPPED_BY_USER,
    WINDOW_CLOSED,
    open_session_log_folder,
    session_log_directory,
    start_recent_input,
    start_session_recording,
    stop_session_recording,
)
from cube_net.ui.settings_panel.panel import SettingsPanel
from cube_net.ui.sheet.bounding_item import BoundingItem
from cube_net.ui.sheet.coordinates_text import copied_text
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.sheet.view_place import LastView
from cube_net.ui.sheet.workspace import Workspace
from cube_net.ui.style import DEFAULT_STYLE, Style, apply_style
from cube_net.ui.template.create_network_button import CreateNetworkButton
from cube_net.ui.template.draw_hole_button import DrawHoleButton
from cube_net.ui.template.net_area import NetArea
from cube_net.ui.template.template_mode import TemplateMode
from cube_net.ui.template.validate_button import ValidateButton
from cube_net.ui.template.validation_messages import shown_name
from cube_net.ui.too_long_message import project_too_long_text
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


class Restoring(Enum):
    """How offering to restore a file that can't be opened went (`MainWindow._offer_restoring`)."""

    # Nothing to restore it from (no actions to undo, or it can't be read at all).
    NOT_OFFERED = "not offered"

    # The user said no.
    DECLINED = "declined"

    # No state of its history opens.
    FAILED = "failed"

    RESTORED = "restored"


def restored_text(actions: int) -> str:
    """What restoring says it did: "State 1 action ago was restored.", "State 5 actions ago was restored."."""
    if actions == 1:
        return tr("State {n} action ago was restored.", n=actions)
    return tr("State {n} actions ago was restored.", n=actions)


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


def template_files() -> str:
    """The file dialogs' filter for template files, in the current language."""
    return tr("Cube Net templates (*{suffix})", suffix=TEMPLATE_SUFFIX)


def any_files() -> str:
    """Open's filter: projects and templates (and each kind on its own)."""
    both = tr(
        "Cube Net projects and templates (*{project} *{template})", project=PROJECT_SUFFIX, template=TEMPLATE_SUFFIX
    )
    return ";;".join((both, project_files(), template_files()))


def format_style(style: Style) -> str:
    """The style in session recordings, in one word."""
    return (
        f"tiling={style.hatch_columns}x{style.hatch_rows};"
        f"dashes={style.dashes_per_unit};edge={style.edge_width};radius={style.vertex_radius};"
        f"grid={style.grid_color}/{style.grid_width}"
    )


def format_ruler_total(total: float | None) -> str:
    return "Σ —" if total is None else f"Σ {total:.3f}"


def format_coordinates(x: float, y: float) -> str:
    return f"x: {x:.3f}   y: {y:.3f}"


class OpeningCancelled(Exception):
    """A file wasn't opened, and the user has been told why (a repair turned down, or failed)."""


# How long the status bar says where the session is recorded (ms).
RECORDING_MESSAGE_MS = 15000


class MainWindow(QMainWindow):
    """Top-level window: the sheet view in the middle, mouse coordinates in the status bar."""

    def __init__(
        self,
        parent: QWidget | None = None,
        settings: AppSettings | None = None,
        session_dir: Path | None = None,
        appimage: AppImage | None = None,
        desktop_entry: DesktopEntry | None = None,
        empty: bool = False,
    ) -> None:
        """`session_dir`: where session recordings go (default: the app data folder). `appimage`: the AppImage the
        app runs from, if it does (Linux), and `desktop_entry` where its applications menu's entry goes (default: the
        user's data folder). `empty`: start with nothing open (as the application does, until it reopens the last
        project or one is started), not with a new project of the cube."""
        super().__init__(parent)
        self.settings = AppSettings() if settings is None else settings
        self.appimage = appimage
        self.desktop_entry = desktop_entry if desktop_entry is not None else DesktopEntry(data_home())
        TRANSLATIONS.set_language(self.settings.language)  # before any text is set
        self.point_labels = PointLabels(CUBE)
        self.project_settings = self._filled_in(ProjectSettings(style=DEFAULT_STYLE), CUBE)
        apply_style(self._project_style())  # before anything gets drawn
        palette.set_face_colors(self._face_colors())

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
        # A template is made on its own sheet: the window shows one view or the other (`in_template_mode`).
        self.template_mode = TemplateMode(self, self._note)
        self.template_mode.write_error_report = self.write_error_report
        self.template_mode.view.set_max_zoom(self.settings.max_zoom)
        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.sheet_view)
        self.stack.addWidget(self.template_mode.view)
        # Nothing open: no sheet, just the grey around it (`nothing_open`).
        self.empty_area = EmptyArea(self)
        self.stack.addWidget(self.empty_area)
        self.setCentralWidget(self.stack)
        self.sheet_view.setFocus()  # it wants to know about SHIFT even before the first click

        self.coords_label = QLabel(NO_COORDINATES, self)
        # Wide enough for any value, so the status bar doesn't jump while the mouse moves.
        widest = format_coordinates(-8888.888, -8888.888)
        self.coords_label.setMinimumWidth(self.coords_label.fontMetrics().horizontalAdvance(widest) + 8)
        self.statusBar().addPermanentWidget(self.coords_label)
        self.save_state = SaveStateLabel(self)
        self.statusBar().addPermanentWidget(self.save_state)
        # The file being edited, on the left (taking what room the rest leaves).
        # A message shown before the window was, and when it ends (`time.monotonic`): see `_show_message`.
        self._message_before_shown: tuple[str, float] | None = None
        self.path_label = PathLabel(self)
        self.statusBar().addWidget(self.path_label, 1)
        # Where the mouse is over the sheet (sheet coordinates; None: it's elsewhere), for the footer.
        self._mouse: tuple[float, float] | None = None
        for view in (self.sheet_view, self.template_mode.view):
            view.mouse_moved.connect(self._on_mouse_moved)
            view.mouse_left.connect(self._on_mouse_left)
        self.cut_tool.origin_changed.connect(self._on_origin_changed)
        assert self.workspace.context_menu is not None
        self.workspace.context_menu.point_name = lambda p: self.workspace.point_name(p, self.point_labels)
        # A locked slope (right click -> Set slope): said in the status bar (a widget of it, so that its passing
        # messages don't wipe it out), and Escape unlocks it.
        self.slope_label = QLabel(self)
        self.slope_label.hide()
        self.statusBar().addWidget(self.slope_label)
        self.unlock_slope_action = QAction(self)
        self.unlock_slope_action.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        self.unlock_slope_action.setEnabled(False)  # Escape means nothing else then
        self.unlock_slope_action.triggered.connect(self._on_escape)
        self.addAction(self.unlock_slope_action)
        self.cut_tool.slope_changed.connect(self._on_slope_changed)
        # An action refused because a point it would make has a number too long: the names of the net's vertices tell
        # which point.
        self.cut_tool.describe_too_long = self._too_long_text
        self.cut_tool.too_long.connect(lambda text: tell(self, "Cube Net", text, icon=MessageIcon.WARNING))
        template_tool = self.template_mode.tool
        template_tool.slope_changed.connect(self._on_slope_changed)
        template_tool.origin_changed.connect(self._on_origin_changed)
        template_tool.line_changed.connect(self._update_edit_actions)
        self.template_mode.changed.connect(self._on_template_changed)
        self.template_mode.save_wanted.connect(self._save)

        self._create_instruments()
        self._create_menus()
        TRANSLATIONS.changed.connect(self._update_title)  # "Untitled" is in the current language
        TRANSLATIONS.changed.connect(self._on_texts_changed)
        fields = [*self.findChildren(QAbstractSpinBox), *self.findChildren(QComboBox)]
        ignore_wheel(fields, self)  # every number field and drop-down list of the window
        self._update_title()
        self._update_vertex_labels()
        geometry = self.settings.window_geometry
        if geometry is None or not self.restoreGeometry(geometry):  # as it was when the app was closed last
            self._resize_to_screen()

        self._session_dir = session_dir
        # The latest input, kept in memory all the time: for a crash report (`ui/crash`).
        self.recent_input: SessionRecorder | None = None
        app = QApplication.instance()
        if isinstance(app, QApplication):
            self.recent_input = start_recent_input(app, self)
            self.recent_input.watch_sheet(self.sheet_view)
            self.recent_input.watch_main_window(self)
        if empty:
            self.show_nothing()
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
        # The application starts with nothing open (no snapshot then): the project reopened, or the one started in
        # File -> New's window, gets one.
        self._record_state(recorder)
        self._show_message(tr("Recording session to {path}", path=recorder.log.path), RECORDING_MESSAGE_MS)
        self._update_logging_action()

    def _show_message(self, text: str, ms: int) -> None:
        """A message in the status bar for `ms` milliseconds, over the file's path. Before the window is shown, the
        status bar can't hide the path (it hides only what's visible), so it's shown again once the window is."""
        self.statusBar().showMessage(text, ms)
        if not self.isVisible():
            self._message_before_shown = (text, time.monotonic() + ms / 1000)

    def showEvent(self, event: QShowEvent | None) -> None:
        super().showEvent(event)
        if self._message_before_shown is None:
            return
        text, end = self._message_before_shown
        self._message_before_shown = None
        left = round((end - time.monotonic()) * 1000)
        status_bar = self.statusBar()
        if status_bar is not None and left > 0 and status_bar.currentMessage() == text:
            status_bar.clearMessage()  # (the same message again would change nothing)
            status_bar.showMessage(text, left)  # now it hides the path

    def stop_recording(self, reason: str) -> None:
        app = QApplication.instance()
        if self.recorder is None or not isinstance(app, QApplication):
            return
        stop_session_recording(app, self.recorder, reason)
        self.recorder = None
        self.statusBar().showMessage(tr("Session recording stopped"), 5000)
        self._update_logging_action()

    def _too_long_text(self, found: TooLong) -> str:
        return project_too_long_text(found, self.editor.net, self.point_labels, self.editor.origin)

    # --- crash reports --------------------------------------------------------------------------------------------

    def crash_sections(self) -> list[CrashSection]:
        """What a crash report has of the application (`ui/crash`): its state now, as a recording starts with it (the
        project's snapshot included), the latest input, and the session log, if it's being recorded."""
        sections = [CrashSection("State", self._crash_state)]
        recent = self.recent_input
        if recent is not None and isinstance(recent.log, RecentLines):
            lines = recent.log
            sections.append(CrashSection("Recent input", lambda: "\n".join(lines.lines())))
        recorder = self.recorder
        if recorder is not None and isinstance(recorder.log, SessionLog):
            path = recorder.log.path
            sections.append(CrashSection("Session log", lambda: f"{path}\n\n{path.read_text(encoding='utf-8')}"))
        return sections

    def _crash_state(self) -> str:
        lines = RecentLines(size=10_000)
        recorder = SessionRecorder(lines)  # not watching the input: only what `_record_state` says goes into it
        recorder.watch_sheet(self.sheet_view)
        self._record_state(recorder)
        recorder.record_view()
        return "\n".join(lines.lines())

    def write_error_report(self, sections: Sequence[CrashSection]) -> Path:
        """An action was refused by a safety net (a bug): an error report with the application's state, then
        `sections`, then the latest input and the session log, in the session logs' folder. Returns its path."""
        own = self.crash_sections()
        directory = self._session_dir if self._session_dir is not None else session_log_directory()
        return write_error_report(directory, [*own[:1], *sections, *own[1:]])

    def end_recording_after_crash(self) -> None:
        """The application is about to close after a crash: the session file says so in its last line."""
        self.stop_recording(CRASHED)

    def _record_state(self, recorder: SessionRecorder, snapshot: bool = True) -> None:
        """Everything needed to reproduce the session from this point on: the whole project in its snapshot, and what
        isn't part of a project. The rest is there to be read by a person."""
        if self.nothing_open:
            recorder.note("state", "nothing open")
            recorder.note("state", "coordinates", "on" if self.settings.show_vertex_coordinates else "off")
            recorder.note("state", "language", self.settings.language.value)
            recorder.note("state", "max_zoom", self.settings.max_zoom)
            recorder.note("state", "window", f"{self.width()}x{self.height()}")
            return
        if self.in_template_mode:
            self._record_template_state(recorder, snapshot)
            return
        recorder.note("state", "project", self.project_path if self.project_path is not None else "untitled")
        recorder.note("state", "threshold", format_threshold(self.project_settings.area_threshold))
        if snapshot:
            self._record_snapshot(recorder)
        self._record_net_state(recorder)
        recorder.note("state", "labels", "on" if self.settings.show_vertex_labels else "off")
        recorder.note("state", "coordinates", "on" if self.settings.show_vertex_coordinates else "off")
        recorder.note("state", "language", self.settings.language.value)
        recorder.note("state", "blink", "on" if self.settings.blink_on_success else "off")
        recorder.note("state", "max_zoom", self.settings.max_zoom)
        recorder.note("state", "style", format_style(self._project_style()))
        recorder.note("state", "face_colors", "/".join(self._face_colors()))
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

    def _record_template_state(self, recorder: SessionRecorder, snapshot: bool) -> None:
        """What's needed to reproduce a session of making a template from here on (its snapshot), and the rest."""
        path = self.template_mode.path
        recorder.note("state", "template", path if path is not None else "untitled")
        if snapshot:
            self._record_snapshot(recorder)
        editor = self.template_mode.editor
        recorder.note("state", "looping", editor.state.value, len(editor.template.vertices))
        recorder.note("state", "coordinates", "on" if self.settings.show_vertex_coordinates else "off")
        recorder.note("state", "language", self.settings.language.value)
        recorder.note("state", "max_zoom", self.settings.max_zoom)
        recorder.note("state", "style", format_style(self.template_mode.style))
        recorder.note("state", "validation", self.template_mode.status().value)
        recorder.note("state", "window", f"{self.width()}x{self.height()}")
        recorder.note("state", "history", editor.history.done_count, editor.history.undone_count)

    def _record_snapshot(self, recorder: SessionRecorder) -> None:
        document = self.template_mode.document() if self.in_template_mode else self._project()
        recorder.note("state", "snapshot", snapshot_text(document))

    def _record_net_state(self, recorder: SessionRecorder) -> None:
        cuts = self.editor.approved_cuts
        recorder.note("state", "net", "default" if cuts == 0 else f"after {cuts} approved cuts")

    def _create_instruments(self) -> None:
        self.instruments = toolbar = QToolBar(self)
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
        # The rectangle's corners have the coordinates hint too, while it's shown (an empty list while it isn't).
        self.cut_tool.hint_points = self.bounding_item.corners
        self._update_bounding()
        self.net_area = NetArea(toolbar)  # in their place while a template is made
        self.net_area.action.setVisible(False)
        self.draw_hole_button = DrawHoleButton(toolbar)  # below it
        self.draw_hole_button.set_visible(False)
        self.draw_hole_button.clicked.connect(self._on_draw_hole)
        self.validate_button = ValidateButton(toolbar, with_separator=False)  # below that
        self.validate_button.set_visible(False)
        self.validate_button.clicked.connect(self._on_validate)
        self.create_network_button = CreateNetworkButton(toolbar)  # below that
        self.create_network_button.set_visible(False)
        self.create_network_button.clicked.connect(self._on_create_network)
        self.center_separator = toolbar.addSeparator()  # Center: below Bounds in a project, below Create network here
        self.center_action = QAction(self)
        bind(self.center_action, self.center_action.setText, "Center")
        bind(
            self.center_action,
            self.center_action.setToolTip,
            "Put the net's center of mass in the middle of the view, zoomed out as far as allowed",
        )
        self.center_action.triggered.connect(self._on_center)
        toolbar.addAction(self.center_action)

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
        self.sheet_cursor.update()  # the hint, over one of its corners

    def _on_approve(self) -> None:
        self.cut_tool.approve()
        if self.recorder is not None:
            self.recorder.note("cut", "approve")

    @property
    def nothing_open(self) -> bool:
        """Is no project or template open (the grey area instead of a sheet)?"""
        return self.stack.currentWidget() is self.empty_area

    def show_nothing(self) -> None:
        """No project or template: the grey area instead of the sheet, and nothing that works on one (the
        instruments, Save, Undo, Settings -> Style...). Opening or starting one ends it."""
        self.ruler_action.setChecked(False)
        self.cut_tool.unlock_slope()
        self.template_mode.tool.cancel()
        self.stack.setCurrentWidget(self.empty_area)
        self.project_path = None
        for action in (self.ruler_action, self.net_area.action, self.validate_action, self.draw_hole_action):
            action.setVisible(False)
        self.ruler_total_action.setVisible(False)
        self.validate_button.set_visible(False)
        self.draw_hole_button.set_visible(False)
        self.create_network_button.set_visible(False)
        self.center_separator.setVisible(False)
        self.center_action.setVisible(False)
        self.bounding.set_shown(False)
        self.approve_action.setVisible(True)
        self.settings_panel.style_tab.setEnabled(False)
        self._mouse = None
        self._show_mouse_coordinates()
        self._update_title()
        self._update_edit_actions()

    @property
    def in_template_mode(self) -> bool:
        """Is a template shown (made), not a project?"""
        return self.stack.currentWidget() is self.template_mode.view

    def _set_template_mode(self, template: bool) -> None:
        """Show the template's view and what goes with it, or the project's."""
        if template:
            self.ruler_action.setChecked(False)  # the ruler is the project view's
            self.cut_tool.unlock_slope()
        else:
            self.template_mode.tool.cancel()
        self.stack.setCurrentWidget(self.template_mode.view if template else self.sheet_view)
        (self.template_mode.view if template else self.sheet_view).setFocus()
        self.settings_panel.style_tab.setEnabled(True)
        self.ruler_action.setVisible(not template)
        self.bounding.set_shown(not template)
        self.net_area.action.setVisible(template)
        self.validate_action.setVisible(template)
        self.validate_button.set_visible(template)
        self.draw_hole_action.setVisible(template)
        self.draw_hole_button.set_visible(template)
        self.create_network_button.set_visible(template)
        self.center_separator.setVisible(True)
        self.center_action.setVisible(True)
        self.approve_action.setVisible(not template)
        self.settings_panel.set_template_mode(template)
        self._mouse = None
        self._show_mouse_coordinates()
        self._update_net_area()
        self._update_edit_actions()

    def _note(self, *fields: object) -> None:
        """A line in the session log, if one is being recorded."""
        if self.recorder is not None:
            self.recorder.note(*fields)

    def _on_template_changed(self) -> None:
        self._update_net_area()
        self.validate_button.set_status(self.template_mode.status())
        self._update_title()
        self._update_edit_actions()

    def _update_net_area(self) -> None:
        self.net_area.set_area(self.template_mode.area())

    def _on_escape(self) -> None:
        """Escape: a template drops a fold line being drawn or a drag, and unlocks a locked slope; a project unlocks a
        locked slope."""
        if self.in_template_mode:
            self.template_mode.tool.cancel()
        else:
            self.cut_tool.unlock_slope()

    def _on_draw_hole(self) -> None:
        """Draw hole (H): the next clicks draw a hole in the template (docs/template_plan.md, §8.5)."""
        if self.in_template_mode and self.template_mode.tool.can_start_hole():
            self.template_mode.tool.start_hole()
            self._note("template", "draw hole")
            self._update_edit_actions()

    def _on_validate(self) -> None:
        if self.in_template_mode:
            self.template_mode.validate()

    def _on_create_network(self) -> None:
        """Create network: a new project from the template as it is in the window, as File -> New -> Custom template
        makes one from its file. Unsaved changes are asked about first, but the project is made from them whatever
        the answer (Don't save: they're gone with the template, but the project has them); Cancel: nothing happens."""
        if not self.in_template_mode or not self.template_mode.can_create_network():
            return
        document = self.template_mode.document()
        path = self.template_mode.path
        if not self._confirm_leaving_project():
            return
        start = Start.CUSTOM.value if path is None else f"{Start.CUSTOM.value} {path}"
        self.start_new_project(project_from_template(document), start)

    def _on_center(self) -> None:
        """Center: the centre of mass of what's shown (the net, or the template's net once its loop is closed: its
        closed holes taken away) in the middle of the view, zoomed out as far as the zoom rules let that net be."""
        if self.in_template_mode:
            template = self.template_mode.editor.template
            center = template_centroid(template)
            box = Box.around(v.position for v in template.vertices) if template.vertices else None
            view = self.template_mode.view
        else:
            net = self.editor.display_net  # the rearranged one, while it's being approved
            center, box, view = net.centroid(), net.bounding_box(), self.sheet_view
        if center is None or box is None:
            return
        view.center_on(QPointF(float(center.x), float(center.y)), box, self._seen_part(view))
        self._note("view", "center", format_point(center))

    def _seen_part(self, view: SheetView) -> QRect:
        """The part of the view's viewport the user sees (its pixels): what the settings panel, lying over its right
        side while it's open, leaves of it."""
        viewport = view.viewport()
        assert viewport is not None
        seen = viewport.rect()
        if self.settings_panel.isVisible():
            panel = QRect(viewport.mapFrom(self, self.settings_panel.geometry().topLeft()), self.settings_panel.size())
            if panel.intersects(seen):
                seen.setRight(min(seen.right(), panel.left() - 1))
        return seen

    def _on_undo(self) -> None:
        if self.in_template_mode:
            self.template_mode.tool.undo()
            self._note("template", "undo")
            return
        entry = self.editor.history.next_undo()
        revision = self.editor.history.revision
        self.cut_tool.undo()
        if self.recorder is not None:
            self.recorder.note("cut", "undo", self.editor.state.value)
        if entry is not None and self.editor.history.revision != revision:
            self._tell_if_origin_moved(entry)

    def _on_redo(self) -> None:
        if self.in_template_mode:
            self.template_mode.tool.redo()
            self._note("template", "redo")
            return
        entry = self.editor.history.next_redo()
        revision = self.editor.history.revision
        self.cut_tool.redo()
        if self.recorder is not None:
            self.recorder.note("cut", "redo", self.editor.state.value)
        if entry is not None and self.editor.history.revision != revision:
            self._tell_if_origin_moved(entry)

    def _tell_if_origin_moved(self, entry: HistoryEntry[EditorSnapshot]) -> None:
        """`entry` was just undone or redone: if it moved the origin, say what coordinates its point has now."""
        moved = entry.after.origin
        if entry.kind is ActionKind.MOVE_ORIGIN and moved.point is not None:
            tell_origin_moved(self, moved.name, self.editor.origin.shown(moved.point))

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self._mouse = x, y
        self._show_mouse_coordinates()

    def _on_mouse_left(self) -> None:
        self._mouse = None
        self._show_mouse_coordinates()

    def _show_mouse_coordinates(self) -> None:
        """The footer: the mouse's coordinates, from the moved origin if it was moved."""
        if self._mouse is None:
            self.coords_label.setText(NO_COORDINATES)
            return
        at = self._origin().position
        self.coords_label.setText(format_coordinates(self._mouse[0] - float(at.x), self._mouse[1] - float(at.y)))

    def _origin(self) -> Origin:
        return self.template_mode.editor.origin if self.in_template_mode else self.editor.origin

    def _on_origin_changed(self) -> None:
        self._show_mouse_coordinates()
        self._update_edit_actions()  # an action: undo, and the project has changes
        if self.recorder is not None:
            self.recorder.note("origin", format_point(self._origin().position))

    def _update_edit_actions(self) -> None:
        """Undo and redo need something to undo or redo and no point being dragged; approving needs a valid
        rearrangement."""
        if self.nothing_open:
            for action in (
                self.approve_action,
                self.validate_action,
                self.draw_hole_action,
                self.unlock_slope_action,
                self.undo_action,
                self.redo_action,
                self.save_action,
                self.save_as_action,
                self.center_action,
            ):
                action.setEnabled(False)
            for action in (self.new_action, self.new_template_action, self.open_action, self.quit_action):
                action.setEnabled(True)
            self._update_saved_state()
            return
        if self.in_template_mode:
            tool = self.template_mode.tool
            dragging = tool.busy()
            history = self.template_mode.editor.history
            self.approve_action.setEnabled(False)
            self.validate_action.setEnabled(self.template_mode.can_validate())
            self.draw_hole_action.setEnabled(tool.can_start_hole())
            self.draw_hole_button.set_enabled(tool.can_start_hole())
            self.validate_button.set_enabled(self.template_mode.can_validate())
            self.create_network_button.set_enabled(self.template_mode.can_create_network())
            self.unlock_slope_action.setEnabled(True)  # Escape always means something while making a template
            self.center_action.setEnabled(template_centroid(self.template_mode.editor.template) is not None)
        else:
            dragging = self.cut_tool.busy  # a point is being dragged, or a button of the line is pressed
            history = self.editor.history
            rearranged = self.editor.rearranged
            self.approve_action.setEnabled(rearranged is not None and rearranged.valid)
            self.validate_action.setEnabled(False)
            self.draw_hole_action.setEnabled(False)
            self.unlock_slope_action.setEnabled(self.cut_tool.slope is not None)
            self.center_action.setEnabled(True)
        self.undo_action.setEnabled(history.can_undo and not dragging)
        self.redo_action.setEnabled(history.can_redo and not dragging)
        for action in (
            self.new_action,
            self.new_template_action,
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
        self.sheet_cursor.update()  # the hint, over one of its corners
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
        """Are there changes that aren't saved? Undo and redo count too: the history is saved with the project (or the
        template)."""
        if self.nothing_open:
            return False
        if self.in_template_mode:
            return self.template_mode.is_dirty
        return self.editor.history.revision != self._saved_revision or self.project_settings != self._saved_settings

    def _document_path(self) -> Path | None:
        """The file of what's shown: the project's or the template's (None: none, or nothing is open)."""
        if self.nothing_open:
            return None
        return self.template_mode.path if self.in_template_mode else self.project_path

    def _project_name(self) -> str:
        path = self._document_path()
        return tr(UNTITLED) if path is None else path.name

    def _update_title(self) -> None:
        # "[*]": a "*" before the name while there are unsaved changes (on macOS a dot in the close button instead).
        self.setWindowTitle(APP_TITLE if self.nothing_open else f"[*]{self._project_name()} — {APP_TITLE}")
        self.path_label.set_path(self._document_path())

    def _update_saved_state(self) -> None:
        """The title's "*" and the status bar's word: whether there are unsaved changes."""
        dirty = self.is_dirty
        self.setWindowModified(dirty)
        self.save_state.set_state(dirty, self._document_path() is not None)

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

    def save_template_to(self, path: Path) -> bool:
        """Save the template to `path`; from now on that's its file. Tells the user if it fails."""
        try:
            self.template_mode.save_to(path)
        except ProjectFileError as e:
            tell(self, APP_TITLE, error_text(e), icon=MessageIcon.ERROR)
            return False
        self.settings.last_project = path
        self._update_title()
        self._update_saved_state()
        self.statusBar().showMessage(tr("Saved to {path}", path=path), SAVED_MESSAGE_MS)
        self._note("template", "saved", path)
        return True

    def open_project_from(self, path: Path) -> bool:
        """Show the project (or the template) from `path` instead of what's shown. If it fails, tells the user and
        nothing changes."""
        try:
            self._load_and_show(path)
        except OpeningCancelled:
            return False
        except ProjectFileError as e:
            outcome = self._offer_restoring(path, e)
            if outcome is Restoring.RESTORED:
                return True
            if outcome is Restoring.NOT_OFFERED:
                tell(self, APP_TITLE, error_text(e), icon=MessageIcon.ERROR)
            elif outcome is Restoring.FAILED and ask_yes_no(self, tr("Unable to restore the file. Open another?")):
                self._on_open()
            return False
        return True

    def _offer_restoring(self, path: Path, error: ProjectFileError) -> Restoring:
        """The file can't be opened: if it has actions to undo, asks whether to try to restore its last state that
        opens (`restore_document`). Restored, it's shown with unsaved changes (it isn't saved by itself), and the user
        is told how many actions ago that state was."""
        if not restorable(path):
            return Restoring.NOT_OFFERED
        if not ask_yes_no(self, f"{error_text(error)}\n\n{tr('Try to restore the last valid state?')}"):
            return Restoring.DECLINED
        restored = restore_document(path)
        self._note("file", "restore", path, "failed" if restored is None else f"{restored[1]} actions ago")
        if restored is None:
            return Restoring.FAILED
        document, actions = restored
        if isinstance(document, TemplateDocument):
            self._show_template(document, path)
            self.template_mode.mark_unsaved()
        else:
            self._show_project(document, path)
            self._saved_revision = -1  # restored: not what the file holds
        self.settings.last_project = path
        self._update_saved_state()
        if self.recorder is not None:
            self._record_state(self.recorder)
        tell(self, APP_TITLE, restored_text(actions))
        return Restoring.RESTORED

    def _load_and_show(self, path: Path) -> None:
        """Show the project (or the template) from `path`. Raises `ProjectFileError` if it can't be loaded, and
        `OpeningCancelled` if the user turned down repairing it, or the repair failed (they've been told)."""
        document = load_document(path)
        if isinstance(document, TemplateDocument) and needs_template_repair(document):
            self._show_template(self._repaired_template(document, path), path)
            self.template_mode.mark_unsaved()  # repaired: not what the file holds
        elif isinstance(document, TemplateDocument):
            self._show_template(document, path)
        elif needs_repair(document):
            self._show_project(self._repaired(document, path), path)
            self._saved_revision = -1  # repaired: not what the file holds
        else:
            self._show_project(document, path)
        self.settings.last_project = path
        if self.recorder is not None:
            self.recorder.note("template" if isinstance(document, TemplateDocument) else "project", "opened", path)
            self._record_state(self.recorder)

    def _repaired(self, project: Project, path: Path) -> Project:
        """A project with numbers too long (`MAX_NUMBER_DIGITS`): repaired, if the user wants it (`repair_project`).
        Raises `OpeningCancelled` if not, or if the repair fails."""
        net = project.state.net
        names = [shown_name(name) for name in vertex_names(net, project.labels, long_vertices(project))]
        if not ask_yes_no(self, too_long_question(names)):
            self._note("project", "repair declined", path)
            raise OpeningCancelled
        try:
            repaired = repair_project(project)
        except RepairError as e:
            self._note("project", "repair failed", path, str(e)[:200])
            tell(self, APP_TITLE, repair_failed_text(), icon=MessageIcon.ERROR)
            raise OpeningCancelled from e
        self._note("project", "repaired", path)
        tell(self, APP_TITLE, repaired_text(names))
        return repaired

    def _repaired_template(self, document: TemplateDocument, path: Path) -> TemplateDocument:
        """A template with numbers too long: repaired, if the user wants it (`repair_template`). Raises
        `OpeningCancelled` if not, or if the repair fails."""
        names = [shown_name(name) for name in template_vertex_names(template_long_vertices(document))]
        if not ask_yes_no(self, template_too_long_question(names)):
            self._note("template", "repair declined", path)
            raise OpeningCancelled
        try:
            repaired = repair_template(document)
        except RepairError as e:
            self._note("template", "repair failed", path, str(e)[:200])
            tell(self, APP_TITLE, template_repair_failed_text(), icon=MessageIcon.ERROR)
            raise OpeningCancelled from e
        self._note("template", "repaired", path)
        tell(self, APP_TITLE, repaired_text(names))
        return repaired

    def reopen_last_project(self) -> None:
        """At start: back to the project the user worked on last, if any (otherwise the window's new one stays)."""
        path = self.settings.last_project
        if path is None:
            self.ask_for_new_project()  # the first start (or the last one couldn't be reopened then)
            return
        try:
            self._load_and_show(path)
        except OpeningCancelled:
            self.ask_for_new_project()  # nothing open: as at the first start
            return
        except ProjectFileError as e:
            self._reopening_failed(path, e)
            return
        last = self.settings.last_view
        if last is not None and last.path == path:  # (another file is shown as it always is)
            (self.template_mode.view if self.in_template_mode else self.sheet_view).show_place(last.place)

    def _reopening_failed(self, path: Path, e: ProjectFileError) -> None:
        """The last project couldn't be reopened: restoring it is offered, or another one."""
        outcome = self._offer_restoring(path, e)
        if outcome is Restoring.RESTORED:
            return
        self.settings.last_project = None  # don't ask about it at every start from now on
        if self.recorder is not None:
            self.recorder.note("project", "reopening failed", path)
        failed = outcome is Restoring.FAILED
        self._offer_another_project(tr("Unable to restore the file.") if failed else error_text(e))

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
        except OpeningCancelled:
            self.ask_for_new_project()  # nothing open: as at the first start
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
        """The project that should be here can't be loaded: the user decides (a new one, from File -> New's window, or
        another file). Nothing is open until then, and stays so if the user gives up."""
        self.show_nothing()
        while ask_after_load_failed(self, message) is AfterLoadFailed.OPEN_ANOTHER:
            name, _ = QFileDialog.getOpenFileName(self, tr("Open project"), "", any_files())
            if not name:
                return
            try:
                self._load_and_show(Path(name))
            except OpeningCancelled:
                message = tr("Unable to open the file.")
            except ProjectFileError as e:
                message = error_text(e)
            else:
                return
        self.ask_for_new_project()

    def start_new_project(self, project: Project | None = None, start: str = Start.CUBE.value) -> None:
        """Show a new project (None: the cube's, File -> New's Cube) instead of the current one."""
        self._show_project(builtin_project(Start.CUBE) if project is None else project, None)
        if self.recorder is not None:
            self.recorder.note("project", "new", start)
            self._record_state(self.recorder)

    def start_new_template(self) -> None:
        """Show a new, empty template instead of what's shown (File -> New Template)."""
        self._show_template(None, None)
        self._note("template", "new")
        if self.recorder is not None:
            self._record_state(self.recorder)

    def _show_template(self, document: TemplateDocument | None, path: Path | None) -> None:
        self._set_template_mode(True)
        # A new template starts with the style files' style; one saved before the style belonged to documents gets
        # what Settings -> Style was then. Filled in, it isn't a change.
        style = DEFAULT_STYLE if document is None else document.style or self.settings.legacy_style or DEFAULT_STYLE
        self.template_mode.show(document, path, style)
        self._show_style(style)
        self._update_title()
        self._update_saved_state()

    def _show_project(self, project: Project, path: Path | None) -> None:
        self._set_template_mode(False)
        self.editor.load(project.state, project.history)
        self.point_labels = project.labels
        # Colours filled in aren't a change: the project looks as it did (or as a new one should).
        settings = self._filled_in(project.settings, project.state.net.body)
        self.project_settings = settings
        self._show_face_colors()
        self._show_style(self._project_style())
        self.bounding.set_target(settings.area_threshold)
        self.project_path = path
        self._saved_revision = project.history.revision
        self._saved_settings = settings
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
        path = self._document_path()
        return "" if path is None else str(path.parent)

    def _on_new(self) -> None:
        """File -> New: the user chooses what the project starts from (or a template that isn't valid, to open)."""
        open_template = self.template_mode.path if self.in_template_mode else None
        choice = choose_new_project(self, template_files(), self._dialog_folder(), open_template)
        if choice is not None and self._confirm_leaving_project():
            self._start_chosen(choice)

    def ask_for_new_project(self) -> None:
        """File -> New's window with nothing open (at the first start, or when the last project couldn't be reopened);
        given up, nothing is open."""
        self.show_nothing()
        choice = choose_new_project(self, template_files(), "")
        if choice is not None:
            self._start_chosen(choice)
        elif self.recorder is not None:
            self.recorder.note("project", "new", "cancelled")

    def _start_chosen(self, choice: NewProjectChoice) -> None:
        if choice.template is not None:
            assert choice.path is not None
            self._show_template(choice.template, choice.path)
            self.settings.last_project = choice.path
            self._note("template", "opened", choice.path, "not valid")
            if self.recorder is not None:
                self._record_state(self.recorder)
            return
        start = choice.start.value if choice.path is None else f"{choice.start.value} {choice.path}"
        self.start_new_project(choice.project, start)

    def _on_new_template(self) -> None:
        if self._confirm_leaving_project():
            self.start_new_template()

    def _on_open(self) -> None:
        if not self._confirm_leaving_project():
            return
        name, _ = QFileDialog.getOpenFileName(self, tr("Open project"), self._dialog_folder(), any_files())
        if name:
            self.open_project_from(Path(name))

    def _save(self) -> bool:
        """Save to the file of what's shown; without one, it needs a name first. False if it wasn't saved."""
        path = self._document_path()
        if path is None:
            return self._save_as()
        return self.save_template_to(path) if self.in_template_mode else self.save_project_to(path)

    def _save_as(self) -> bool:
        if self.in_template_mode:
            title, files, suffix = tr("Save template as"), template_files(), TEMPLATE_SUFFIX
        else:
            title, files, suffix = tr("Save project as"), project_files(), PROJECT_SUFFIX
        name, _ = QFileDialog.getSaveFileName(self, title, self._dialog_folder(), files)
        if not name:
            return False
        path = Path(name)
        path = path if path.suffix else path.with_suffix(suffix)
        return self.save_template_to(path) if self.in_template_mode else self.save_project_to(path)

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
        self.template_mode.view.set_max_zoom(max_zoom)
        if self.recorder is not None:
            self.recorder.note("settings", "max_zoom", max_zoom)

    def show_help_at_first_start(self) -> None:
        """At start: Help -> Help opens by itself the first time (the first start ever, or the first one after an
        update from a version that didn't do it), and never again."""
        if self.settings.help_shown:
            return
        self.settings.help_shown = True
        self.show_help()
        if self.recorder is not None:
            self.recorder.note("help", "first start")

    def show_help(self) -> None:
        """Help -> Help: one window, brought to the front if it's open already; opened again, it has its default size
        (the user may have resized it before, and has no other way back to that size)."""
        if self.help_window is None:
            self.help_window = HelpWindow(self, HelpTab.named(self.settings.help_tab))  # the one looked at last
            self.help_window.language_changed.connect(self._on_language_changed)
            self.help_window.tab_changed.connect(self._on_help_tab_changed)
        elif not self.help_window.isVisible():
            self.help_window.restore_default_size()
        self.help_window.show()
        self.help_window.raise_()
        self.help_window.activateWindow()

    def _on_help_tab_changed(self, tab: HelpTab) -> None:
        self.settings.help_tab = tab.value

    def _filled_in(self, settings: ProjectSettings, body: Body) -> ProjectSettings:
        """`settings` with face colours and a style, where it has none (saved by an older version): the face colours
        of the cube from Settings -> Style of an older version, if there are any, or else the body's own; the style
        from Settings -> Style of an older version, if there is one, or else the style files' one."""
        if settings.face_colors is None:
            legacy = self.settings.legacy_face_colors if body is CUBE else None
            settings = replace(settings, face_colors=legacy if legacy is not None else body.colors)
        if settings.style is None:
            settings = replace(settings, style=self.settings.legacy_style or DEFAULT_STYLE)
        return settings

    def _project_style(self) -> Style:
        style = self.project_settings.style
        assert style is not None  # `_filled_in` filled it in
        return style

    def _face_colors(self) -> tuple[str, ...]:
        colors = self.project_settings.face_colors
        assert colors is not None  # `_filled_in` filled them in
        return colors

    def _show_face_colors(self) -> None:
        """Put the project's face colours in place: on the sheet and in Settings -> Style."""
        palette.set_face_colors(self._face_colors(), self.editor.net.body)
        self.settings_panel.style_tab.set_face_colors(self._face_colors(), self.editor.net.body.colors)
        self._repaint_net()

    def _on_face_colors_changed(self, colors: tuple[str, ...]) -> None:
        self.project_settings = replace(self.project_settings, face_colors=colors)
        palette.set_face_colors(colors, self.editor.net.body)
        self._repaint_net()
        self._update_saved_state()
        if self.recorder is not None:
            self.recorder.note("project", "face_colors", "/".join(colors))

    def _show_style(self, style: Style) -> None:
        """Put the open document's style in place: on the sheet and in Settings -> Style."""
        apply_style(style)
        self.settings_panel.style_tab.set_style(style)
        self._repaint_net()

    def _on_style_changed(self, style: Style) -> None:
        """Settings -> Style changed: it's the open document's (a change to save, like its face colours)."""
        if self.in_template_mode:
            self.template_mode.set_style(style)
        else:
            self.project_settings = replace(self.project_settings, style=style)
        apply_style(style)
        self._repaint_net()
        self._update_saved_state()
        self._note("template" if self.in_template_mode else "project", "style", format_style(style))

    def _repaint_net(self) -> None:
        """Paint the net again, in the colours and sizes in place now (Help's animations keep their own look)."""
        item = self.sheet_view.net_item()
        if item is not None:
            item.restyle()
        self.template_mode.tool.restyle()
        scene = self.sheet_view.scene()
        if scene is not None:
            scene.update()

    def _on_target_changed(self, threshold: Fraction) -> None:
        if threshold == self.project_settings.area_threshold:
            return
        self.project_settings = replace(self.project_settings, area_threshold=threshold)
        self._update_bounding()
        self._update_saved_state()
        if self.recorder is not None:
            self.recorder.note("project", "threshold", format_threshold(threshold))

    def _place_settings_panel(self) -> None:
        screen = self.screen()
        width = screen.geometry().width() if screen is not None else 1920
        self.settings_panel.place_over(self.stack.geometry(), width)  # the sheet's area, whichever view is shown

    def _on_texts_changed(self) -> None:
        """Texts of another length: the settings panel takes the width it needs now (still at most its share)."""
        if not self.settings_panel.isHidden():
            self._place_settings_panel()

    def _on_instruments_toggled(self, shown: bool) -> None:
        self.instruments.setVisible(shown)
        self.settings.instruments_shown = shown

    def createPopupMenu(self) -> QMenu | None:
        """No menu on a right click over the instrument panel (Qt's default one would let it be hidden there): View
        shows and hides it."""
        return None

    def _on_settings_toggled(self, shown: bool) -> None:
        if shown:
            self._place_settings_panel()
        self.settings_panel.setVisible(shown)
        self.settings.settings_open = shown

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        """The settings panel follows the sheet's area when it moves or changes its size."""
        if (
            watched is self.stack
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
            self._remember_view()
            self.settings.window_geometry = self.saveGeometry()  # its size, place and whether it's maximized
            event.accept()
        else:
            event.ignore()

    def _remember_view(self) -> None:
        """Where the view is, for the next start (`reopen_last_project`): kept with the file shown (none: nothing)."""
        path = None if self.nothing_open else self._document_path()
        view = self.template_mode.view if self.in_template_mode else self.sheet_view
        self.settings.last_view = None if path is None else LastView(path, view.place())

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
        self.new_template_action = QAction(self)
        bind(self.new_template_action, self.new_template_action.setText, "New &Template")
        self.new_template_action.setShortcut("Ctrl+T")
        self.new_template_action.triggered.connect(self._on_new_template)
        file_menu.addAction(self.new_template_action)
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
        # L switches them, when it's released (with the settings panel open or not).
        self.labels_key = KeyReleaseShortcut(Qt.Key.Key_L, self)
        self.labels_key.activated.connect(self.show_labels_action.toggle)
        # The coordinates hint: its switch, C (when it's released, as L), and Ctrl+C, which copies what it shows (or
        # the area's hint, while that's shown).
        self.show_coordinates_action = QAction(self)
        bind(self.show_coordinates_action, self.show_coordinates_action.setText, "Show vertex coordinates")
        self.show_coordinates_action.setCheckable(True)
        self.show_coordinates_action.setChecked(self.settings.show_vertex_coordinates)
        self.show_coordinates_action.toggled.connect(self._on_show_coordinates_toggled)
        self.coordinates_key = KeyReleaseShortcut(Qt.Key.Key_C, self)
        self.coordinates_key.activated.connect(self.show_coordinates_action.toggle)
        self.copy_coordinates_action = QAction(self)
        self.copy_coordinates_action.setShortcut(QKeySequence.StandardKey.Copy)  # a text field with the focus wins
        self.copy_coordinates_action.triggered.connect(self.copy_coordinates)
        self.addAction(self.copy_coordinates_action)
        self.sheet_cursor.set_coordinates_shown(self.settings.show_vertex_coordinates)
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
        self.validate_action = QAction(self)
        bind(self.validate_action, self.validate_action.setText, "&Validate")
        self.validate_action.setShortcut("V")
        self.validate_action.triggered.connect(self._on_validate)
        self.validate_action.setVisible(False)  # only while a template is made
        edit_menu.addAction(self.validate_action)
        self.draw_hole_action = QAction(self)
        bind(self.draw_hole_action, self.draw_hole_action.setText, "Draw &hole")
        self.draw_hole_action.setShortcut("H")
        self.draw_hole_action.triggered.connect(self._on_draw_hole)
        self.draw_hole_action.setVisible(False)  # only while a template is made
        edit_menu.addAction(self.draw_hole_action)

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
            self._project_style(),
            self,
            self.settings.language,
            self.menu_entry_action,
            self.settings.check_updates,
            coordinates=self.show_coordinates_action,
        )
        self.settings_panel.preferences.check_updates_changed.connect(self._on_check_updates_changed)
        self.settings_panel.preferences.language_changed.connect(self._on_language_changed)
        self.settings_panel.preferences.blink_changed.connect(self._on_blink_changed)
        self.settings_panel.show_tab(self.settings.settings_tab)  # the one the user looked at last, even last time
        self.settings_panel.tabs.currentChanged.connect(self._on_settings_tab_changed)
        self.settings_panel.preferences.max_zoom_changed.connect(self._on_max_zoom_changed)
        self.settings_panel.style_tab.style_changed.connect(self._on_style_changed)
        self.settings_panel.style_tab.set_face_colors(self._face_colors(), CUBE.colors)
        self.settings_panel.style_tab.face_colors_changed.connect(self._on_face_colors_changed)
        self.stack.installEventFilter(self)
        self.settings_action = QAction(self)
        bind(self.settings_action, self.settings_action.setText, "&Settings")
        self.settings_action.setCheckable(True)
        bind(
            self.settings_action,
            self.settings_action.setToolTip,
            "Settings: Style is the open project's or template's, the rest the application's",
        )
        self.settings_action.toggled.connect(self._on_settings_toggled)
        # View: which panels are shown. Each item's check box only shows that; a click on the item switches it.
        view_menu = menu_bar.addMenu("")
        assert view_menu is not None
        bind(view_menu, view_menu.setTitle, "&View")
        check_on_right_style.use_on(view_menu)
        self.instruments_action = QAction(self)
        bind(self.instruments_action, self.instruments_action.setText, "&Instruments")
        self.instruments_action.setCheckable(True)
        self.instruments_action.setChecked(self.settings.instruments_shown)  # as the user left it
        self.instruments.setVisible(self.settings.instruments_shown)
        # R and B work with the panel hidden too (a hidden widget's actions don't take their shortcuts).
        self.addActions([self.ruler_action, self.bounding.action])
        self.instruments_action.toggled.connect(self._on_instruments_toggled)
        view_menu.addAction(self.instruments_action)
        view_menu.addAction(self.settings_action)
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
        self.template_mode.cursor.set_coordinates_shown(self.settings.show_vertex_coordinates)
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

    def _on_show_coordinates_toggled(self, checked: bool) -> None:
        self.settings.show_vertex_coordinates = checked
        self.sheet_cursor.set_coordinates_shown(checked)
        self.template_mode.cursor.set_coordinates_shown(checked)
        if self.recorder is not None:
            self.recorder.note("coordinates", "on" if checked else "off")

    def _on_slope_changed(self, direction: Vec | None) -> None:
        self.unlock_slope_action.setEnabled(direction is not None or self.in_template_mode)
        if direction is None:
            self.slope_label.hide()
        else:
            y, x = slope_of(direction)
            self.slope_label.setText(
                tr("Slope locked: y {y}, x {x} (until the point is placed; Escape unlocks)", y=y, x=x)
            )
            self.slope_label.show()
        if self.recorder is not None:
            self.recorder.note("slope", *(("off",) if direction is None else (str(c) for c in slope_of(direction))))

    def copy_coordinates(self) -> None:
        """Ctrl+C: the area's hint while it's shown; otherwise the coordinates hint's two lines; with every number in
        full (nothing if neither is shown)."""
        cursor = self.template_mode.cursor if self.in_template_mode else self.sheet_cursor
        point = cursor.coordinates()
        clipboard = QApplication.clipboard()
        if self.in_template_mode and self.net_area.hint_shown() and clipboard is not None:
            clipboard.setText(self.net_area.copied_hint())
            self._note("area", "copied")
        elif self.bounding.hint_shown() and clipboard is not None:
            clipboard.setText(self.bounding.copied_hint())
            if self.recorder is not None:
                self.recorder.note("area", "copied")
        elif point is not None and clipboard is not None:
            clipboard.setText(copied_text(point))
            if self.recorder is not None:
                self.recorder.note("coordinates", "copied", format_point(point))

    def _on_show_labels_toggled(self, checked: bool) -> None:
        self.settings.show_vertex_labels = checked
        self._update_vertex_labels()
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
