# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main window: session recording, state snapshots, the logging button, crash reports."""

from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import QToolBar
from pytestqt.qtbot import QtBot
from window_checks import session_lines, settings_in

from cube_net.core.project import project_from_bytes
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.main_window import (
    MainWindow,
    format_style,
)
from cube_net.ui.session.snapshots import snapshots_in
from cube_net.ui.style import DEFAULT_STYLE


def test_recording_started_at_launch(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
    qtbot.addWidget(window)
    assert window.recorder is not None
    lines = session_lines(window.recorder.log.path)
    assert "# recording started: at app launch" in lines
    assert lines[-13:] == [
        "state net default",
        "state labels on",
        "state coordinates on",
        "state language en",
        "state blink on",
        "state max_zoom 1000",
        f"state style {format_style(DEFAULT_STYLE)}",
        "state face_colors #0057B8/#F28E00/#008A4B/#8B45B5/#E50055/#00A6D6",
        f"state window {window.width()}x{window.height()}",
        "state bounds off",
        "state ruler off",
        "state cut default",
        "state history 0 0",
    ]
    window.stop_recording("test over")


def test_no_recording_when_off(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
    qtbot.addWidget(window)
    assert window.recorder is None
    assert list(tmp_path.glob("session-*.log")) == []


def test_turning_recording_off_and_on(qtbot: QtBot, tmp_path: Path) -> None:
    settings = settings_in(tmp_path, record=False)
    window = MainWindow(settings=settings, session_dir=tmp_path)
    qtbot.addWidget(window)
    window.logging_action.trigger()  # starts a file describing the current state
    first = window.recorder
    assert first is not None
    assert not settings.record_session  # the button doesn't touch the auto-start setting
    assert "# recording started: turned on by the user" in session_lines(first.log.path)
    window.show_labels_action.setChecked(False)
    window.logging_action.trigger()  # ends it
    assert window.recorder is None
    assert session_lines(first.log.path)[-2:] == ["labels off", "stop turned off by the user"]
    window.logging_action.trigger()  # a new file, with the new state
    second = window.recorder
    assert second is not None and second.log.path != first.log.path
    assert "state labels off" in session_lines(second.log.path)
    window.stop_recording("test over")


def test_destroying_the_window_ends_its_recording(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
    recorder = window.recorder
    assert recorder is not None
    window.deleteLater()
    qtbot.waitUntil(lambda: recorder.log.closed)
    assert session_lines(recorder.log.path)[-1] == "stop the main window was closed"


def test_state_snapshot_includes_ruler_points_and_bounds(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.bounding.action.setChecked(True)
    window.ruler_action.setChecked(True)
    window.sheet_view.left_pressed.emit(11.0, 12.0)
    window.sheet_view.left_pressed.emit(12.5, 13.25)
    window.logging_action.trigger()  # turned on now: the file must describe all of this
    assert window.recorder is not None
    lines = session_lines(window.recorder.log.path)
    assert "state bounds on" in lines
    assert "state ruler on 11.000,12.000 12.500,13.250" in lines
    window.stop_recording("test over")


def test_cut_points_and_rejections_recorded(qtbot: QtBot, tmp_path: Path) -> None:
    from cube_net.ui.sheet import net_style

    window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)  # the zoom (and so the hitbox in sheet units) is set when the view is shown
    view = window.sheet_view
    inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.left_pressed.emit(11.5, 14 - inside)  # on the cut B_1-A_1
    view.left_pressed.emit(12.5, 12)  # on the cut below face 3, through D_1 at (12, 13): rejected
    view.left_pressed.emit(11.5, 13.5)
    assert window.recorder is not None
    lines = session_lines(window.recorder.log.path)
    assert lines[-3:] == ["cut cutting 11.500,14.000", "cut rejected 12.500,12.000", "cut cutting 11.500,13.500"]
    window.stop_recording("test over")
    window.logging_action.trigger()  # a new file: its state block holds the cut line
    assert window.recorder is not None
    assert "state cut cutting 11.500,14.000p 11.500,13.500" in session_lines(window.recorder.log.path)
    window.stop_recording("test over")


def test_cut_line_edits_recorded_and_labels_follow(qtbot: QtBot, tmp_path: Path) -> None:
    from cube_net.ui.sheet import net_style

    window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    view = window.sheet_view
    inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.left_pressed.emit(11.5, 14 - inside)
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside, 13.5)
    view.left_pressed.emit(11.5, 13.75)  # a midpoint: insert (when released on it)
    view.left_released.emit(11.5, 13.75)
    view.left_pressed.emit(11.5, 13.75)  # that new point: drag it
    view.mouse_moved.emit(11.25, 13.75)
    view.left_released.emit(11.25, 13.75)
    view.left_pressed.emit(11.25, 13.75)  # drag it off the net: the labels of the line step aside
    view.mouse_moved.emit(9.0, 14.5)
    assert window.cut_tool.item.labels() == ()
    view.left_released.emit(9.0, 14.5)  # rejected: back in place, labels back
    assert len(window.cut_tool.item.labels()) == 6
    assert window.recorder is not None
    lines = session_lines(window.recorder.log.path)
    assert lines[-3:] == ["cut insert 1 11.500,13.750", "cut move 1 11.250,13.750", "cut rejected 9.000,14.500"]
    window.stop_recording("test over")


def test_logs_button_at_the_bottom_of_the_panel(qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[object] = []

    def fake_open(directory: Path | None) -> bool:
        opened.append(directory)
        return False

    monkeypatch.setattr("cube_net.ui.main_window.open_session_log_folder", fake_open)
    window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.resize(800, 700)
    window.show()
    qtbot.waitExposed(window)
    toolbar = window.findChild(QToolBar, "instruments")
    assert toolbar is not None
    button = toolbar.widgetForAction(window.open_logs_action)
    bounds = toolbar.widgetForAction(window.bounding.action)
    assert button is not None and bounds is not None
    assert button.y() > toolbar.height() / 2 > bounds.y()  # at the bottom, with the rest at the top
    window.open_logs_action.trigger()
    assert opened == [tmp_path]
    assert "Could not open" in window.statusBar().currentMessage()


class TestSnapshots:
    """A session log holds the whole project, so that the file alone is enough to reproduce what follows."""

    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = True) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def close_line(self, window: MainWindow) -> None:
        from cube_net.ui.sheet import net_style

        h = net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def snapshots(self, window: MainWindow) -> list[bytes]:
        assert window.recorder is not None
        return snapshots_in(window.recorder.log.path)

    def test_at_launch(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        snapshots = self.snapshots(window)
        assert len(snapshots) == 1
        project = project_from_bytes(snapshots[0])
        assert project.state.points is None
        assert not project.history.can_undo
        window.stop_recording("test over")

    def test_when_recording_is_turned_on_it_has_the_work_so_far(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=False)
        self.close_line(window)
        window.undo_action.trigger()
        window.logging_action.trigger()
        project = project_from_bytes(self.snapshots(window)[-1])
        assert project.state.points is not None and len(project.state.points) == 2
        assert project.history.can_undo and project.history.can_redo
        window.stop_recording("test over")

    def test_unsaved_settings_are_in_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        from dataclasses import replace
        from fractions import Fraction

        window = self.make(qtbot, tmp_path, record=False)
        window.project_settings = replace(
            window.project_settings, area_threshold=Fraction(5), face_colors=("#000000",) * 6
        )
        window.logging_action.trigger()
        assert project_from_bytes(self.snapshots(window)[-1]).settings == window.project_settings
        window.stop_recording("test over")

    def test_one_more_for_another_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        assert len(self.snapshots(window)) == 1  # saving changes nothing in the project
        window.open_project_from(path)
        assert len(self.snapshots(window)) == 2
        assert project_from_bytes(self.snapshots(window)[1]).state.points is not None
        window.start_new_project()
        assert len(self.snapshots(window)) == 3
        assert project_from_bytes(self.snapshots(window)[2]).state.points is None
        window.stop_recording("test over")

    def test_it_opens_as_a_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.session.snapshots import extract_snapshots

        window = self.make(qtbot, tmp_path, record=False)
        self.close_line(window)
        window.logging_action.trigger()
        assert window.recorder is not None
        log = window.recorder.log.path
        window.stop_recording("test over")
        other = self.make(qtbot, tmp_path, record=False)
        assert other.open_project_from(extract_snapshots(log)[-1])
        assert other.editor.state.value == "cut_editing"
        other.undo_action.trigger()
        assert other.editor.state.value == "cutting"

    def test_a_person_can_still_read_the_log(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=False)
        self.close_line(window)
        window.logging_action.trigger()
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert any(line.startswith("state cut cut_editing ") for line in lines)
        assert "state history 3 0" in lines
        assert not any(line.startswith("state region") for line in lines)
        window.stop_recording("test over")


class TestSnapshotsAtLaunch:
    """One snapshot of what the session really starts from, not of the new project a window has for a moment."""

    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = True) -> MainWindow:
        settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
        settings.record_session = record
        window = MainWindow(settings=settings, session_dir=tmp_path, empty=True)  # as the application starts
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def saved_project(self, qtbot: QtBot, tmp_path: Path) -> Path:
        """A session that ended with this file saved: one point of a line in it."""
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path, record=False)
        h = net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()
        window.sheet_view.left_pressed.emit(11.5, 14 - h)
        path = tmp_path / "cube.cubenet"
        assert window.save_project_to(path)
        return path

    def snapshots(self, window: MainWindow) -> list[bytes]:
        assert window.recorder is not None
        return snapshots_in(window.recorder.log.path)

    def test_nothing_to_reopen_one_of_the_new_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        snapshots = self.snapshots(window)
        assert len(snapshots) == 1
        assert project_from_bytes(snapshots[0]).state.points is None
        window.stop_recording("test over")

    def test_reopened_one_of_that_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        self.saved_project(qtbot, tmp_path)
        window = self.make(qtbot, tmp_path)
        assert self.snapshots(window) == []
        window.reopen_last_project()
        snapshots = self.snapshots(window)
        assert len(snapshots) == 1
        assert project_from_bytes(snapshots[0]).state.points is not None
        window.stop_recording("test over")

    def test_the_other_state_lines_are_still_there_before_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        self.saved_project(qtbot, tmp_path)
        window = self.make(qtbot, tmp_path)
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert "state nothing open" in lines and "state language en" in lines
        assert not any(line.startswith("state net") for line in lines)  # there's no project yet
        window.reopen_last_project()
        lines = session_lines(window.recorder.log.path)
        assert "state net default" in lines[lines.index("state nothing open") :]
        window.stop_recording("test over")

    def test_reopening_failed_one_of_the_new_project(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        self.saved_project(qtbot, tmp_path).unlink()
        monkeypatch.setattr("cube_net.ui.main_window.ask_after_load_failed", lambda *_: AfterLoadFailed.NEW_PROJECT)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        snapshots = self.snapshots(window)
        assert len(snapshots) == 1
        assert project_from_bytes(snapshots[0]).state.points is None
        window.stop_recording("test over")

    def test_reopening_failed_and_another_opened_one_of_that(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PyQt6.QtWidgets import QFileDialog

        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        path = self.saved_project(qtbot, tmp_path)
        other = path.with_name("other.cubenet")
        path.rename(other)
        monkeypatch.setattr("cube_net.ui.main_window.ask_after_load_failed", lambda *_: AfterLoadFailed.OPEN_ANOTHER)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(other), ""))
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        snapshots = self.snapshots(window)
        assert len(snapshots) == 1
        assert project_from_bytes(snapshots[0]).state.points is not None
        window.stop_recording("test over")

    def test_turned_on_later_it_always_has_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        self.saved_project(qtbot, tmp_path)
        window = self.make(qtbot, tmp_path, record=False)
        window.logging_action.trigger()
        assert self.snapshots(window) == []  # nothing open yet
        window.reopen_last_project()
        assert len(self.snapshots(window)) == 1
        window.stop_recording("test over")


class TestLoggingButton:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_right_above_logs(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        toolbar = window.findChild(QToolBar)
        assert toolbar is not None
        actions = toolbar.actions()
        assert actions.index(window.logging_action) == actions.index(window.open_logs_action) - 1

    def test_an_icon_and_no_text(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        toolbar = window.findChild(QToolBar)
        assert toolbar is not None
        button = toolbar.widgetForAction(window.logging_action)
        assert button is not None and not window.logging_action.icon().isNull()
        assert window.logging_action.text() == ""

    def test_start_then_stop(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.instruments.logging_icons import record_icon, stop_icon

        window = self.make(qtbot, tmp_path)
        action = window.logging_action
        assert window.recorder is None
        assert action.toolTip() == "Start logging"
        assert action.icon().cacheKey() == record_icon().cacheKey()
        action.trigger()
        assert window.recorder is not None
        assert action.toolTip() == "Stop logging"
        assert action.icon().cacheKey() == stop_icon().cacheKey()
        path = window.recorder.log.path
        action.trigger()
        assert window.recorder is None
        assert action.toolTip() == "Start logging"
        assert session_lines(path)[-1] == "stop turned off by the user"

    def test_stop_while_it_started_at_launch(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        assert window.recorder is not None
        assert window.logging_action.toolTip() == "Stop logging"
        window.logging_action.trigger()
        assert window.recorder is None
        assert window.settings.record_session is True  # still starts by itself next time

    def test_tooltips_in_russian(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.i18n import TRANSLATIONS, Language

        window = self.make(qtbot, tmp_path)
        TRANSLATIONS.set_language(Language.RUSSIAN)
        assert window.logging_action.toolTip() == "Начать логирование"
        window.logging_action.trigger()
        assert window.logging_action.toolTip() == "Остановить логирование"
        assert window.settings_panel.preferences.auto_log.text() == "Автоматически начинать логирование"
        window.stop_recording("test over")


class TestCrashReports:
    """What a crash report has of the main window (`ui/crash`)."""

    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_the_state_with_the_snapshot_and_the_recent_input(self, qtbot: QtBot, tmp_path: Path) -> None:
        import time

        from cube_net.core.project import project_from_bytes
        from cube_net.ui.crash.crash_report import write_crash_report
        from cube_net.ui.session.snapshots import snapshots_in

        window = self.make(qtbot, tmp_path)
        qtbot.keyClick(window.sheet_view.viewport(), Qt.Key.Key_A)
        sections = window.crash_sections()
        assert [s.title for s in sections] == ["State", "Recent input"]  # no recording: no session log
        assert "state cut default" in sections[0].text()
        assert "key A" in sections[1].text()
        try:
            raise ValueError("broken")
        except ValueError as e:
            path = write_crash_report(
                tmp_path / "crashes", (ValueError, e, e.__traceback__), sections, time.monotonic()
            )
        [snapshot] = snapshots_in(path)  # the developer gets the project back from it
        restored = project_from_bytes(snapshot).state.net
        assert [v.position for v in restored.vertices] == [v.position for v in window.editor.net.vertices]

    def test_the_session_log_too_and_it_ends(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        assert window.recorder is not None
        log = window.recorder.log.path
        sections = {s.title: s for s in window.crash_sections()}
        assert sections["Session log"].text().startswith(f"{log}\n\n# Cube Net")
        window.end_recording_after_crash()
        assert window.recorder is None
        assert session_lines(log)[-1] == "stop crashed"
