# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main window: its sheet, the coordinates and labels, the ruler, the bounding rectangle, the status bar."""

from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, QSettings, Qt
from pytestqt.qtbot import QtBot
from window_checks import session_lines, settings_in

from cube_net.ui.app_settings import AppSettings
from cube_net.ui.main_window import (
    APP_TITLE,
    NO_COORDINATES,
    MainWindow,
    format_coordinates,
    format_ruler_total,
)


def test_main_window_opens(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    assert window.windowTitle() == f"[*]Untitled — {APP_TITLE}"
    assert window.centralWidget() is window.stack and window.stack.currentWidget() is window.sheet_view
    assert not window.in_template_mode


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


def test_l_switches_the_vertex_labels_when_released(qtbot: QtBot, tmp_path: Path) -> None:
    from PyQt6.QtTest import QTest

    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    window = MainWindow(settings=settings)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    handle = window.windowHandle()
    assert handle is not None
    box = window.settings_panel.preferences.show_labels
    assert box.toolTip() == "Hotkey: L"
    for panel_shown in (True, False):
        window.settings_panel.setVisible(panel_shown)
        QTest.keyPress(handle, Qt.Key.Key_L)
        assert window.show_labels_action.isChecked()  # not yet
        QTest.keyRelease(handle, Qt.Key.Key_L)
        assert not window.show_labels_action.isChecked() and not box.isChecked()
        assert settings.show_vertex_labels is False
        QTest.keyClick(handle, Qt.Key.Key_L)
        assert window.show_labels_action.isChecked() and box.isChecked()


def test_c_switches_the_coordinates_hint_when_released(qtbot: QtBot, tmp_path: Path) -> None:
    from PyQt6.QtTest import QTest

    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    window = MainWindow(settings=settings)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    handle = window.windowHandle()
    assert handle is not None
    box = window.settings_panel.preferences.show_coordinates
    assert box is not None and box.toolTip() == "Hotkey: C" and box.text() == "Show vertex coordinates"
    assert window.show_coordinates_action.isChecked()  # on by default
    QTest.keyPress(handle, Qt.Key.Key_C)
    assert window.show_coordinates_action.isChecked()  # not yet
    QTest.keyRelease(handle, Qt.Key.Key_C)
    assert not window.show_coordinates_action.isChecked() and not box.isChecked()
    assert settings.show_vertex_coordinates is False
    window.sheet_view.mouse_moved.emit(10.0, 13.0)  # a vertex
    assert not window.sheet_cursor.coordinates_hint.isVisible()
    QTest.keyClick(handle, Qt.Key.Key_C)
    assert window.show_coordinates_action.isChecked() and window.sheet_cursor.coordinates_hint.isVisible()


def test_the_coordinates_hint_off_at_start_when_switched_off(qtbot: QtBot, tmp_path: Path) -> None:
    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    settings.show_vertex_coordinates = False
    window = MainWindow(settings=settings)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.sheet_view.mouse_moved.emit(10.0, 13.0)
    assert not window.show_coordinates_action.isChecked()
    assert not window.sheet_cursor.coordinates_hint.isVisible()


def test_ctrl_c_copies_what_the_hint_shows(qtbot: QtBot, tmp_path: Path) -> None:
    from PyQt6.QtGui import QEnterEvent, QKeySequence
    from PyQt6.QtWidgets import QApplication

    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    window = MainWindow(settings=settings)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    assert window.copy_coordinates_action.shortcut() == QKeySequence(QKeySequence.StandardKey.Copy)
    clipboard = QApplication.clipboard()
    assert clipboard is not None
    clipboard.setText("what the user copied")
    window.sheet_view.mouse_moved.emit(11.5, 12.5)  # no hint: the clipboard stays as it is
    window.copy_coordinates_action.trigger()
    assert clipboard.text() == "what the user copied"
    window.sheet_view.mouse_moved.emit(10.0, 13.0)
    window.copy_coordinates_action.trigger()
    assert clipboard.text() == "y: 13\nx: 10"
    label = window.bounding.label
    at = QPointF(5, 5)
    QApplication.sendEvent(label, QEnterEvent(at, at, QPointF(label.mapToGlobal(QPoint(5, 5)))))  # over the area
    window.copy_coordinates_action.trigger()
    assert clipboard.text() == window.bounding.copied_hint()  # the area's hint wins while it's shown
    assert clipboard.text().endswith("12 = 12.000")


def test_labels_off_at_start_when_disabled_in_settings(qtbot: QtBot, tmp_path: Path) -> None:
    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    settings.show_vertex_labels = False
    window = MainWindow(settings=settings)
    qtbot.addWidget(window)
    item = window.sheet_view.net_item()
    assert item is not None and item.labels() is None
    assert not window.show_labels_action.isChecked()


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

    window = MainWindow(settings=settings_in(tmp_path, record=False))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    view = window.sheet_view

    def h1_in_window() -> object:
        return view.viewport().mapTo(window, view.from_sheet(QPointF(11, 12)).toPoint())

    before, x = h1_in_window(), window.stack.x()  # the view is in the stack of the project's and template's views
    window.ruler_action.setChecked(True)
    window.ruler_total_label.setText("Σ 123456789.123")  # a long total: the panel gets wider
    qtbot.waitUntil(lambda: window.stack.x() > x)
    assert h1_in_window() == before
    window.ruler_action.setChecked(False)
    qtbot.waitUntil(lambda: window.stack.x() == x)
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


def test_no_panning_from_a_cut_line_point_off_the_net(qtbot: QtBot, tmp_path: Path) -> None:

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


def test_the_footer_shows_the_files_path(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    assert window.path_label.path() == ""  # a new project: no file yet
    project = tmp_path / "cube.cubenet"
    assert window.save_project_to(project)
    assert window.path_label.path() == str(project)
    window.new_template_action.trigger()
    assert window.path_label.path() == ""
    template = tmp_path / "pillow.nettemplate"
    assert window.save_template_to(template)
    assert window.path_label.path() == str(template)
    assert window.open_project_from(project)
    assert window.path_label.path() == str(project)


class TestStatusMessages:
    def test_a_message_shown_before_the_window_still_hides_the_path(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)  # it says it records
        qtbot.addWidget(window)
        assert window.statusBar().currentMessage().startswith("Recording session to")
        window.show()
        qtbot.waitExposed(window)
        assert window.statusBar().currentMessage().startswith("Recording session to")
        assert not window.path_label.isVisible()  # under the message, not drawn over by it
        window.statusBar().clearMessage()
        assert window.path_label.isVisible()
        window.stop_recording("test over")
