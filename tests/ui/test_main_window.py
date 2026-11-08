from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import QToolBar
from pytestqt.qtbot import QtBot

from cube_net.ui.app_settings import AppSettings
from cube_net.ui.main_window import APP_TITLE, NO_COORDINATES, MainWindow, format_coordinates, format_ruler_total


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
    assert window.windowTitle() == APP_TITLE
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
    assert view.is_on_net(11.5, 12.5)  # face 2
    assert not view.is_on_net(10.5, 13.5)  # empty corner left of face 1


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
    assert lines[-6:] == [
        "state net default",
        "state labels on",
        f"state window {window.width()}x{window.height()}",
        "state bounds off",
        "state ruler off",
        "state cut default",
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
    window.record_session_action.setChecked(True)  # starts a file describing the current state
    first = window.recorder
    assert first is not None and settings.record_session
    assert "# recording started: turned on by the user" in session_lines(first.log.path)
    window.show_labels_action.setChecked(False)
    window.record_session_action.setChecked(False)  # ends it
    assert window.recorder is None and not settings.record_session
    assert session_lines(first.log.path)[-2:] == ["labels off", "stop turned off by the user"]
    window.record_session_action.setChecked(True)  # a new file, with the new state
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
    window.record_session_action.setChecked(True)  # turned on now: the file must describe all of this
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
    window.record_session_action.setChecked(False)
    window.record_session_action.setChecked(True)  # a new file: its state block holds the cut line
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
    assert view.is_on_net(11 - near, 14 + near)  # up-left of A_1: off the net, but in its circle
    assert not view.is_on_net(11 - 3 * near, 14 + 3 * near)  # farther out: panning is fine there


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
    view.left_pressed.emit(11.5, 13.75)  # a midpoint: insert
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
        assert not window.undo_rearrangement_action.isEnabled()
        window.sheet_view.left_pressed.emit(*self.bottom_of_face_5(window))
        assert window.undo_rearrangement_action.isEnabled()
        window.undo_rearrangement_action.trigger()
        assert window.editor.state.value == "cut_editing"
        assert window.bounding.label.text() == "Area\n12.000"
        assert len(window.cut_tool.item.points()) == 3
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert lines[-2:] == ["cut glue 11.500,10.000 12.000,10.000 ok", "cut unglue"]
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
        window.record_session_action.setChecked(True)
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
        window.undo_rearrangement_action.trigger()
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
        window.undo_rearrangement_action.trigger()
        assert item.overlapping() == frozenset()
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
        window.undo_rearrangement_action.trigger()
        assert not self.divided_on(window)  # the hover was reset; the next move decides
        window.sheet_view.mouse_moved.emit(11.75, 10 + h)
        assert self.divided_on(window)
