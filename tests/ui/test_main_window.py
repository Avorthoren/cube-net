from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings
from pytestqt.qtbot import QtBot

from cube_net.ui.app_settings import AppSettings
from cube_net.ui.main_window import APP_TITLE, NO_COORDINATES, MainWindow, format_coordinates


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
    assert lines[-3:] == ["state net default", "state labels on", f"state window {window.width()}x{window.height()}"]
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
    window.cut_hover.update_at(10.02, 12.5)
    assert window.cut_hover.hovered() is not None
