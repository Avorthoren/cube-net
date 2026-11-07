from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings, Qt
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
