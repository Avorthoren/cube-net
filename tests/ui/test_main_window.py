# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import QToolBar
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Vec
from cube_net.core.project import project_from_bytes
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.main_window import (
    APP_TITLE,
    NO_COORDINATES,
    MainWindow,
    format_coordinates,
    format_ruler_total,
    format_style,
)
from cube_net.ui.session.snapshots import snapshots_in
from cube_net.ui.style import DEFAULT_STYLE


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never touch the real user settings in tests."""
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))


def test_main_window_opens(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    assert window.windowTitle() == f"[*]Untitled — {APP_TITLE}"
    assert window.centralWidget() is window.sheet_view


def test_default_sheet(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    r = window.sheet_view.sheet_rect()
    assert (r.left(), r.top(), r.right(), r.bottom()) == (5, 5, 18, 19)


def test_coordinates_in_status_bar(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    assert window.coords_label.text() == NO_COORDINATES
    window.sheet_view.mouse_moved.emit(11.25, 12.0)
    assert window.coords_label.text() == "x: 11.250   y: 12.000"
    window.sheet_view.mouse_left.emit()
    assert window.coords_label.text() == NO_COORDINATES


def test_format_coordinates_three_decimals() -> None:
    assert format_coordinates(11.0, -0.0004) == "x: 11.000   y: -0.000"
    assert format_coordinates(12.3456, 7.1) == "x: 12.346   y: 7.100"


def test_hit_test_follows_default_net(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)  # vertex circles have their pixel size only once the zoom is set
    view = window.sheet_view
    assert view.press_claimed(10.0, 13.0)  # a perimeter vertex
    assert not view.press_claimed(11.5, 12.5)  # the middle of face 2: nothing to click there
    assert not view.press_claimed(10.5, 13.5)  # empty corner left of face 1


def test_vertex_labels_toggle(qtbot: QtBot, tmp_path: Path) -> None:
    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    window = MainWindow(settings=settings)
    qtbot.addWidget(window)
    item = window.sheet_view.net_item()
    assert item is not None
    assert window.show_labels_action.isChecked()
    labels = item.labels()
    assert labels is not None and len(labels) == 14
    window.show_labels_action.setChecked(False)
    assert item.labels() is None
    assert settings.show_vertex_labels is False
    window.show_labels_action.setChecked(True)
    assert item.labels() is not None and settings.show_vertex_labels is True


def test_labels_off_at_start_when_disabled_in_settings(qtbot: QtBot, tmp_path: Path) -> None:
    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    settings.show_vertex_labels = False
    window = MainWindow(settings=settings)
    qtbot.addWidget(window)
    item = window.sheet_view.net_item()
    assert item is not None and item.labels() is None
    assert not window.show_labels_action.isChecked()


def settings_in(tmp_path: Path, record: bool) -> AppSettings:
    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    settings.record_session = record
    settings.settings_open = False  # as the user left it; it's open only at the very first start
    return settings


def session_lines(path: Path) -> list[str]:
    """Lines of a session file without the times."""
    return [line if line.startswith("#") else line.split(" ", 1)[1] for line in path.read_text().splitlines()]


def test_recording_started_at_launch(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
    qtbot.addWidget(window)
    assert window.recorder is not None
    lines = session_lines(window.recorder.log.path)
    assert "# recording started: at app launch" in lines
    assert lines[-11:] == [
        "state net default",
        "state labels on",
        "state language en",
        "state blink on",
        "state max_zoom 1000",
        f"state style {format_style(DEFAULT_STYLE)}",
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


def test_cut_hover_wired(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=False))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    from cube_net.ui.sheet import net_style

    x = 10 + net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()  # inside the hitbox of A_2 - E_2
    window.cut_hover.update_at(x, 12.5)
    assert window.cut_hover.hovered() is not None


def test_ruler_toggle_and_recording(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.ruler_action.setChecked(True)
    assert window.ruler_tool.active
    window.sheet_view.left_pressed.emit(11.25, 12.0)
    window.ruler_action.setChecked(False)
    assert not window.ruler_tool.active
    assert window.recorder is not None
    lines = session_lines(window.recorder.log.path)
    assert lines[-3:] == ["ruler on", "ruler 11.250,12.000", "ruler off"]
    window.stop_recording("test over")


def test_ruler_shortcut_recorded_every_time(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.show()
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)  # shortcuts only work in the active window
    qtbot.keyClick(window, Qt.Key.Key_R)
    qtbot.keyClick(window, Qt.Key.Key_R)
    assert window.recorder is not None
    lines = [line for line in session_lines(window.recorder.log.path) if line.startswith(("shortcut", "ruler"))]
    assert lines == ["shortcut R", "ruler on", "shortcut R", "ruler off"]
    window.stop_recording("test over")


def test_destroying_the_window_ends_its_recording(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
    recorder = window.recorder
    assert recorder is not None
    window.deleteLater()
    qtbot.waitUntil(lambda: recorder.log.closed)
    assert session_lines(recorder.log.path)[-1] == "stop the main window was closed"


def test_ruler_total_on_instrument_panel(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=False))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    action = window.ruler_total_action
    assert not action.isVisible()  # only while the ruler is active
    window.ruler_action.setChecked(True)
    assert action.isVisible()
    assert window.ruler_total_label.text() == "Σ —"
    window.sheet_view.left_pressed.emit(11.0, 12.0)
    assert window.ruler_total_label.text() == "Σ 0.000"
    window.sheet_view.left_pressed.emit(12.0, 13.0)
    assert window.ruler_total_label.text() == "Σ 1.414"
    window.ruler_action.setChecked(False)
    assert not action.isVisible()


def test_format_ruler_total() -> None:
    assert format_ruler_total(None) == "Σ —"
    assert format_ruler_total(7.0999) == "Σ 7.100"


def test_sheet_does_not_move_when_ruler_total_widens_the_panel(qtbot: QtBot, tmp_path: Path) -> None:
    from PyQt6.QtCore import QPointF

    window = MainWindow(settings=settings_in(tmp_path, record=False))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    view = window.sheet_view

    def h1_in_window() -> object:
        return view.viewport().mapTo(window, view.from_sheet(QPointF(11, 12)).toPoint())

    before, x = h1_in_window(), view.x()
    window.ruler_action.setChecked(True)
    window.ruler_total_label.setText("Σ 123456789.123")  # a long total: the panel gets wider
    qtbot.waitUntil(lambda: view.x() > x)
    assert h1_in_window() == before
    window.ruler_action.setChecked(False)
    qtbot.waitUntil(lambda: view.x() == x)
    assert h1_in_window() == before


def test_bounding_rectangle_on_panel_and_recorded(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
    qtbot.addWidget(window)
    assert window.bounding.label.text() == "Area\n12.000"
    assert not window.bounding.success  # 12 is not below 7.1
    window.bounding.action.setChecked(True)
    assert len(window.bounding_item.corners()) == 4
    window.bounding.action.setChecked(False)
    assert window.recorder is not None
    assert session_lines(window.recorder.log.path)[-2:] == ["bounds on", "bounds off"]
    window.stop_recording("test over")


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
    view.left_pressed.emit(12.5, 13.5)  # outside: rejected
    view.left_pressed.emit(11.5, 13.5)
    assert window.recorder is not None
    lines = session_lines(window.recorder.log.path)
    assert lines[-3:] == ["cut cutting 11.500,14.000", "cut rejected 12.500,13.500", "cut cutting 11.500,13.500"]
    window.stop_recording("test over")
    window.logging_action.trigger()  # a new file: its state block holds the cut line
    assert window.recorder is not None
    assert "state cut cutting 11.500,14.000p 11.500,13.500" in session_lines(window.recorder.log.path)
    window.stop_recording("test over")


def test_no_panning_inside_a_vertex_circle_outside_the_net(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=False))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    from cube_net.ui.sheet import net_style

    view = window.sheet_view
    near = net_style.VERTEX_RADIUS_PX / 2 / view.scale_factor()
    assert view.press_claimed(11 - near, 14 + near)  # up-left of A_1: off the net, but in its circle
    assert not view.press_claimed(11 - 3 * near, 14 + 3 * near)  # farther out: panning is fine there


def test_cut_line_labels_follow_the_line_and_the_setting(qtbot: QtBot, tmp_path: Path) -> None:
    from cube_net.ui.sheet import net_style

    window = MainWindow(settings=settings_in(tmp_path, record=False))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    view = window.sheet_view
    view.left_pressed.emit(11.5, 14 - net_style.CUT_HITBOX_PX / 2 / view.scale_factor())
    assert [str(label) for _, label in window.cut_tool.item.labels()] == ["I_1", "I_2"]
    window.show_labels_action.setChecked(False)
    assert window.cut_tool.item.labels() == ()
    window.show_labels_action.setChecked(True)
    assert len(window.cut_tool.item.labels()) == 2


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


def test_no_panning_from_a_cut_line_point_off_the_net(qtbot: QtBot, tmp_path: Path) -> None:
    from PyQt6.QtCore import QPointF

    from cube_net.ui.sheet import net_style

    window = MainWindow(settings=settings_in(tmp_path, record=False))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    view = window.sheet_view
    inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.left_pressed.emit(11.5, 14 - inside)
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside, 13.5)
    above = 14 + net_style.VERTEX_RADIUS_PX / 2 / view.scale_factor()  # in the start point's circle, off the net
    pos = view.from_sheet(QPointF(11.5, above)).toPoint()
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    assert not view.is_panning()
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)


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


class TestRearrangement:
    def closed_corner_cut(self, window: MainWindow) -> None:
        from cube_net.ui.sheet import net_style

        view = window.sheet_view
        inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(11.5, 14 - inside)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - inside, 13.5)

    def bottom_of_face_5(self, window: MainWindow) -> tuple[float, float]:
        """On the part x_2-B_3 of the cut A_3-B_3."""
        from cube_net.ui.sheet import net_style

        return 11.75, 10 + net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_click_on_a_part_of_a_cut_rearranges_and_everything_follows(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtCore import QPointF

        window = self.make(qtbot, tmp_path)
        self.closed_corner_cut(window)
        view = window.sheet_view
        h1_before = view.from_sheet(QPointF(11, 12))
        assert window.bounding.label.text() == "Area\n12.000"
        view.left_pressed.emit(*self.bottom_of_face_5(window))
        assert window.editor.state.value == "cut_approving"
        assert window.net is window.editor.display_net
        item = view.net_item()
        assert item is not None and len(item.glue()) == 2
        assert window.cut_tool.item.points() == ()  # the line is part of the net now
        assert window.cut_tool.item.midpoints() == []
        assert window.bounding.label.text() != "Area\n12.000"  # the area follows
        r = view.sheet_rect()
        assert r.top() == 4.5  # the sheet follows: y_2 is at 9.5, plus the margin of 5
        h1_after = view.from_sheet(QPointF(11, 12))
        assert (h1_after.x(), h1_after.y()) == pytest.approx((h1_before.x(), h1_before.y()), abs=1.5)  # nothing jumps

    def test_undo_goes_back_to_editing(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.closed_corner_cut(window)
        window.sheet_view.left_pressed.emit(*self.bottom_of_face_5(window))
        window.undo_action.trigger()
        assert window.editor.state.value == "cut_editing"
        assert window.bounding.label.text() == "Area\n12.000"
        assert len(window.cut_tool.item.points()) == 3
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert lines[-2:] == ["cut glue 11.500,10.000 12.000,10.000 ok", "cut undo cut_editing"]
        window.stop_recording("test over")

    def test_labels_keep_the_previewed_names_after_rearranging(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_corner_cut(window)
        before = {label.name for _, label in window.cut_tool.item.labels()}
        window.sheet_view.left_pressed.emit(*self.bottom_of_face_5(window))
        item = window.sheet_view.net_item()
        assert item is not None
        labels = item.labels()
        assert labels is not None
        assert before == {"I", "J", "K"}
        assert before <= {label.name for label in labels.values()}
        assert sorted(label.index for label in labels.values() if label.name == "I") == [1, 2, 3]  # x_1, x_2, x's copy

    def test_hover_follows_the_divided_cut_in_editing(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_corner_cut(window)
        x, y = self.bottom_of_face_5(window)
        window.cut_hover.update_at(x, y)
        cut = window.cut_hover.hovered()
        assert cut is not None
        ends = {float(p.x) for p in (cut.origin.position, cut.destination.position)}
        assert ends == {11.5, 12.0}  # only the part x_2-B_3 of A_3-B_3

    def test_state_snapshot_has_the_glue(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_corner_cut(window)
        window.sheet_view.left_pressed.emit(*self.bottom_of_face_5(window))
        window.logging_action.trigger()
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert "state glue 11.500,10.000 12.000,10.000" in lines
        assert any(line.startswith("state cut cut_approving ") for line in lines)
        window.stop_recording("test over")


class TestApproveButton:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def valid_rearrangement(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)

    def overlapping_rearrangement(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(12 - h, 13.5)  # on D_1-B_1
        view.left_pressed.emit(11 + h, 11.5)  # on H_1-E_1: closes the line
        view.left_pressed.emit(12.75, 13 + h - 2 * h)  # on z_3-B_2, from inside face 3

    def test_disabled_until_a_valid_rearrangement(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.approve_action.isEnabled()
        self.valid_rearrangement(window)
        assert window.approve_action.isEnabled()
        item = window.sheet_view.net_item()
        assert item is not None and item.overlapping() == frozenset()
        window.undo_action.trigger()
        assert not window.approve_action.isEnabled()

    def test_overlap_shown_black_and_not_approvable(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.overlapping_rearrangement(window)
        assert window.editor.state.value == "cut_approving"
        assert not window.approve_action.isEnabled()
        item = window.sheet_view.net_item()
        assert item is not None and item.overlapping()
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1].endswith(" overlap")
        window.undo_action.trigger()
        assert item.overlapping() == frozenset()
        window.stop_recording("test over")

    def test_click_on_the_x_acts_as_undo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.overlapping_rearrangement(window)
        line = window.editor.cut_line
        window.sheet_view.left_pressed.emit(12.75, 13.0)
        window.sheet_view.left_released.emit(12.75, 13.0)
        assert window.editor.state.value == "cut_editing"
        assert window.editor.cut_line is not None and window.editor.cut_line.points == line.points
        assert window.net is window.editor.net
        assert window.cut_tool.approve_button.position() is None
        assert not window.redo_action.isEnabled()  # it overlapped: it's forgotten
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1] == "cut undo cut_editing"
        window.stop_recording("test over")

    def test_shortcut_is_ctrl_enter(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.approve_action.shortcut().toString() == "Ctrl+Return"


class TestDividedView:
    """While hovering a perimeter edge in CUT_EDITING, cuts that can't be chosen are shown thin and black."""

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def close_line(self, window: MainWindow) -> None:
        """From the top of face 1, through y, to its right side (the corner cut)."""
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def divided_on(self, window: MainWindow) -> bool:
        item = window.sheet_view.net_item()
        assert item is not None
        return item.divided() is not None

    def hover_edge(self, window: MainWindow) -> None:
        window.sheet_view.mouse_moved.emit(10 + self.hitbox(window), 12.5)  # A_2-E_2

    def test_on_while_hovering_an_edge_off_elsewhere(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(7.0, 7.0)
        assert not self.divided_on(window)
        self.hover_edge(window)
        assert self.divided_on(window)
        window.sheet_view.mouse_moved.emit(11.5, 12.5)  # the middle of face 2
        assert not self.divided_on(window)
        self.hover_edge(window)
        window.sheet_view.mouse_left.emit()
        assert not self.divided_on(window)

    def test_off_in_other_states(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.hover_edge(window)
        assert not self.divided_on(window)  # DEFAULT
        h = self.hitbox(window)
        window.sheet_view.mouse_moved.emit(7.0, 7.0)
        window.sheet_view.left_pressed.emit(11.5, 14 - h)
        self.hover_edge(window)
        assert not self.divided_on(window)  # CUTTING

    def test_off_while_the_ruler_is_active(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_edge(window)
        assert self.divided_on(window)
        window.ruler_action.setChecked(True)
        assert not self.divided_on(window)
        window.sheet_view.mouse_moved.emit(7.0, 7.0)
        self.hover_edge(window)
        assert not self.divided_on(window)
        window.ruler_action.setChecked(False)
        assert self.divided_on(window)  # still over the edge

    def test_off_while_dragging_a_point(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_edge(window)
        assert self.divided_on(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)  # the inner point: the drag starts
        assert not self.divided_on(window)
        self.hover_edge(window)
        assert not self.divided_on(window)
        view.left_released.emit(11.5, 13.5)
        view.mouse_moved.emit(7.0, 7.0)
        self.hover_edge(window)
        assert self.divided_on(window)

    def test_the_new_line_itself_does_not_trigger_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(11.5 + self.hitbox(window), 13.8)  # beside the new line
        assert not self.divided_on(window)

    def test_off_after_rearranging_and_back_after_undo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        h = self.hitbox(window)
        window.sheet_view.mouse_moved.emit(11.75, 10 + h)
        assert self.divided_on(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + h)
        assert window.editor.state.value == "cut_approving"
        assert not self.divided_on(window)
        window.undo_action.trigger()
        assert not self.divided_on(window)  # the hover was reset; the next move decides
        window.sheet_view.mouse_moved.emit(11.75, 10 + h)
        assert self.divided_on(window)


class TestApproving:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        window.activateWindow()
        qtbot.waitUntil(window.isActiveWindow)
        return window

    def rearranged(self, window: MainWindow) -> None:
        from cube_net.ui.sheet import net_style

        h = net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)

    def test_check_mark_accepts_and_everything_follows(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.rearranged(window)
        area = window.bounding.label.text()
        window.approve_action.trigger()
        assert window.editor.state.value == "default"
        assert window.net is window.editor.net
        assert not window.approve_action.isEnabled()
        assert window.undo_action.isEnabled()
        assert window.bounding.label.text() == area
        item = window.sheet_view.net_item()
        assert item is not None
        assert item.glue() == () and item.overlapping() == frozenset()
        assert window.cut_tool.item.points() == ()
        labels = item.labels()
        assert labels is not None and len(labels) == 20
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-2:] == [
            "cut glue 11.500,10.000 12.000,10.000 ok",
            "cut approve",
        ]
        window.stop_recording("test over")

    @pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Enter])
    def test_ctrl_enter_accepts(self, qtbot: QtBot, tmp_path: Path, key: Qt.Key) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearranged(window)
        qtbot.keyClick(window, key, Qt.KeyboardModifier.ControlModifier)
        assert window.editor.state.value == "default"

    def test_ctrl_enter_does_nothing_when_not_approvable(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        qtbot.keyClick(window, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
        assert window.editor.state.value == "default"
        assert window.editor.approved_cuts == 0

    def test_the_next_cut_starts_on_the_new_net(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path)
        self.rearranged(window)
        window.approve_action.trigger()
        view = window.sheet_view
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        assert view.press_claimed(11.75, 9.5 + h)  # a cut of the moved piece, under face 5
        assert not view.press_claimed(11.75, 13.9)  # where the top of face 1 was
        window.cut_hover.update_at(11.75, 9.5 + h)
        cut = window.cut_hover.hovered()
        assert cut is not None  # y_2-z_2, a cut of the new net
        view.left_pressed.emit(11.75, 9.5 + h)
        assert window.editor.state.value == "cutting"
        assert window.cut_tool.item.points()[0].position == Vec(F(47, 4), F(19, 2))

    def test_state_snapshot_describes_the_new_net(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearranged(window)
        window.approve_action.trigger()
        window.logging_action.trigger()
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert "state net after 1 approved cuts" in lines
        snapshots = snapshots_in(window.recorder.log.path)
        project = project_from_bytes(snapshots[-1])
        assert project.state.approved_cuts == 1
        assert len(project.state.net.regions) == 7
        window.stop_recording("test over")


class TestApproveButtonOnTheSheet:
    def test_clicking_it_approves_and_it_is_not_on_the_panel(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtCore import QPointF

        from cube_net.ui.sheet import net_style

        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        toolbar = window.findChild(QToolBar, "instruments")
        assert toolbar is not None and window.approve_action not in toolbar.actions()
        view = window.sheet_view
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)
        assert window.editor.state.value == "cut_approving"
        position = view.from_sheet(QPointF(11.75, 10)).toPoint()
        qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=position)
        assert window.editor.state.value == "default"
        assert window.cut_tool.approve_button.position() is None


class TestUndoRedo:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        window.activateWindow()
        qtbot.waitUntil(window.isActiveWindow)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def closed_line(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def rearrange(self, window: MainWindow) -> None:
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))

    def shown(self, window: MainWindow) -> tuple[object, ...]:
        """What the user sees of the state."""
        item = window.sheet_view.net_item()
        assert item is not None
        return (
            window.editor.state,
            window.net,
            window.cut_tool.item.points(),
            item.glue(),
            item.overlapping(),
            window.bounding.label.text(),
            window.cut_tool.approve_button.position(),
            window.approve_action.isEnabled(),
        )

    def test_nothing_to_undo_at_first(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.undo_action.isEnabled()
        assert not window.redo_action.isEnabled()

    def test_shortcuts(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        qtbot.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        assert window.editor.state.value == "cutting"
        qtbot.keyClick(window, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
        assert window.editor.state.value == "cut_editing"

    def test_in_every_state_everything_on_screen_follows(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        h = self.hitbox(window)
        steps = [
            lambda: view.left_pressed.emit(11.5, 14 - h),
            lambda: view.left_pressed.emit(11.5, 13.5),
            lambda: view.left_pressed.emit(12 - h, 13.5),
            lambda: self.rearrange(window),
        ]
        states = [self.shown(window)]
        for step in steps:
            step()
            states.append(self.shown(window))
        assert window.approve_action.isEnabled()
        window.approve_action.trigger()
        states.append(self.shown(window))
        assert window.editor.state.value == "default"

        window.undo_action.trigger()  # the approval and the rearrangement together
        assert self.shown(window) == states[3]
        for i in (2, 1, 0):
            window.undo_action.trigger()
            assert self.shown(window) == states[i]
        assert not window.undo_action.isEnabled()
        for i in range(1, 6):
            assert window.redo_action.isEnabled()
            window.redo_action.trigger()
            assert self.shown(window) == states[i]
        assert not window.redo_action.isEnabled()

    def test_a_new_action_disables_redo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        window.undo_action.trigger()
        assert window.redo_action.isEnabled()
        window.sheet_view.left_pressed.emit(11.7, 13.7)
        assert not window.redo_action.isEnabled()

    def test_not_while_dragging_a_point(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)
        assert window.cut_tool.dragging
        assert not window.undo_action.isEnabled()
        view.mouse_moved.emit(11.6, 13.6)
        assert not window.undo_action.isEnabled()
        view.left_released.emit(11.6, 13.6)
        assert window.undo_action.isEnabled()
        window.undo_action.trigger()
        line = window.editor.cut_line
        assert line is not None and float(line.points[1].position.x) == 11.5

    def test_pressing_a_point_without_moving_it_gives_undo_back(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        done = window.editor.history.done_count
        window.sheet_view.left_pressed.emit(11.5, 13.5)
        window.sheet_view.left_released.emit(11.5, 13.5)
        assert window.undo_action.isEnabled()
        assert window.editor.history.done_count == done

    def test_rubber_band_does_not_start_at_a_point_that_is_gone(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.mouse_moved.emit(11.7, 13.5)
        window.undo_action.trigger()
        assert window.cut_tool.item.rubber_band() is None
        view.mouse_moved.emit(11.7, 13.5)
        band = window.cut_tool.item.rubber_band()
        assert band is not None and band[0].y == 14

    def test_hover_follows_the_line_after_undo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        view = window.sheet_view
        view.mouse_moved.emit(10 + self.hitbox(window), 12.5)
        item = view.net_item()
        assert item is not None and item.divided() is not None
        window.undo_action.trigger()  # the line isn't closed anymore: nothing to show
        assert window.editor.state.value == "cutting"
        assert item.divided() is None
        window.redo_action.trigger()
        view.mouse_moved.emit(7.0, 7.0)
        view.mouse_moved.emit(10 + self.hitbox(window), 12.5)
        assert item.divided() is window.editor.split()

    def test_labels_come_back(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        self.rearrange(window)
        item = window.sheet_view.net_item()
        assert item is not None

        def names() -> set[str]:
            labels = item.labels()
            assert labels is not None
            return {str(label) for label in labels.values()}

        window.approve_action.trigger()
        approved = names()
        window.undo_action.trigger()
        window.redo_action.trigger()
        window.redo_action.trigger()
        assert names() == approved

    def test_the_ruler_is_not_part_of_the_history(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        done = window.editor.history.done_count
        window.ruler_tool.set_active(True)
        window.sheet_view.left_pressed.emit(7.0, 7.0)
        points = window.ruler_tool.ruler.points
        assert len(points) == 1
        assert window.editor.history.done_count == done
        window.undo_action.trigger()
        assert window.ruler_tool.ruler.points == points

    def test_drawing_area_follows_the_net(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.closed_line(window)
        self.rearrange(window)
        window.undo_action.trigger()
        area = window.cut_tool.item.boundingRect()
        box = window.editor.display_net.bounding_box()
        assert area.left() < float(box.lo.x) and area.bottom() > float(box.hi.y)

    def test_recorded(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.closed_line(window)
        window.undo_action.trigger()
        window.redo_action.trigger()
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-2:] == ["cut undo cutting", "cut redo cut_editing"]
        window.stop_recording("test over")


class TestFlashKeepsTheHover:
    def test_useless_cuts_stay_thin_black_after_the_flash(self, qtbot: QtBot, tmp_path: Path) -> None:
        """The mouse stays on a cut that can't be chosen: it flashes, and then everything is as it was."""
        from cube_net.ui.sheet import net_style

        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        view = window.sheet_view
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        useless = 10.5, 12 + h  # E_2-H_1: its counterpart is in the same half
        view.mouse_moved.emit(*useless)
        item = view.net_item()
        assert item is not None
        hovered = window.cut_hover.hovered()
        assert hovered is not None and item.divided() is not None

        with qtbot.waitSignal(window.cut_tool.rejected):
            view.left_pressed.emit(*useless)
        assert item.divided() is not None
        qtbot.waitUntil(lambda: window.cut_tool.item.flash() is None, timeout=2000)

        assert window.cut_hover.hovered() is hovered
        assert item.divided() is window.editor.split()


class TestVertexHoverWhileEditing:
    """In CUT_EDITING perimeter vertices can't be clicked, so they don't highlight, except for where a dragged endpoint
    would go."""

    # The corner cut: x on the top of face 1, y, z on its right side; z's image is on the top of face 3.
    X = 11.5, 14.0
    Y = 11.5, 13.5
    Z_IMAGE = 12.5, 13.0
    A_1 = 11.0, 14.0
    B_1 = 12.0, 14.0
    B_2 = 13.0, 13.0

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def close_line(self, window: MainWindow) -> None:
        from cube_net.ui.sheet import net_style

        h = net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(*self.Y)
        view.left_pressed.emit(12 - h, 13.5)
        assert window.editor.state.value == "cut_editing"

    def highlighted(self, window: MainWindow) -> tuple[float, float] | None:
        vertex = window.cut_hover.hovered_vertex()
        return None if vertex is None else (float(vertex.position.x), float(vertex.position.y))

    def test_not_while_just_hovering(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        for place in (self.A_1, self.B_2, self.Z_IMAGE, self.X):
            view.mouse_moved.emit(*place)
            assert self.highlighted(window) is None, place

    def test_gone_as_soon_as_the_line_closes(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        view.left_pressed.emit(*self.A_1)
        view.left_pressed.emit(*self.Y)
        view.mouse_moved.emit(*self.B_1)
        assert self.highlighted(window) == self.B_1  # still cutting: a vertex can end the line
        view.left_pressed.emit(*self.B_1)
        assert window.editor.state.value == "cut_editing"
        assert self.highlighted(window) is None

    def test_where_a_dragged_endpoint_would_go(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(*self.X)
        view.mouse_moved.emit(*self.A_1)
        assert self.highlighted(window) == self.A_1
        view.mouse_moved.emit(11.2, 14.0)
        assert self.highlighted(window) is None
        view.mouse_moved.emit(*self.B_2)
        assert self.highlighted(window) == self.B_2
        view.left_released.emit(*self.B_2)
        assert self.highlighted(window) is None

    def test_a_dragged_endpoint_does_not_light_up_an_image(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(*self.X)
        view.mouse_moved.emit(*self.Z_IMAGE)
        assert self.highlighted(window) is None

    def test_a_dragged_inner_point_does_not_light_up_anything(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(*self.Y)
        view.mouse_moved.emit(*self.A_1)
        assert self.highlighted(window) is None

    def test_back_after_undo(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.undo_action.trigger()
        assert window.editor.state.value == "cutting"
        window.sheet_view.mouse_moved.emit(*self.B_2)
        assert self.highlighted(window) == self.B_2


class TestNoHoverWhileApproving:
    """Only the button can be clicked in CUT_APPROVING, so nothing on the perimeter highlights."""

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def valid(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)

    def overlapping(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11 + h, 11.5)
        view.left_pressed.emit(12.75, 13 - h)

    def assert_nothing_highlights(self, window: MainWindow) -> None:
        view = window.sheet_view
        h = self.hitbox(window)
        for x, y in ((10 + h, 12.5), (10.0, 13.0), (11 - h, 11.5), (12.0, 10.0)):  # cuts and vertices
            view.mouse_moved.emit(x, y)
            assert window.cut_hover.hovered() is None, (x, y)
            assert window.cut_hover.hovered_vertex() is None, (x, y)

    def test_with_a_valid_rearrangement(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.valid(window)
        assert window.editor.state.value == "cut_approving"
        self.assert_nothing_highlights(window)

    def test_with_an_overlapping_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.overlapping(window)
        assert window.editor.state.value == "cut_approving"
        self.assert_nothing_highlights(window)

    def test_gone_at_once_when_rearranging(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.mouse_moved.emit(11.75, 10 + h)
        assert window.cut_hover.hovered() is not None
        view.left_pressed.emit(11.75, 10 + h)
        assert window.cut_hover.hovered() is None

    def test_back_after_undo_and_after_approving(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.valid(window)
        h = self.hitbox(window)
        view = window.sheet_view
        window.undo_action.trigger()
        view.mouse_moved.emit(10 + h, 12.5)
        assert window.cut_hover.hovered() is not None  # CUT_EDITING: cuts can be chosen
        window.redo_action.trigger()
        self.assert_nothing_highlights(window)
        window.approve_action.trigger()
        assert window.editor.state.value == "default"
        view.mouse_moved.emit(10 + h, 12.5)
        assert window.cut_hover.hovered() is not None
        view.mouse_moved.emit(10.0, 13.0)
        assert window.cut_hover.hovered_vertex() is not None


class TestPanningFromInsideTheNet:
    """A drag pans the sheet from wherever a press means nothing in the current state, even inside the net."""

    MIDDLE_OF_FACE_2 = 11.5, 12.5

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def close_line(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        assert window.editor.state.value == "cut_editing"

    def rearrange(self, window: MainWindow) -> None:
        self.close_line(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))
        assert window.editor.state.value == "cut_approving"

    def assert_drag_pans(self, qtbot: QtBot, window: MainWindow, x: float, y: float) -> None:
        """A real drag from (x, y): the sheet follows the mouse, and the editor doesn't notice."""
        from PyQt6.QtCore import QPoint, QPointF

        view = window.sheet_view
        state = window.editor.state
        done = window.editor.history.done_count
        start = view.from_sheet(QPointF(x, y)).toPoint()
        end = start + QPoint(40, -30)
        qtbot.mouseMove(view.viewport(), start)
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
        assert view.is_panning()
        qtbot.mouseMove(view.viewport(), end)
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
        assert not view.is_panning()
        moved = view.to_sheet(QPointF(end))
        assert (moved.x(), moved.y()) == pytest.approx((x, y), abs=2 / view.scale_factor())
        assert window.editor.state is state
        assert window.editor.history.done_count == done

    def test_default_pans_from_the_middle_of_a_face(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.assert_drag_pans(qtbot, window, *self.MIDDLE_OF_FACE_2)
        assert window.editor.cut_line is None

    def test_default_what_can_be_clicked(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        assert view.press_claimed(10 + h, 12.5)  # a cut
        assert view.press_claimed(10.0, 13.0)  # a vertex
        assert not view.press_claimed(*self.MIDDLE_OF_FACE_2)
        assert not view.press_claimed(10 + 3 * h, 12.5)  # just past the hitbox of the cut

    def test_a_press_on_a_cut_still_starts_the_line(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtCore import QPointF

        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        pos = view.from_sheet(QPointF(10 + self.hitbox(window), 12.5)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert not view.is_panning()
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert window.editor.state.value == "cutting"

    def test_cutting_a_click_on_the_net_still_adds_a_point(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - self.hitbox(window))
        assert view.press_claimed(*self.MIDDLE_OF_FACE_2)
        assert not view.press_claimed(10.5, 13.5)  # off the net: panning, as always

    def test_cut_editing_what_can_be_clicked(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        h = self.hitbox(window)
        view = window.sheet_view
        for place in (
            (11.5, 14.0),  # an endpoint of the line
            (11.5, 13.5),  # its inner point
            (11.5, 13.75),  # the circle in the middle of a segment
            (11.75, 10 + h),  # a cut that can be chosen
            (10.5, 12 + h),  # a cut that can't, which is told by a flash
        ):
            assert view.press_claimed(*place), place
        for place in (
            self.MIDDLE_OF_FACE_2,
            (10.0, 13.0),  # a perimeter vertex
            (12.5, 13.0),  # a counterpart image
            (11.5 + h, 13.625),  # next to the new line, whose hitbox means nothing
        ):
            assert not view.press_claimed(*place), place

    def test_cut_editing_pans_from_a_face_and_a_vertex(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.assert_drag_pans(qtbot, window, *self.MIDDLE_OF_FACE_2)
        self.assert_drag_pans(qtbot, window, 10.0, 13.0)

    def test_cut_approving_only_the_button_can_be_clicked(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearrange(window)
        h = self.hitbox(window)
        view = window.sheet_view
        assert view.press_claimed(11.75, 10.0)  # the button
        for place in (self.MIDDLE_OF_FACE_2, (10 + h, 12.5), (10.0, 13.0)):  # a face, a cut, a vertex
            assert not view.press_claimed(*place), place
        self.assert_drag_pans(qtbot, window, *self.MIDDLE_OF_FACE_2)
        self.assert_drag_pans(qtbot, window, 10 + h, 12.5)

    def test_cut_approving_the_x_can_be_clicked_too(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11 + h, 11.5)
        view.left_pressed.emit(12.75, 13 - h)
        assert window.editor.rearranged is not None and not window.editor.rearranged.valid
        assert view.press_claimed(12.75, 13.0)

    def test_never_while_the_ruler_is_active(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtCore import QPointF

        window = self.make(qtbot, tmp_path)
        window.ruler_tool.set_active(True)
        view = window.sheet_view
        pos = view.from_sheet(QPointF(*self.MIDDLE_OF_FACE_2)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert not view.is_panning()
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert len(window.ruler_tool.ruler.points) == 1

    def test_dragging_a_point_does_not_pan(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtCore import QPointF

        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        pos = view.from_sheet(QPointF(11.5, 13.5)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        assert not view.is_panning()
        assert window.cut_tool.dragging
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=pos)


class TestShiftInTheWindow:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        window.activateWindow()
        qtbot.waitUntil(window.isActiveWindow)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def test_the_sheet_has_the_focus_from_the_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.sheet_view.hasFocus()

    def test_hover_shows_what_the_straight_segment_ends_on(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        h = self.hitbox(window)
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.7, 13.5)
        in_a_cut = 12 - h, 13.2  # in the hitbox of a cut, while the straight segment goes down from the last point
        view.mouse_moved.emit(*in_a_cut)
        assert window.cut_hover.hovered() is not None
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        assert window.cut_hover.hovered() is None
        view.mouse_moved.emit(12 - h, 13.45)  # now it goes right, into that cut
        assert window.cut_hover.hovered() is not None
        qtbot.keyRelease(view, Qt.Key.Key_Shift)
        view.mouse_moved.emit(*in_a_cut)
        assert window.cut_hover.hovered() is not None

    def test_undo_is_back_after_a_shift_click(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtCore import QPointF

        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        h = self.hitbox(window)
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        pos = view.from_sheet(QPointF(11.5, 13.5)).toPoint()
        modifier = Qt.KeyboardModifier.ShiftModifier
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, modifier, pos)
        assert not window.undo_action.isEnabled()  # it may still become a drag
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, modifier, pos)
        assert window.undo_action.isEnabled()
        window.undo_action.trigger()
        assert window.editor.cut_line is not None and len(window.editor.cut_line.points) == 3


class TestProjects:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def close_line(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def rearrange(self, window: MainWindow) -> None:
        self.close_line(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))

    def shown(self, window: MainWindow) -> tuple[object, ...]:
        item = window.sheet_view.net_item()
        assert item is not None
        labels = item.labels() or {}
        return (
            window.editor.state,
            sorted(str(v.position) for v in window.net.vertices),
            [p.position for p in window.cut_tool.item.points()],
            len(item.glue()),
            len(item.overlapping()),
            window.bounding.label.text(),
            window.cut_tool.approve_button.position(),
            window.approve_action.isEnabled(),
            window.undo_action.isEnabled(),
            window.redo_action.isEnabled(),
            sorted((str(v.position), str(name)) for v, name in labels.items()),
            [(p, name) for p, name in window.cut_tool.item.labels()],
        )

    def reopened(self, qtbot: QtBot, tmp_path: Path, window: MainWindow) -> MainWindow:
        """The project in another window, as after a restart."""
        path = tmp_path / "cube.cubenet"
        assert window.save_project_to(path)
        other = self.make(qtbot, tmp_path)
        assert other.open_project_from(path)
        return other

    def test_every_state_comes_back_as_it_was_shown(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        view.left_pressed.emit(11.5, 14 - h)
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        view.left_pressed.emit(11.75, 10 + h)
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        window.approve_action.trigger()
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        window.undo_action.trigger()
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)

    def test_undo_and_redo_work_after_reopening(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearrange(window)
        window.approve_action.trigger()
        other = self.reopened(qtbot, tmp_path, window)
        other.undo_action.trigger()
        window.undo_action.trigger()
        assert self.shown(other) == self.shown(window)
        for _ in range(2):
            other.redo_action.trigger()
            window.redo_action.trigger()
            assert self.shown(other) == self.shown(window)
        assert other.editor.state.value == "default"

    def test_the_tools_work_on_the_opened_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearrange(window)
        other = self.reopened(qtbot, tmp_path, window)
        other.approve_action.trigger()
        assert other.editor.state.value == "default"
        assert other.net is other.editor.net
        h = self.hitbox(other)
        other.sheet_view.mouse_moved.emit(10 + h, 12.5)
        assert other.cut_hover.hovered() is not None
        other.sheet_view.left_pressed.emit(10 + h, 12.5)
        assert other.editor.state.value == "cutting"

    def test_an_overlap_comes_back(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11 + h, 11.5)
        view.left_pressed.emit(12.75, 13 - h)
        other = self.reopened(qtbot, tmp_path, window)
        item = other.sheet_view.net_item()
        assert item is not None and item.overlapping()
        assert not other.cut_tool.approve_button.enabled()
        other.sheet_view.left_pressed.emit(12.75, 13.0)  # the "x" undoes it, for good
        other.sheet_view.left_released.emit(12.75, 13.0)
        assert other.editor.state.value == "cut_editing"
        assert not other.redo_action.isEnabled()

    def test_settings_come_back_and_are_used(self, qtbot: QtBot, tmp_path: Path) -> None:
        from fractions import Fraction

        from cube_net.core.project_settings import ProjectSettings

        window = self.make(qtbot, tmp_path)
        window.project_settings = ProjectSettings(Fraction(5))
        other = self.reopened(qtbot, tmp_path, window)
        assert other.project_settings.area_threshold == 5

    def test_a_drag_in_progress_is_forgotten(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        path = tmp_path / "cube.cubenet"
        assert window.save_project_to(path)
        window.sheet_view.left_pressed.emit(11.5, 13.5)
        window.sheet_view.mouse_moved.emit(11.7, 13.7)
        assert window.cut_tool.dragging
        assert window.open_project_from(path)
        assert not window.cut_tool.dragging
        assert window.undo_action.isEnabled()
        window.sheet_view.left_released.emit(11.7, 13.7)  # nothing happens
        line = window.editor.cut_line
        assert line is not None and float(line.points[1].position.x) == 11.5

    def test_the_title_tells_the_file(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert "cube.cubenet" not in window.windowTitle()
        window.save_project_to(tmp_path / "cube.cubenet")
        assert window.windowTitle().startswith("[*]cube.cubenet")
        assert window.project_path == tmp_path / "cube.cubenet"

    def test_opening_a_bad_file_tells_and_changes_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        before = self.shown(window)
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _parent, _title, text, **_: told.append(text))
        bad = tmp_path / "bad.cubenet"
        bad.write_text("Hello!")
        assert not window.open_project_from(bad)
        assert len(told) == 1 and "bad.cubenet" in told[0]
        assert self.shown(window) == before
        assert window.project_path is None

    def test_saving_to_a_bad_place_tells_and_changes_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _parent, _title, text, **_: told.append(text))
        assert not window.save_project_to(tmp_path / "nowhere" / "cube.cubenet")
        assert len(told) == 1
        assert window.project_path is None

    def test_file_menu_comes_first(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        menu_bar = window.menuBar()
        assert menu_bar is not None
        assert menu_bar.actions()[0].text() == "&File"
        assert window.open_action.shortcut().toString() == "Ctrl+O"
        assert window.save_as_action.shortcut().toString() == "Ctrl+Shift+S"

    def test_save_as_adds_the_ending(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PyQt6.QtWidgets import QFileDialog

        window = self.make(qtbot, tmp_path)
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: (str(tmp_path / "cube"), ""))
        window.save_as_action.trigger()
        assert (tmp_path / "cube.cubenet").exists()

    def test_cancelled_dialogs_do_nothing(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PyQt6.QtWidgets import QFileDialog

        window = self.make(qtbot, tmp_path)
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: ("", ""))
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: ("", ""))
        window.save_as_action.trigger()
        window.open_action.trigger()
        assert window.project_path is None

    def test_open_through_the_menu(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PyQt6.QtWidgets import QFileDialog

        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        other = self.make(qtbot, tmp_path)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(path), ""))
        other.open_action.trigger()
        assert other.editor.state.value == "cut_editing"

    def test_recorded(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert lines[-1] == f"project saved {path}"
        window.open_project_from(path)
        lines = session_lines(window.recorder.log.path)
        assert f"project opened {path}" in lines
        assert f"state project {path}" in lines
        window.stop_recording("test over")


class TestUnsavedChanges:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        window.activateWindow()
        qtbot.waitUntil(window.isActiveWindow)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def start_line(self, window: MainWindow) -> None:
        window.sheet_view.left_pressed.emit(11.5, 14 - self.hitbox(window))

    def close_line(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def answer(self, monkeypatch: pytest.MonkeyPatch, *choices: object) -> list[str]:
        """Make the question answer this, and "don't save" after that (the window gets closed when the test ends);
        returns the list of the projects it was asked about."""
        from cube_net.ui.save_changes_dialog import SaveChoice

        remaining = list(choices)
        asked: list[str] = []

        def ask(_parent: object, name: str) -> object:
            asked.append(name)
            return remaining.pop(0) if remaining else SaveChoice.DISCARD

        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", ask)
        return asked

    def file_dialogs(self, monkeypatch: pytest.MonkeyPatch, save: str = "", open_: str = "") -> list[str]:
        """Make the file dialogs answer this; returns the list of the dialogs that were shown."""
        from PyQt6.QtWidgets import QFileDialog

        shown: list[str] = []

        def show_save(*_: object) -> tuple[str, str]:
            shown.append("save")
            return save, ""

        def show_open(*_: object) -> tuple[str, str]:
            shown.append("open")
            return open_, ""

        monkeypatch.setattr(QFileDialog, "getSaveFileName", show_save)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", show_open)
        return shown

    # --- what counts as a change -------------------------------------------------------------------------------------

    def test_a_new_window_has_none(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.is_dirty
        assert not window.isWindowModified()

    def test_every_action_is_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        view = window.sheet_view
        h = self.hitbox(window)

        def check(action: object) -> None:
            assert window.save_project_to(path)
            assert not window.isWindowModified()
            assert callable(action)
            action()
            assert window.is_dirty
            assert window.isWindowModified()

        check(lambda: view.left_pressed.emit(11.5, 14 - h))  # the first point
        check(lambda: view.left_pressed.emit(11.5, 13.5))  # a point
        check(lambda: view.left_pressed.emit(12 - h, 13.5))  # the last point

        def move() -> None:
            view.left_pressed.emit(11.5, 13.5)
            view.mouse_moved.emit(11.6, 13.6)
            view.left_released.emit(11.6, 13.6)

        check(move)
        check(window.undo_action.trigger)
        check(window.redo_action.trigger)
        check(lambda: view.left_pressed.emit(11.75, 10 + h))  # rearranged
        check(window.approve_action.trigger)

    def test_what_changes_nothing_is_not_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.save_project_to(tmp_path / "cube.cubenet")
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)  # pressed and released without moving
        view.left_released.emit(11.5, 13.5)
        assert not window.is_dirty
        h = self.hitbox(window)
        view.left_pressed.emit(10.5, 12 + h)  # a useless cut flashes
        assert not window.is_dirty
        view.mouse_moved.emit(11.5, 12.5)
        assert not window.isWindowModified()
        window.ruler_tool.set_active(True)
        view.left_pressed.emit(7.0, 7.0)
        assert not window.is_dirty

    def test_undoing_back_to_the_saved_state_is_still_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        """The history is saved too, and it's not what it was."""
        window = self.make(qtbot, tmp_path)
        self.start_line(window)
        window.save_project_to(tmp_path / "cube.cubenet")
        window.sheet_view.left_pressed.emit(11.5, 13.5)
        window.undo_action.trigger()
        assert window.isWindowModified()

    def test_the_title_shows_the_name(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.windowTitle().startswith("[*]Untitled")
        window.save_project_to(tmp_path / "cube.cubenet")
        assert window.windowTitle().startswith("[*]cube.cubenet")

    # --- Save --------------------------------------------------------------------------------------------------------

    def test_save_without_a_file_asks_for_a_name(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        shown = self.file_dialogs(monkeypatch, save=str(tmp_path / "cube"))
        self.start_line(window)
        window.save_action.trigger()
        assert shown == ["save"]
        assert window.project_path == tmp_path / "cube.cubenet"
        assert not window.is_dirty

    def test_save_with_a_file_just_saves(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.core.project import load_project

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        shown = self.file_dialogs(monkeypatch)
        self.start_line(window)
        window.save_action.trigger()
        assert shown == []
        assert not window.is_dirty
        assert load_project(path).state.points is not None

    def test_ctrl_s(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.save_project_to(tmp_path / "cube.cubenet")
        self.start_line(window)
        qtbot.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
        assert not window.is_dirty

    def test_save_cancelled_changes_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        self.file_dialogs(monkeypatch)
        self.start_line(window)
        window.save_action.trigger()
        assert window.is_dirty
        assert window.project_path is None

    def test_save_as_moves_to_the_new_file(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        window = self.make(qtbot, tmp_path)
        window.save_project_to(tmp_path / "a.cubenet")
        self.file_dialogs(monkeypatch, save=str(tmp_path / "b.cubenet"))
        self.start_line(window)
        window.save_as_action.trigger()
        assert window.project_path == tmp_path / "b.cubenet"
        assert not window.is_dirty

    def test_a_failed_save_leaves_the_changes_unsaved(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda *_, **__: None)
        self.start_line(window)
        assert not window.save_project_to(tmp_path / "nowhere" / "cube.cubenet")
        assert window.is_dirty
        assert window.isWindowModified()

    # --- New ---------------------------------------------------------------------------------------------------------

    def test_new_with_nothing_to_lose_does_not_ask(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        asked = self.answer(monkeypatch)
        window.new_action.trigger()
        assert asked == []

    def test_new_starts_all_over(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from fractions import Fraction

        from cube_net.core.project_settings import DEFAULT_AREA_THRESHOLD, ProjectSettings

        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))
        window.approve_action.trigger()
        window.project_settings = ProjectSettings(Fraction(5))
        window.save_project_to(tmp_path / "cube.cubenet")
        names_before = window.point_labels.saved()[0]
        assert names_before
        window.new_action.trigger()
        assert window.editor.state.value == "default"
        assert window.editor.approved_cuts == 0
        assert window.net is window.editor.net
        assert window.bounding.label.text() == "Area\n12.000"
        assert window.cut_tool.item.points() == ()
        assert not window.undo_action.isEnabled() and not window.redo_action.isEnabled()
        assert window.project_path is None
        assert window.windowTitle().startswith("[*]Untitled")
        assert not window.is_dirty and not window.isWindowModified()
        assert window.project_settings.area_threshold == DEFAULT_AREA_THRESHOLD
        assert window.point_labels.saved()[0] == {}

    def test_new_cancel(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        asked = self.answer(monkeypatch, SaveChoice.CANCEL)
        self.close_line(window)
        window.new_action.trigger()
        assert asked == ["Untitled"]
        assert window.editor.state.value == "cut_editing"
        assert window.is_dirty

    def test_new_discard(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        saved = path.read_bytes()
        asked = self.answer(monkeypatch, SaveChoice.DISCARD)
        self.close_line(window)
        window.new_action.trigger()
        assert asked == ["cube.cubenet"]
        assert window.editor.state.value == "default"
        assert path.read_bytes() == saved

    def test_new_save(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.core.project import load_project
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        self.answer(monkeypatch, SaveChoice.SAVE)
        self.close_line(window)
        window.new_action.trigger()
        assert window.editor.state.value == "default"
        assert window.project_path is None
        assert load_project(path).state.points is not None

    def test_new_save_but_the_name_is_cancelled(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.SAVE)
        shown = self.file_dialogs(monkeypatch)
        self.close_line(window)
        window.new_action.trigger()
        assert shown == ["save"]
        assert window.editor.state.value == "cut_editing"
        assert window.is_dirty

    def test_new_save_but_saving_fails(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda *_, **__: None)
        self.answer(monkeypatch, SaveChoice.SAVE)
        self.file_dialogs(monkeypatch, save=str(tmp_path / "nowhere" / "cube.cubenet"))
        self.close_line(window)
        window.new_action.trigger()
        assert window.editor.state.value == "cut_editing"

    def test_the_tools_work_after_new(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.new_action.trigger()
        self.close_line(window)
        assert window.editor.state.value == "cut_editing"
        window.undo_action.trigger()
        assert window.editor.state.value == "cutting"

    # --- Open --------------------------------------------------------------------------------------------------------

    def test_open_cancel_shows_no_file_dialog(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.CANCEL)
        shown = self.file_dialogs(monkeypatch)
        self.close_line(window)
        window.open_action.trigger()
        assert shown == []
        assert window.editor.state.value == "cut_editing"

    def test_open_discard(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        self.answer(monkeypatch, SaveChoice.DISCARD)
        self.file_dialogs(monkeypatch, open_=str(path))
        self.close_line(window)
        window.open_action.trigger()
        assert window.editor.state.value == "default"
        assert not window.is_dirty

    def test_open_dialog_cancelled_keeps_the_changes(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.DISCARD)
        self.file_dialogs(monkeypatch)
        self.close_line(window)
        window.open_action.trigger()
        assert window.editor.state.value == "cut_editing"
        assert window.is_dirty

    def test_an_opened_project_has_no_changes(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        window.open_project_from(path)
        assert not window.is_dirty and not window.isWindowModified()
        window.undo_action.trigger()
        assert window.is_dirty and window.isWindowModified()

    # --- Quit --------------------------------------------------------------------------------------------------------

    def test_quit_with_nothing_to_lose_does_not_ask(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        asked = self.answer(monkeypatch)
        window.quit_action.trigger()
        assert asked == []
        assert not window.isVisible()

    def test_quit_cancel_stays(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.CANCEL)
        self.close_line(window)
        window.quit_action.trigger()
        assert window.isVisible()
        assert window.is_dirty

    def test_quit_discard_goes(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.DISCARD)
        self.close_line(window)
        window.quit_action.trigger()
        assert not window.isVisible()

    def test_quit_save_goes(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.core.project import load_project
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        self.answer(monkeypatch, SaveChoice.SAVE)
        self.close_line(window)
        window.quit_action.trigger()
        assert not window.isVisible()
        assert load_project(path).state.points is not None

    def test_quit_save_cancelled_stays(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.SAVE)
        self.file_dialogs(monkeypatch)
        self.close_line(window)
        window.quit_action.trigger()
        assert window.isVisible()

    def test_closing_the_window_is_quitting(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        asked = self.answer(monkeypatch, SaveChoice.CANCEL, SaveChoice.DISCARD)
        self.close_line(window)
        assert not window.close()
        assert window.isVisible()
        assert window.close()
        assert asked == ["Untitled", "Untitled"]

    def test_closing_during_a_drag_forgets_it(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.CANCEL)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)
        view.mouse_moved.emit(11.7, 13.7)
        assert window.cut_tool.dragging
        assert not window.close()
        assert not window.cut_tool.dragging
        assert window.undo_action.isEnabled()
        line = window.editor.cut_line
        assert line is not None and float(line.points[1].position.x) == 11.5
        assert float(window.cut_tool.item.points()[1].position.x) == 11.5

    # --- the rest ----------------------------------------------------------------------------------------------------

    def test_not_while_dragging(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        actions = (
            window.new_action,
            window.open_action,
            window.save_action,
            window.save_as_action,
            window.quit_action,
        )
        assert all(action.isEnabled() for action in actions)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)
        assert not any(action.isEnabled() for action in actions)
        view.left_released.emit(11.5, 13.5)
        assert all(action.isEnabled() for action in actions)

    def test_shortcuts_and_order(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.new_action.shortcut().toString() == "Ctrl+N"
        assert window.save_action.shortcut().toString() == "Ctrl+S"
        assert window.quit_action.shortcut().toString() == "Ctrl+Q"
        menu = window.new_action.associatedObjects()[0]
        texts = [a.text() for a in menu.actions() if not a.isSeparator()]  # type: ignore[union-attr]
        assert texts == ["&New", "&Open...", "&Save", "Save &As...", "&Quit"]

    def test_recorded(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        self.answer(monkeypatch, SaveChoice.DISCARD)
        self.close_line(window)
        window.new_action.trigger()
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert "project unsaved changes discard" in lines
        assert "project new" in lines
        assert "state project untitled" in lines[lines.index("project new") :]
        window.stop_recording("test over")


class TestReopeningAtStart:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        """A window as after a restart: the settings are in the same place, the project is the new one for now."""
        settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
        settings.record_session = record
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def worked_on(self, qtbot: QtBot, tmp_path: Path, name: str = "cube.cubenet") -> Path:
        """A session that ended with this file saved: a closed line in it."""
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path)
        h = net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        path = tmp_path / name
        assert window.save_project_to(path)
        return path

    def answers(self, monkeypatch: pytest.MonkeyPatch, *choices: object) -> list[str]:
        """Make the question answer this; returns what it was told."""
        remaining = list(choices)
        told: list[str] = []

        def ask(_parent: object, message: str) -> object:
            told.append(message)
            return remaining.pop(0)

        monkeypatch.setattr("cube_net.ui.main_window.ask_after_load_failed", ask)
        return told

    def test_the_first_time_a_new_project(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        told = self.answers(monkeypatch)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert told == []
        assert window.editor.state.value == "default"
        assert window.project_path is None
        assert not window.is_dirty

    def test_back_to_what_was_saved(self, qtbot: QtBot, tmp_path: Path) -> None:
        path = self.worked_on(qtbot, tmp_path)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == path
        assert window.windowTitle().startswith("[*]cube.cubenet")
        assert window.editor.state.value == "cut_editing"
        assert not window.is_dirty
        window.undo_action.trigger()
        assert window.editor.state.value == "cutting"

    def test_a_window_alone_opens_nothing(self, qtbot: QtBot, tmp_path: Path) -> None:
        self.worked_on(qtbot, tmp_path)
        window = self.make(qtbot, tmp_path)
        assert window.editor.state.value == "default"

    def test_the_last_one_saved_wins(self, qtbot: QtBot, tmp_path: Path) -> None:
        self.worked_on(qtbot, tmp_path, "a.cubenet")
        b = self.worked_on(qtbot, tmp_path, "b.cubenet")
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == b

    def test_the_last_one_opened_counts_too(self, qtbot: QtBot, tmp_path: Path) -> None:
        a = self.worked_on(qtbot, tmp_path, "a.cubenet")
        self.worked_on(qtbot, tmp_path, "b.cubenet")
        self.make(qtbot, tmp_path).open_project_from(a)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == a

    def test_a_new_project_changes_nothing_until_it_is_saved(self, qtbot: QtBot, tmp_path: Path) -> None:
        path = self.worked_on(qtbot, tmp_path)
        self.make(qtbot, tmp_path).start_new_project()
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == path

    def test_a_file_that_failed_to_open_is_not_remembered(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        path = self.worked_on(qtbot, tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda *_, **__: None)
        window = self.make(qtbot, tmp_path)
        assert not window.open_project_from(tmp_path / "missing.cubenet")
        assert window.settings.last_project == path

    def test_a_failed_save_is_not_remembered(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        path = self.worked_on(qtbot, tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda *_, **__: None)
        window = self.make(qtbot, tmp_path)
        assert not window.save_project_to(tmp_path / "nowhere" / "cube.cubenet")
        assert window.settings.last_project == path

    def test_it_is_gone_the_user_is_told_and_gets_a_new_project(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        path = self.worked_on(qtbot, tmp_path)
        path.unlink()
        told = self.answers(monkeypatch, AfterLoadFailed.NEW_PROJECT)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert len(told) == 1 and "cube.cubenet" in told[0]
        assert window.editor.state.value == "default"
        assert window.project_path is None
        assert not window.is_dirty

    def test_it_is_damaged_the_user_is_told_why(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        path = self.worked_on(qtbot, tmp_path)
        path.write_text("Hello!")
        told = self.answers(monkeypatch, AfterLoadFailed.NEW_PROJECT)
        self.make(qtbot, tmp_path).reopen_last_project()
        assert "isn't a Cube Net project" in told[0]

    def test_it_is_asked_only_once(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        self.worked_on(qtbot, tmp_path).unlink()
        told = self.answers(monkeypatch, AfterLoadFailed.NEW_PROJECT)
        self.make(qtbot, tmp_path).reopen_last_project()
        self.make(qtbot, tmp_path).reopen_last_project()
        assert len(told) == 1

    def test_open_another_instead(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PyQt6.QtWidgets import QFileDialog

        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        other = self.worked_on(qtbot, tmp_path, "other.cubenet")
        self.worked_on(qtbot, tmp_path).unlink()
        self.answers(monkeypatch, AfterLoadFailed.OPEN_ANOTHER)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(other), ""))
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == other
        assert window.editor.state.value == "cut_editing"
        assert window.settings.last_project == other

    def test_open_another_dialog_cancelled_leaves_a_new_project(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PyQt6.QtWidgets import QFileDialog

        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        self.worked_on(qtbot, tmp_path).unlink()
        told = self.answers(monkeypatch, AfterLoadFailed.OPEN_ANOTHER)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: ("", ""))
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert len(told) == 1
        assert window.project_path is None
        assert window.settings.last_project is None

    def test_the_other_one_fails_too_asks_again_with_the_new_reason(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PyQt6.QtWidgets import QFileDialog

        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        self.worked_on(qtbot, tmp_path).unlink()
        bad = tmp_path / "bad.cubenet"
        bad.write_text("Hello!")
        told = self.answers(monkeypatch, AfterLoadFailed.OPEN_ANOTHER, AfterLoadFailed.NEW_PROJECT)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(bad), ""))
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert len(told) == 2
        assert "cube.cubenet" in told[0] and "bad.cubenet" in told[1]
        assert window.project_path is None

    def test_recorded(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        path = self.worked_on(qtbot, tmp_path)
        window = self.make(qtbot, tmp_path, record=True)
        window.reopen_last_project()
        assert window.recorder is not None
        assert f"project opened {path}" in session_lines(window.recorder.log.path)
        window.stop_recording("test over")
        path.unlink()
        self.answers(monkeypatch, AfterLoadFailed.NEW_PROJECT)
        other = self.make(qtbot, tmp_path, record=True)
        other.settings.last_project = path
        other.reopen_last_project()
        assert other.recorder is not None
        assert f"project reopening failed {path}" in session_lines(other.recorder.log.path)
        other.stop_recording("test over")


class TestTargetArea:
    """The project's target area, edited on the instruments panel."""

    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def enter(self, qtbot: QtBot, window: MainWindow, text: str) -> None:
        """Type it into the field and press Enter, as the user does."""
        line = window.bounding.target.lineEdit()
        assert line is not None
        line.selectAll()
        qtbot.keyClicks(line, text)
        qtbot.keyClick(line, Qt.Key.Key_Return)

    def test_it_shows_the_project_s_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.bounding.target.text() == "7.100"
        assert window.bounding.target_label.text() == "Target area"

    def test_its_range_and_decimals(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        field = window.bounding.target
        assert (field.minimum(), field.maximum(), field.decimals()) == (0, 20, 3)

    def test_an_entered_value_is_used_at_once(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.bounding.success
        self.enter(qtbot, window, "12.5")  # the cross has 12.000
        assert window.project_settings.area_threshold == F(25, 2)
        assert window.bounding.success
        self.enter(qtbot, window, "6.789")
        assert window.project_settings.area_threshold == F(6789, 1000)
        assert not window.bounding.success

    def test_digits_count_only_once_entered(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        line = window.bounding.target.lineEdit()
        assert line is not None
        line.selectAll()
        qtbot.keyClicks(line, "13")
        assert window.project_settings.area_threshold == F(71, 10)

    def test_out_of_range_cannot_get_through(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.enter(qtbot, window, "99")
        assert 0 <= window.project_settings.area_threshold <= 20

    def test_a_change_is_an_unsaved_change(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.enter(qtbot, window, "5")
        assert window.is_dirty and window.isWindowModified()
        assert window.save_project_to(tmp_path / "cube.cubenet")
        assert not window.is_dirty
        self.enter(qtbot, window, "6")
        self.enter(qtbot, window, "5")
        assert not window.is_dirty  # back to what was saved

    def test_saved_with_the_project_and_shown_when_opened(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.enter(qtbot, window, "5")
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        other = self.make(qtbot, tmp_path)
        other.open_project_from(path)
        assert other.project_settings.area_threshold == 5
        assert other.bounding.target.text() == "5.000"
        assert not other.is_dirty
        other.start_new_project()
        assert other.bounding.target.text() == "7.100"
        assert not other.is_dirty

    def test_undo_does_not_touch_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.sheet_view.left_pressed.emit(10.0, 13.0)
        self.enter(qtbot, window, "5")
        window.undo_action.trigger()
        assert window.project_settings.area_threshold == 5

    def test_no_more_project_settings_in_the_file_menu(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not hasattr(window, "project_settings_action")

    def test_recorded(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        assert window.recorder is not None
        assert "state threshold 7.100" in session_lines(window.recorder.log.path)
        self.enter(qtbot, window, "5")
        assert session_lines(window.recorder.log.path)[-1] == "project threshold 5.000"
        window.stop_recording("test over")


# x_1-B_1, on the top of face 1 (for the corner cut).
TOP_PART = frozenset({Vec(F(23, 2), 14), Vec(12, 14)})


class TestCounterpartBlinks:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def close_line(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def blinking(self, window: MainWindow) -> set[Vec] | None:
        cut = window.counterpart_blink.cut()
        return None if cut is None else {cut.origin.position, cut.destination.position}

    def hover_bottom(self, window: MainWindow) -> None:
        """x_2-B_3, on the bottom of face 5: it can be chosen, and its counterpart is x_1-B_1 on the top of face 1."""
        window.sheet_view.mouse_moved.emit(11.75, 10 + self.hitbox(window))

    def test_the_exact_part_that_is_the_counterpart(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        assert self.blinking(window) == TOP_PART
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is window.counterpart_blink.cut()

    def test_it_is_a_cut_that_gets_painted(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        cut = window.counterpart_blink.cut()
        assert cut is not None
        assert cut in window.editor.split().net.boundary_edges()

    def test_it_really_blinks(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        item = window.sheet_view.net_item()
        assert item is not None
        qtbot.waitUntil(lambda: item.hidden_cut() is None, timeout=2000)
        qtbot.waitUntil(lambda: item.hidden_cut() is not None, timeout=2000)

    def test_not_for_a_useless_cut(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(10.5, 12 + self.hitbox(window))  # E_2-H_1: thin and black
        item = window.sheet_view.net_item()
        assert item is not None and item.divided() is not None
        assert window.cut_hover.hovered() is not None
        assert self.blinking(window) is None
        assert item.hidden_cut() is None

    def test_not_for_the_new_line(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(11.5 + self.hitbox(window), 13.8)
        assert self.blinking(window) is None

    def test_not_on_a_vertex(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.mouse_moved.emit(12.0, 10.0)
        assert self.blinking(window) is None

    @pytest.mark.parametrize("state", ["default", "cutting"])
    def test_not_in_other_states(self, qtbot: QtBot, tmp_path: Path, state: str) -> None:
        window = self.make(qtbot, tmp_path)
        if state == "cutting":
            window.sheet_view.left_pressed.emit(11.5, 14 - self.hitbox(window))
        self.hover_bottom(window)
        assert window.cut_hover.hovered() is not None
        assert self.blinking(window) is None

    def test_not_while_approving(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))
        assert window.editor.state.value == "cut_approving"
        assert self.blinking(window) is None
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is None

    def test_stops_when_the_mouse_moves_away(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.sheet_view.mouse_moved.emit(11.5, 12.5)
        assert self.blinking(window) is None
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is None

    def test_stops_when_the_mouse_leaves_the_view(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.sheet_view.mouse_left.emit()
        assert self.blinking(window) is None

    def test_follows_the_mouse_to_another_cut(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        assert self.blinking(window) == TOP_PART
        window.sheet_view.mouse_moved.emit(11.75, 14 - self.hitbox(window))  # x_1-B_1: now the other way round
        assert self.blinking(window) == {Vec(F(23, 2), 10), Vec(12, 10)}
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is window.counterpart_blink.cut()

    def test_not_while_dragging(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)
        assert self.blinking(window) is None
        self.hover_bottom(window)
        assert self.blinking(window) is None
        view.left_released.emit(11.75, 10 + self.hitbox(window))
        view.mouse_moved.emit(7.0, 7.0)
        self.hover_bottom(window)
        assert self.blinking(window) is not None

    def test_not_while_the_ruler_is_active(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.ruler_action.trigger()
        assert self.blinking(window) is None
        window.ruler_action.trigger()
        assert self.blinking(window) is not None

    def test_undo_stops_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        self.hover_bottom(window)
        window.undo_action.trigger()
        assert window.editor.state.value == "cutting"
        assert self.blinking(window) is None
        item = window.sheet_view.net_item()
        assert item is not None and item.hidden_cut() is None

    def test_the_counterpart_follows_the_line(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Moving the end of the line changes where the parts begin."""
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14.0)
        view.mouse_moved.emit(11.25, 14.0)
        view.left_released.emit(11.25, 14.0)
        view.mouse_moved.emit(7.0, 7.0)
        view.mouse_moved.emit(11.75, 10 + self.hitbox(window))
        assert self.blinking(window) == {Vec(F(45, 4), 14), Vec(12, 14)}


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
        from fractions import Fraction

        from cube_net.core.project_settings import ProjectSettings

        window = self.make(qtbot, tmp_path, record=False)
        window.project_settings = ProjectSettings(Fraction(5))
        window.logging_action.trigger()
        assert project_from_bytes(self.snapshots(window)[-1]).settings == ProjectSettings(Fraction(5))
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
        window = MainWindow(settings=settings, session_dir=tmp_path)
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
        assert "state project untitled" in lines
        assert "state net default" in lines
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
        assert len(self.snapshots(window)) == 1
        window.stop_recording("test over")


class TestSettingsPanel:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.resize(1200, 800)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_the_menu_bar(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        menu_bar = window.menuBar()
        assert menu_bar is not None
        assert [a.text() for a in menu_bar.actions()][:3] == ["&File", "&Edit", "&Settings"]

    def test_it_opens_and_closes(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        panel = window.settings_panel
        assert not panel.isVisible()
        window.settings_action.trigger()
        assert panel.isVisible()
        window.settings_action.trigger()
        assert not panel.isVisible()

    def test_the_tabs(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        tabs = window.settings_panel.tabs
        assert [tabs.tabText(i) for i in range(tabs.count())] == ["Preferences", "Style"]

    def test_over_the_right_of_the_sheet_and_the_sheet_stays(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtCore import QPointF

        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        before = view.from_sheet(QPointF(11, 12))
        window.settings_action.trigger()
        panel = window.settings_panel
        assert panel.geometry().right() == view.geometry().right()
        assert panel.geometry().top() == view.geometry().top()
        assert panel.geometry().height() == view.geometry().height()
        screen = window.screen()
        assert screen is not None
        assert panel.width() <= screen.geometry().width() / 3
        assert view.from_sheet(QPointF(11, 12)) == before

    def test_it_follows_the_window(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.resize(1000, 700)
        qtbot.waitUntil(lambda: window.settings_panel.geometry().right() == window.sheet_view.geometry().right())
        assert window.settings_panel.height() == window.sheet_view.height()

    def test_the_sheet_works_while_it_is_open(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.sheet_view.left_pressed.emit(10.0, 13.0)
        assert window.editor.state.value == "cutting"

    def test_preferences_switches_are_the_same_as_before(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        tab = window.settings_panel.preferences
        assert tab.show_labels.text() == "Show vertex labels"
        assert tab.auto_log.text() == "Auto-start logging"
        assert tab.show_labels.isChecked() == window.settings.show_vertex_labels
        tab.show_labels.setChecked(False)
        assert not window.show_labels_action.isChecked()
        assert window.settings.show_vertex_labels is False
        item = window.sheet_view.net_item()
        assert item is not None and item.labels() is None
        window.show_labels_action.setChecked(True)
        assert tab.show_labels.isChecked()

    def test_auto_log_only_decides_about_the_next_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        tab = window.settings_panel.preferences
        assert tab.auto_log.text() == "Auto-start logging"
        assert window.recorder is None and not tab.auto_log.isChecked()
        tab.auto_log.setChecked(True)
        assert window.recorder is None  # it doesn't start now
        assert window.settings.record_session is True
        window.logging_action.trigger()
        tab.auto_log.setChecked(False)
        assert window.recorder is not None  # nor does it stop
        assert window.settings.record_session is False
        window.stop_recording("test over")

    def test_auto_log_starts_it_at_launch(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_panel.preferences.auto_log.setChecked(True)
        other = MainWindow(settings=window.settings, session_dir=tmp_path)
        qtbot.addWidget(other)
        assert other.recorder is not None
        other.stop_recording("test over")

    def test_max_zoom(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtCore import QPointF

        window = self.make(qtbot, tmp_path, record=True)
        view = window.sheet_view
        view.zoom_by(1e6, QPointF(100, 100))
        assert view.scale_factor() == pytest.approx(1000)
        window.settings_panel.preferences.max_zoom.setValue(700)
        assert window.settings.max_zoom == 700
        assert view.scale_factor() == pytest.approx(700)
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1] == "settings max_zoom 700"
        assert not window.is_dirty  # not part of the project
        window.stop_recording("test over")

    def test_the_max_zoom_setting_is_used_from_the_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        settings = settings_in(tmp_path, record=False)
        settings.max_zoom = 3000
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        assert window.sheet_view.zoom_limits()[1] == 3000
        assert window.settings_panel.preferences.max_zoom.value() == 3000

    def test_the_start_zoom_is_as_far_out_as_it_goes(self, qtbot: QtBot, tmp_path: Path) -> None:
        """The default net takes 50% of the screen height at the start, which is also the zoom-out limit."""
        window = self.make(qtbot, tmp_path)
        assert window.sheet_view.scale_factor() == pytest.approx(window.sheet_view.zoom_limits()[0])

    def test_the_rearranged_net_decides_how_far_out(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        before = view.zoom_limits()[0]
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)
        assert window.editor.state.value == "cut_approving"
        assert view.zoom_limits()[0] < before


class TestStyle:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_a_change_is_saved_and_used_at_once(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui import palette
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path, record=True)
        tab = window.settings_panel.style_tab
        tab.edge_width.setValue(8)
        assert net_style.EDGE_WIDTH_PX == 8
        assert net_style.CUT_HITBOX_PX == 12  # still 1.5 times as wide: a hovered cut is drawn this wide too
        assert window.settings.style.edge_width == 8
        tab.face_fields[0].edit.setText("")
        qtbot.keyClicks(tab.face_fields[0].edit, "123abc")
        assert palette.FACE_COLORS[1].name().upper() == "#123ABC"
        assert tab.face_swatches[0].color().name().upper() == "#123ABC"
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1].startswith("settings style faces=#123ABC/")
        assert not window.is_dirty
        window.stop_recording("test over")

    def test_it_comes_back_next_time(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path)
        window.settings_panel.style_tab.vertex_radius.setValue(15)
        window.close()
        net_style.set_sizes(5.0, 10.0, 10, 5, 10, 1.0)
        other = self.make(qtbot, tmp_path)
        assert net_style.VERTEX_RADIUS_PX == 15
        assert other.settings_panel.style_tab.vertex_radius.value() == 15

    def test_the_hitbox_follows_the_thickness(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path)
        window.settings_panel.style_tab.edge_width.setValue(15)
        h = net_style.CUT_HITBOX_PX * 0.9 / window.sheet_view.scale_factor()
        window.sheet_view.mouse_moved.emit(10 + h, 12.5)
        assert window.cut_hover.hovered() is not None

    def test_the_net_is_painted_anew(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        before = window.sheet_view.viewport().grab().toImage()
        window.settings_panel.style_tab.hatch_columns.setValue(3)
        qtbot.wait(20)
        after = window.sheet_view.viewport().grab().toImage()
        assert before != after

    def test_restore_default_after_yes(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.settings_panel import style_tab as tabs
        from cube_net.ui.style import DEFAULT_STYLE

        window = self.make(qtbot, tmp_path)
        tab = window.settings_panel.style_tab
        tab.hatch_columns.setValue(3)
        tab.edge_width.setValue(9)
        asked: list[str] = []
        monkeypatch.setattr("cube_net.ui.settings_panel.section.confirm_restore", lambda _p, name: asked.append(name))
        tab.sections[tabs.FACE_TILING].restore_button.click()
        assert asked == ["Faces tiling"]
        assert window.settings.style.hatch_columns == 3  # said no
        monkeypatch.setattr("cube_net.ui.settings_panel.section.confirm_restore", lambda *_: True)
        tab.sections[tabs.FACE_TILING].restore_button.click()
        assert window.settings.style.hatch_columns == DEFAULT_STYLE.hatch_columns
        assert tab.hatch_columns.value() == DEFAULT_STYLE.hatch_columns
        assert window.settings.style.edge_width == 9  # only that section


class TestBlinkSetting:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def succeed(self, window: MainWindow) -> None:
        window.bounding.target.setValue(13)  # the cross has 12.000

    def test_on_by_default(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.settings_panel.preferences.blink.isChecked()
        self.succeed(window)
        assert window.bounding.blinking

    def test_off_means_steadily_green(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.succeed(window)
        window.settings_panel.preferences.blink.setChecked(False)
        assert not window.bounding.blinking and window.bounding.success
        assert window.settings.blink_on_success is False
        window.save_project_to(tmp_path / "cube.cubenet")
        window.settings_panel.preferences.blink.setChecked(True)
        assert not window.is_dirty  # an app setting, not the project's
        window.settings_panel.preferences.blink.setChecked(False)
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1] == "settings blink off"
        window.stop_recording("test over")

    def test_used_from_the_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        settings = settings_in(tmp_path, record=False)
        settings.blink_on_success = False
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        assert not window.settings_panel.preferences.blink.isChecked()
        self.succeed(window)
        assert not window.bounding.blinking and window.bounding.success


class TestLastSettingsTab:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
        settings.record_session = False
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_preferences_the_first_time(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        assert window.settings_panel.tab_name() == "preferences"

    def test_the_same_tab_when_opened_again(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.settings_panel.show_tab("Style")
        window.settings_action.trigger()
        window.settings_action.trigger()
        assert window.settings_panel.tab_name() == "style"

    def test_and_in_the_next_run(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.settings_panel.show_tab("Style")
        other = self.make(qtbot, tmp_path)
        other.settings_action.trigger()
        assert other.settings_panel.tab_name() == "style"


class TestSettingsPanelOpenAtStart:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
        settings.record_session = False
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        window.resize(1200, 800)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_open_the_first_time(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.settings_panel.isVisible()
        assert window.settings_action.isChecked()

    def test_left_open_starts_open_in_its_place(self, qtbot: QtBot, tmp_path: Path) -> None:
        first = self.make(qtbot, tmp_path)
        first.settings_action.trigger()
        first.settings_action.trigger()  # hidden and shown again: left open
        window = self.make(qtbot, tmp_path)
        assert window.settings_action.isChecked()
        assert window.settings_panel.isVisible()
        view = window.sheet_view.geometry()
        qtbot.waitUntil(lambda: window.settings_panel.geometry().right() == view.right())
        assert window.settings_panel.height() == window.sheet_view.height()

    def test_left_closed_starts_closed(self, qtbot: QtBot, tmp_path: Path) -> None:
        self.make(qtbot, tmp_path).settings_action.trigger()  # open the first time: this hides it
        assert not self.make(qtbot, tmp_path).settings_panel.isVisible()

    def test_the_hide_button_is_like_clicking_settings(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.settings_panel.hide_button.click()
        assert not window.settings_panel.isVisible()
        assert not window.settings_action.isChecked()
        assert window.settings.settings_open is False
        window.settings_action.trigger()
        assert window.settings_panel.isVisible()


def test_no_number_field_of_the_window_takes_the_wheel(qtbot: QtBot, tmp_path: Path) -> None:
    from PyQt6.QtCore import QPoint, QPointF
    from PyQt6.QtGui import QWheelEvent
    from PyQt6.QtWidgets import QAbstractSpinBox, QApplication

    window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.show()
    window.settings_action.trigger()
    qtbot.waitExposed(window)
    fields = window.findChildren(QAbstractSpinBox)
    assert window.bounding.target in fields and window.settings_panel.style_tab.edge_width in fields
    assert len(fields) == 8  # target area, max zoom, tiling (2), dashes, thickness, radius, grid
    before = [field.text() for field in fields]
    for field in fields:
        pos = QPointF(field.width() / 2, field.height() / 2)
        event = QWheelEvent(
            pos,
            field.mapToGlobal(pos),
            QPoint(0, 0),
            QPoint(0, 360),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.sendEvent(field, event)
    assert [field.text() for field in fields] == before
    assert not window.is_dirty


class TestHelpMenu:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        return window

    def test_after_settings_with_three_items(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        menu_bar = window.menuBar()
        assert menu_bar is not None
        assert [a.text() for a in menu_bar.actions()] == ["&File", "&Edit", "&Settings", "&Help"]
        help_menu = menu_bar.actions()[3].menu()
        assert help_menu is not None
        assert [a.text() for a in help_menu.actions()] == ["&About", "&Help", "Check for &updates"]

    def test_help_opens_one_window_with_f1(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.help_action.isEnabled()
        assert window.help_action.shortcut().toString() == "F1"
        window.help_action.trigger()
        first = window.help_window
        assert first is not None and first.isVisible()
        first.close()
        window.help_action.trigger()
        assert window.help_window is first and first.isVisible()  # the same one again

    def test_its_animations_follow_the_vertex_labels_setting(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.show_labels_action.setChecked(True)
        window.help_action.trigger()
        assert window.help_window is not None
        item = window.help_window.players[0].sheet.view.net_item()
        assert item is not None and item.labels() is not None
        window.show_labels_action.setChecked(False)
        assert item.labels() is None

    def test_its_animations_follow_the_style(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.help.help_window import HelpWindow
        from cube_net.ui.style import DEFAULT_STYLE

        window = self.make(qtbot, tmp_path)
        window.help_action.trigger()
        restyled: list[bool] = []
        monkeypatch.setattr(HelpWindow, "restyle", lambda self: restyled.append(True))
        window._on_style_changed(DEFAULT_STYLE)
        assert restyled == [True]

    def test_about_and_updates_open_their_windows(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.help.about_dialog import AboutDialog

        window = self.make(qtbot, tmp_path)
        opened: list[str] = []
        monkeypatch.setattr(AboutDialog, "exec", lambda self: opened.append(type(self).__name__) or 0)
        monkeypatch.setattr(MainWindow, "check_for_updates", lambda self, manual: opened.append(f"check {manual}"))
        window.about_action.trigger()
        window.updates_action.trigger()
        assert opened == ["AboutDialog", "check True"]


class TestLanguage:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
        settings.record_session = record
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def choose(self, window: MainWindow, name: str) -> None:
        box = window.settings_panel.preferences.language
        box.setCurrentIndex(box.findText(name))

    def texts(self, window: MainWindow) -> dict[str, str]:
        menu_bar = window.menuBar()
        assert menu_bar is not None
        prefs = window.settings_panel.preferences
        return {
            "menus": " ".join(a.text() for a in menu_bar.actions()),
            "open": window.open_action.text(),
            "ruler": window.ruler_action.text(),
            "target": window.bounding.target_label.text(),
            "area": window.bounding.label.text().split("\n")[0],
            "tabs": " ".join(window.settings_panel.tabs.tabText(i) for i in range(2)),
            "labels": prefs.show_labels.text(),
            "language": prefs.language_label.text(),
            "title": window.windowTitle(),
        }

    def test_first_in_preferences(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        prefs = window.settings_panel.preferences
        box = prefs.language
        assert [box.itemText(i) for i in range(box.count())] == ["English", "Русский"]
        assert prefs.language_label.text() == "Language"
        layout = prefs.layout()
        assert layout is not None
        first = layout.itemAt(0)
        assert first is not None and first.layout() is not None
        assert first.layout().indexOf(box) >= 0  # type: ignore[union-attr]

    def test_everything_changes_at_once(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        english = self.texts(window)
        self.choose(window, "Русский")
        russian = self.texts(window)
        assert russian == {
            "menus": "&Файл &Правка &Настройки &Справка",
            "open": "&Открыть...",
            "ruler": "Линейка",
            "target": "Цель",
            "area": "Площадь",
            "tabs": "Основные Оформление",
            "labels": "Показывать метки вершин",
            "language": "Язык",
            "title": "[*]Без имени — Cube Net",
        }
        self.choose(window, "English")
        assert self.texts(window) == english

    def test_the_list_does_not_move(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        box = window.settings_panel.preferences.language
        before = box.mapTo(window, box.rect().topLeft())
        self.choose(window, "Русский")
        qtbot.wait(20)
        assert box.mapTo(window, box.rect().topLeft()) == before

    def test_remembered_and_used_at_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.i18n import Language

        window = self.make(qtbot, tmp_path, record=True)
        self.choose(window, "Русский")
        assert window.settings.language is Language.RUSSIAN
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1] == "settings language ru"
        window.stop_recording("test over")
        other = self.make(qtbot, tmp_path)
        assert other.ruler_action.text() == "Линейка"
        assert other.settings_panel.preferences.language.currentText() == "Русский"

    def test_not_a_change_of_the_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.choose(window, "Русский")
        assert not window.is_dirty

    def test_the_wheel_does_not_change_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtCore import QPoint, QPointF
        from PyQt6.QtGui import QWheelEvent
        from PyQt6.QtWidgets import QApplication

        window = self.make(qtbot, tmp_path)
        box = window.settings_panel.preferences.language
        pos = QPointF(box.width() / 2, box.height() / 2)
        event = QWheelEvent(
            pos,
            box.mapToGlobal(pos),
            QPoint(0, 0),
            QPoint(0, -360),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.sendEvent(box, event)
        assert box.currentText() == "English"

    def test_error_messages_in_the_language(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        self.choose(window, "Русский")
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _parent, _title, text, **_: told.append(text))
        bad = tmp_path / "bad.cubenet"
        bad.write_text("Hello!")
        window.open_project_from(bad)
        assert told == [f"Не удалось открыть {bad}. Это не проект Cube Net."]


def test_the_settings_panel_takes_the_width_its_texts_need(qtbot: QtBot, tmp_path: Path) -> None:
    from cube_net.ui.i18n import TRANSLATIONS, Language

    window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.resize(1500, 900)
    window.show()
    qtbot.waitExposed(window)
    window.settings_action.trigger()
    placed: list[int] = []
    original = window.settings_panel.place_over
    window.settings_panel.place_over = lambda area, width: (placed.append(1), original(area, width))  # type: ignore[method-assign]
    TRANSLATIONS.set_language(Language.RUSSIAN)
    assert placed


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


class TestProjectFilesFromOutside:
    """A project file given at start (a double-click on Windows and Linux), or asked for while running (macOS)."""

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def saved(self, qtbot: QtBot, tmp_path: Path, name: str) -> Path:
        window = self.make(qtbot, tmp_path)
        path = tmp_path / name
        assert window.save_project_to(path)
        window.close()
        return path

    def test_at_start_instead_of_the_last_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        last = self.saved(qtbot, tmp_path, "last.cubenet")
        given = self.saved(qtbot, tmp_path, "given.cubenet")
        window = self.make(qtbot, tmp_path)
        window.settings.last_project = last
        window.open_project_at_start(given)
        assert window.project_path == given
        assert window.settings.last_project == given  # it's the one worked on now

    def test_at_start_a_broken_one_lets_the_user_decide(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        broken = tmp_path / "broken.cubenet"
        broken.write_bytes(b"not a project")
        asked: list[str] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_after_load_failed",
            lambda _parent, message: asked.append(message) or AfterLoadFailed.NEW_PROJECT,
        )
        window = self.make(qtbot, tmp_path)
        window.open_project_at_start(broken)
        assert len(asked) == 1 and window.project_path is None  # a new project

    def test_asked_for_while_running(self, qtbot: QtBot, tmp_path: Path) -> None:
        given = self.saved(qtbot, tmp_path, "given.cubenet")
        window = self.make(qtbot, tmp_path)
        window.open_project_requested(given)
        assert window.project_path == given

    def test_unsaved_changes_are_asked_about_first(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        given = self.saved(qtbot, tmp_path, "given.cubenet")
        window = self.make(qtbot, tmp_path)
        window._on_target_changed(F(5))  # an unsaved change
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.CANCEL)
        window.open_project_requested(given)
        assert window.project_path is None  # kept
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)
        window.open_project_requested(given)
        assert window.project_path == given

    def test_the_same_project_just_comes_to_the_front(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        given = self.saved(qtbot, tmp_path, "given.cubenet")
        window = self.make(qtbot, tmp_path)
        window.open_project_requested(given)
        window._on_target_changed(F(5))
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: pytest.fail("not asked"))
        window.open_project_requested(given)
        assert window.is_dirty  # nothing reloaded, the change is still there
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)  # closing


class TestSavedOrNot:
    """The user sees whether there are unsaved changes, and that saving did something."""

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def change(self, window: MainWindow) -> None:
        from cube_net.ui.sheet import net_style

        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - net_style.CUT_HITBOX_PX / 2 / view.scale_factor())  # a cut started

    def test_a_new_project_says_nothing(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.isWindowModified() and window.save_state.text() == ""

    def test_a_change_shows(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)  # closing
        window = self.make(qtbot, tmp_path)
        self.change(window)
        assert window.isWindowModified()  # the "*" before the name
        assert window.windowTitle().startswith("[*]")
        assert window.save_state.text() == "Unsaved changes"

    def test_saving_shows_where_and_that_all_is_saved(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.change(window)
        path = tmp_path / "net.cubenet"
        assert window.save_project_to(path)
        assert not window.isWindowModified()
        assert window.save_state.text() == "Saved"
        assert window.statusBar().currentMessage() == f"Saved to {path}"

    def test_saving_without_changes_still_answers(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        path = tmp_path / "net.cubenet"
        window.save_project_to(path)
        window.statusBar().clearMessage()
        window.save_action.trigger()  # Ctrl+S with nothing changed
        assert window.statusBar().currentMessage() == f"Saved to {path}"

    def test_undo_is_a_change_too(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The project's file has its history: after an undo it would be another file."""
        from cube_net.ui.save_changes_dialog import SaveChoice

        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)  # closing
        window = self.make(qtbot, tmp_path)
        self.change(window)
        window.save_project_to(tmp_path / "net.cubenet")
        window.undo_action.trigger()
        assert window.save_state.text() == "Unsaved changes" and window.isWindowModified()


class TestMenuEntry:
    """Linux, AppImage: Cube Net in the applications menu, asked about once (a throwaway data folder)."""

    def make(self, qtbot: QtBot, tmp_path: Path, appimage: object, settings: AppSettings | None = None) -> MainWindow:
        from cube_net.ui.desktop_integration import DesktopEntry

        window = MainWindow(
            settings=settings or settings_in(tmp_path, record=False),
            session_dir=tmp_path,
            appimage=appimage,  # type: ignore[arg-type]
            desktop_entry=DesktopEntry(tmp_path / "data"),
        )
        qtbot.addWidget(window)
        return window

    def appimage(self, tmp_path: Path, name: str = "Cube.AppImage") -> object:
        import shutil

        from cube_net.ui import desktop_integration
        from cube_net.ui.desktop_integration import AppImage

        root = Path(__file__).resolve().parents[2]
        appdir = tmp_path / "mounted"
        if not appdir.exists():
            (appdir / "usr/share/mime/packages").mkdir(parents=True)
            shutil.copy(root / "packaging/linux/cube-net.desktop", appdir / "cube-net.desktop")
            shutil.copy(root / "packaging/linux/cube-net.xml", appdir / "usr/share/mime/packages/cube-net.xml")
            shutil.copy(Path(desktop_integration.__file__).parent / "icons/cube_net.png", appdir / "cube-net.png")
        file = tmp_path / name
        file.write_text("an AppImage")
        return AppImage(file, appdir)

    def asked(self, monkeypatch: pytest.MonkeyPatch, answer: bool) -> list[bool]:
        questions: list[bool] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_menu_entry", lambda _parent: questions.append(answer) or answer
        )
        monkeypatch.setattr("cube_net.ui.desktop_integration.subprocess.run", lambda *_, **__: None)
        return questions

    def test_asked_once_and_added(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        questions = self.asked(monkeypatch, True)
        settings = settings_in(tmp_path, record=False)
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path), settings)
        window.offer_menu_entry()
        assert questions == [True] and settings.menu_entry is True
        assert window.desktop_entry.installed_for() == tmp_path / "Cube.AppImage"
        assert window.settings_panel.preferences.menu_entry is not None
        assert window.settings_panel.preferences.menu_entry.isChecked()
        window.offer_menu_entry()  # the next start
        assert questions == [True]  # not asked again

    def test_no_is_remembered(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        questions = self.asked(monkeypatch, False)
        settings = settings_in(tmp_path, record=False)
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path), settings)
        window.offer_menu_entry()
        window.offer_menu_entry()
        assert questions == [False] and settings.menu_entry is False
        assert window.desktop_entry.installed_for() is None

    def test_moved_it_follows_at_the_next_start(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.asked(monkeypatch, True)
        settings = settings_in(tmp_path, record=False)
        self.make(qtbot, tmp_path, self.appimage(tmp_path), settings).offer_menu_entry()
        moved = self.appimage(tmp_path, "Moved.AppImage")
        window = self.make(qtbot, tmp_path, moved, settings)
        window.offer_menu_entry()
        assert window.desktop_entry.installed_for() == tmp_path / "Moved.AppImage"

    def test_the_checkbox_adds_and_removes_it(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.asked(monkeypatch, False)
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path))
        window.offer_menu_entry()
        box = window.settings_panel.preferences.menu_entry
        assert box is not None and not box.isChecked()
        box.setChecked(True)
        assert window.desktop_entry.installed_for() is not None and window.settings.menu_entry is True
        monkeypatch.setattr("cube_net.ui.main_window.confirm_menu_entry_removal", lambda _parent: True)
        box.setChecked(False)
        assert window.desktop_entry.installed_for() is None and window.settings.menu_entry is False

    def test_turning_it_off_is_confirmed_first(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.asked(monkeypatch, True)
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path))
        window.offer_menu_entry()
        box = window.settings_panel.preferences.menu_entry
        assert box is not None and box.isChecked()
        confirmations: list[bool] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.confirm_menu_entry_removal", lambda _parent: confirmations.append(False) or False
        )
        box.setChecked(False)
        qtbot.waitUntil(box.isChecked)  # cancelled: it stays on
        assert confirmations == [False]
        assert window.desktop_entry.installed_for() is not None and window.settings.menu_entry is True

    def test_a_failure_says_so_and_changes_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        warned: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _parent, _title, text, **_: warned.append(text))
        window = self.make(qtbot, tmp_path, self.appimage(tmp_path))
        monkeypatch.setattr(window.desktop_entry, "install", lambda appimage: (_ for _ in ()).throw(OSError("full")))
        box = window.settings_panel.preferences.menu_entry
        assert box is not None
        box.setChecked(True)
        qtbot.waitUntil(lambda: not box.isChecked())
        assert warned == ["Couldn't change the applications menu: full"]
        assert window.settings.menu_entry is None

    def test_nothing_of_it_without_an_appimage(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, None)
        window.offer_menu_entry()  # asks nothing
        assert window.settings_panel.preferences.menu_entry is None


class TestUpdates:
    """Help -> Check for updates, and the daily check (the latest release comes from a stand-in, never GitHub)."""

    def make(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, latest: object) -> MainWindow:
        from cube_net.ui.updates.latest_release import LatestRelease, UpdateCheckError

        def fetch() -> LatestRelease | None:
            if isinstance(latest, Exception):
                raise latest
            return None if latest is None else LatestRelease(str(latest), "notes", "https://example.com/release")

        assert UpdateCheckError  # what the failing stand-in raises
        monkeypatch.setattr("cube_net.ui.main_window.fetch_latest_release", fetch)
        monkeypatch.setattr("cube_net.ui.main_window.__version__", "1.0.0")
        self.offered: list[str] = []
        self.automatic: list[bool] = []
        self.told: list[str] = []
        self.opened: list[str] = []
        self.answer = "later"
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_update",
            lambda _parent, release, current, can_update=False, automatic=False: self._offer(
                release.version, automatic
            ),
        )
        monkeypatch.setattr("cube_net.ui.main_window.tell_up_to_date", lambda _parent, current: self.told.append("up"))
        monkeypatch.setattr(
            "cube_net.ui.main_window.tell_check_failed", lambda _parent, problem: self.told.append(f"failed {problem}")
        )
        monkeypatch.setattr(
            "cube_net.ui.main_window.QDesktopServices.openUrl", lambda url: self.opened.append(url.toString())
        )
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        return window

    def _offer(self, version: str, automatic: bool) -> object:
        from cube_net.ui.updates.update_dialogs import UpdateChoice

        self.offered.append(version)
        self.automatic.append(automatic)
        return UpdateChoice.DOWNLOAD if self.answer == "download" else UpdateChoice.LATER

    def check(self, qtbot: QtBot, window: MainWindow, manual: bool) -> None:
        window.check_for_updates(manual)
        assert window._update_check is not None
        qtbot.waitUntil(lambda: not window._update_check.running())  # type: ignore[union-attr]
        qtbot.wait(20)  # the answer's signal, delivered in the window's thread

    def test_a_newer_version_is_offered_and_its_page_opened(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.2.0")
        self.answer = "download"
        self.check(qtbot, window, manual=True)
        assert self.offered == ["1.2.0"] and self.opened == ["https://example.com/release"]

    def test_no_newer_version(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.0.0")
        self.check(qtbot, window, manual=True)
        assert self.offered == [] and self.told == ["up"]

    def test_no_release_at_all(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, None)
        self.check(qtbot, window, manual=True)
        assert self.told == ["up"]

    def test_a_failure_is_told_when_asked(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.updates.latest_release import UpdateCheckError

        window = self.make(qtbot, tmp_path, monkeypatch, UpdateCheckError("no network"))
        self.check(qtbot, window, manual=True)
        assert self.told == ["failed no network"]

    def test_not_now_from_the_menu_skips_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.2.0")
        self.check(qtbot, window, manual=True)
        assert window.settings.skipped_update is None

    def test_daily_check_and_a_turned_down_version(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import datetime

        window = self.make(qtbot, tmp_path, monkeypatch, "1.2.0")
        self.check(qtbot, window, manual=False)
        assert self.offered == ["1.2.0"]
        assert window.settings.skipped_update == "1.2.0"  # "Not now" from the daily check
        assert window.settings.last_update_check == datetime.date.today()
        self.check(qtbot, window, manual=False)  # tomorrow, say
        assert self.offered == ["1.2.0"]  # not again
        self.check(qtbot, window, manual=True)
        assert self.offered == ["1.2.0", "1.2.0"]  # the menu still offers it
        assert self.automatic == [True, False]  # the daily check's offer starts with no button selected

    def test_a_newer_one_than_the_turned_down_one(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.3.0")
        window.settings.skipped_update = "1.2.0"
        self.check(qtbot, window, manual=False)
        assert self.offered == ["1.3.0"]

    def test_a_daily_failure_is_silent_and_tried_again(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.updates.latest_release import UpdateCheckError

        window = self.make(qtbot, tmp_path, monkeypatch, UpdateCheckError("no network"))
        self.check(qtbot, window, manual=False)
        assert self.told == [] and window.settings.last_update_check is None  # not done today: again at the next start

    def test_at_start_once_a_day_if_on(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import datetime

        window = self.make(qtbot, tmp_path, monkeypatch, "1.0.0")
        started: list[bool] = []
        monkeypatch.setattr(MainWindow, "check_for_updates", lambda self, manual: started.append(manual))
        today = datetime.date(2026, 11, 12)
        window.check_for_updates_at_start(today)
        assert started == [False]
        window.settings.last_update_check = today
        window.check_for_updates_at_start(today)  # 00:05 after 23:55 would be another day; this is the same one
        assert started == [False]
        window.check_for_updates_at_start(today + datetime.timedelta(days=1))
        assert started == [False, False]
        window.settings_panel.preferences.check_updates.setChecked(False)
        window.check_for_updates_at_start(today + datetime.timedelta(days=2))
        assert started == [False, False] and window.settings.check_updates is False

    def test_the_checkbox(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch, "1.0.0")
        box = window.settings_panel.preferences.check_updates
        assert box.isChecked()  # on unless switched off
        assert box.text() == "Periodically check for updates" and box.toolTip() == "Once a day"
        assert window.settings.check_updates is True


class TestUpdating:
    """Download and update: the download stands in (it says done at once), installing and quitting are watched."""

    def make(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MainWindow:
        from PyQt6.QtCore import QObject, pyqtSignal

        from cube_net.ui.updates.installation import Installation, Kind
        from cube_net.ui.updates.latest_release import LatestRelease, ReleaseFile

        self.package = tmp_path / "CubeNet-1.2.0-linux-x86_64.AppImage"
        self.done: list[str] = []
        self.outcome = "finished"
        test = self

        class Download(QObject):
            progress = pyqtSignal(int, int)
            finished = pyqtSignal(object)
            failed = pyqtSignal(str)
            cancelled = pyqtSignal()

            def __init__(self, name: str, *_: object) -> None:
                super().__init__()
                test.done.append(f"download {name}")

            def start(self) -> None:
                if test.outcome == "finished":
                    self.finished.emit(test.package)
                else:
                    self.failed.emit("no network")

            def cancel(self) -> None:
                pass

        release = LatestRelease(
            "1.2.0",
            "notes",
            "https://example.com/release",
            {self.package.name: ReleaseFile(10, "https://dl/l"), "SHA256SUMS": ReleaseFile(1, "https://dl/s")},
        )
        installation = Installation(Kind.APPIMAGE, tmp_path / "Cube.AppImage")
        monkeypatch.setattr("cube_net.ui.updates.latest_release.sys.platform", "linux")
        monkeypatch.setattr("cube_net.ui.main_window.__version__", "1.0.0")
        monkeypatch.setattr("cube_net.ui.main_window.fetch_latest_release", lambda: release)
        monkeypatch.setattr("cube_net.ui.main_window.current_installation", lambda: installation)
        monkeypatch.setattr("cube_net.ui.main_window.download_folder", lambda installation: tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.PackageDownload", Download)
        monkeypatch.setattr("cube_net.ui.main_window.ask_update", self.ask)
        monkeypatch.setattr(
            "cube_net.ui.main_window.install_appimage",
            lambda new, current: self.done.append(f"install {new.name}") or new,
        )
        monkeypatch.setattr(
            "cube_net.ui.main_window.start_appimage", lambda path: self.done.append(f"start {path.name}")
        )
        monkeypatch.setattr(
            "cube_net.ui.main_window.QDesktopServices.openUrl", lambda url: self.done.append(f"open {url.toString()}")
        )
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def ask(
        self, _parent: object, release: object, current: str, can_update: bool = False, automatic: bool = False
    ) -> object:
        from cube_net.ui.updates.update_dialogs import UpdateChoice

        self.done.append(f"asked, can update: {can_update}")
        return UpdateChoice.DOWNLOAD

    def check(self, qtbot: QtBot, window: MainWindow) -> None:
        window.check_for_updates(manual=True)
        assert window._update_check is not None
        qtbot.waitUntil(lambda: not window._update_check.running())  # type: ignore[union-attr]
        qtbot.wait(20)

    def test_downloaded_installed_started_and_quit(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch)
        self.check(qtbot, window)
        assert self.done == [
            "asked, can update: True",
            "download CubeNet-1.2.0-linux-x86_64.AppImage",
            "install CubeNet-1.2.0-linux-x86_64.AppImage",
            "start CubeNet-1.2.0-linux-x86_64.AppImage",
        ]
        assert not window.isVisible()  # quit for the new version

    def test_unsaved_changes_first_and_not_again(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.save_changes_dialog import SaveChoice

        window = self.make(qtbot, tmp_path, monkeypatch)
        window._on_target_changed(F(5))  # an unsaved change
        questions: list[str] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_save_changes", lambda *_: questions.append("asked") or SaveChoice.CANCEL
        )
        self.check(qtbot, window)
        assert questions == ["asked"] and "download CubeNet-1.2.0-linux-x86_64.AppImage" not in self.done  # cancelled
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_save_changes", lambda *_: questions.append("asked") or SaveChoice.DISCARD
        )
        self.check(qtbot, window)
        assert questions == ["asked", "asked"]  # once for this update, not again when it quits
        assert not window.isVisible()

    def test_a_failed_download_offers_the_page(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch)
        self.outcome = "failed"
        told: list[str] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.tell_update_failed", lambda _parent, problem: told.append(problem) or True
        )
        self.check(qtbot, window)
        assert told == ["no network"] and self.done[-1] == "open https://example.com/release"
        assert window.isVisible()

    def test_by_hand_when_it_cant_be_put_in_place(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.updates.installation import ManualStepNeeded

        window = self.make(qtbot, tmp_path, monkeypatch)

        def locked(new: Path, current: Path) -> Path:
            raise ManualStepNeeded(new, Path("/opt") / new.name)

        monkeypatch.setattr("cube_net.ui.main_window.install_appimage", locked)
        monkeypatch.setattr("cube_net.ui.main_window.tell_appimage_downloaded", lambda *_: False)  # "Close"
        self.check(qtbot, window)
        assert window.isVisible() and not any(step.startswith("start") for step in self.done)

    def test_run_from_the_source_it_opens_the_page(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path, monkeypatch)
        monkeypatch.setattr("cube_net.ui.main_window.current_installation", lambda: None)
        self.check(qtbot, window)
        assert self.done == ["asked, can update: False", "open https://example.com/release"]
