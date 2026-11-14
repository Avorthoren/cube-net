# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Right click -> Place a vertex, in the main window: the menu and the window are answered from timers, as a user would
(each opens its own event loop)."""

from collections.abc import Callable
from fractions import Fraction as F
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from cube_net.core.editor import EditorState
from cube_net.core.geometry import Vec
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.context_menu import ContextMenu
from cube_net.ui.main_window import MainWindow, format_coordinates
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.place_vertex_window import PlaceVertexWindow


def make(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    settings.record_session = False
    window = MainWindow(settings=settings, session_dir=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def inside(window: MainWindow) -> float:
    """Half a cut's hitbox, in units: that far inside an edge, a click lands on it."""
    return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()


def open_menu() -> ContextMenu:
    menus = [menu for window in QApplication.topLevelWidgets() for menu in window.findChildren(ContextMenu)]
    shown = [menu for menu in menus if menu.is_open()]
    assert len(shown) == 1
    return shown[0]


def answer_menu(act: Callable[[ContextMenu], None]) -> list[bool]:
    """Once the menu is up, do this to it; tells whether its item was enabled."""
    enabled: list[bool] = []

    def answer() -> None:
        menu = open_menu()
        enabled.append(menu.items[0].enabled)
        act(menu)

    QTimer.singleShot(0, answer)
    return enabled


def choose(menu: ContextMenu) -> None:
    """Click "Place a vertex", as the user would."""
    QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.item_rect(0).center())


def close(menu: ContextMenu) -> None:
    QTest.keyClick(menu.window().windowHandle(), Qt.Key.Key_Escape)


def answer_window(act: Callable[[PlaceVertexWindow], None]) -> None:
    def answer() -> None:
        window = QApplication.activeModalWidget()
        assert isinstance(window, PlaceVertexWindow)
        act(window)

    QTimer.singleShot(50, answer)


def test_place_the_first_point_on_an_edge(qtbot: QtBot, tmp_path: Path) -> None:
    window = make(qtbot, tmp_path)

    def typed(dialog: PlaceVertexWindow) -> None:
        dialog.x.numerator.setText("34")
        dialog.x.denominator.setText("3")
        dialog.place_button.click()

    enabled = answer_menu(lambda menu: (answer_window(typed), choose(menu)))
    window.sheet_view.right_pressed.emit(11.5, 14 - inside(window))  # in the hitbox of the top edge of face 1
    assert enabled == [True]
    line = window.editor.cut_line
    assert line is not None and [p.position for p in line.points] == [Vec(F(34, 3), 14)]


def test_disabled_where_nothing_would_be_placed(qtbot: QtBot, tmp_path: Path) -> None:
    window = make(qtbot, tmp_path)
    in_a_face = answer_menu(close)
    window.sheet_view.right_pressed.emit(11.5, 13.5)  # DEFAULT, inside a face
    on_a_vertex = answer_menu(close)
    window.sheet_view.right_pressed.emit(10.0, 13.0)  # a vertex: both coordinates fixed
    assert in_a_face == on_a_vertex == [False]
    assert window.editor.cut_line is None


def test_no_menu_while_editing_without_a_drag(qtbot: QtBot, tmp_path: Path) -> None:
    window = make(qtbot, tmp_path)
    view = window.sheet_view
    view.left_pressed.emit(11.5, 14 - inside(window))
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside(window), 13.5)
    assert window.editor.state is EditorState.CUT_EDITING
    view.right_pressed.emit(11.5, 13.5)  # returns at once: no menu to wait for
    assert window.findChildren(ContextMenu) == []


def test_a_drag_cancelled_puts_the_point_back(qtbot: QtBot, tmp_path: Path) -> None:
    window = make(qtbot, tmp_path)
    view = window.sheet_view
    view.left_pressed.emit(11.5, 14 - inside(window))
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside(window), 13.5)
    for answer in (close, lambda menu: (answer_window(lambda dialog: dialog.reject()), choose(menu))):
        view.left_pressed.emit(11.5, 13.5)
        view.mouse_moved.emit(11.6, 13.6)
        assert window.cut_tool.dragging
        answer_menu(answer)
        view.right_pressed.emit(11.6, 13.6)
        assert not window.cut_tool.dragging
        line = window.editor.cut_line
        assert line is not None and line.points[1].position == Vec(F(23, 2), F(27, 2))  # back where it was


def test_a_drag_placed_ends_there(qtbot: QtBot, tmp_path: Path) -> None:
    window = make(qtbot, tmp_path)
    view = window.sheet_view
    view.left_pressed.emit(11.5, 14 - inside(window))
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside(window), 13.5)
    view.left_pressed.emit(11.5, 13.5)
    view.mouse_moved.emit(11.6, 13.6)

    def typed(dialog: PlaceVertexWindow) -> None:
        dialog.y.numerator.setText("40")
        dialog.y.denominator.setText("3")
        dialog.place_button.click()

    answer_menu(lambda menu: (answer_window(typed), choose(menu)))
    view.right_pressed.emit(11.6, 13.6)
    assert not window.cut_tool.dragging
    line = window.editor.cut_line
    assert line is not None and line.points[1].position == Vec(F(58, 5), F(40, 3))


def test_not_in_the_help_animations(qtbot: QtBot) -> None:
    from PyQt6.QtCore import QSize

    from cube_net.ui.help.demo.demo_sheet import DemoSheet

    assert DemoSheet(QSize(560, 400)).workspace.place_vertex is None


def test_while_the_window_is_open_the_mouse_shows_as_usual(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The footer's coordinates and the coordinates hint follow the mouse over the sheet; a dragged point stays put."""
    from PyQt6.QtCore import QPointF

    window = make(qtbot, tmp_path)
    view = window.sheet_view
    view.left_pressed.emit(11.5, 14 - inside(window))
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside(window), 13.5)
    view.left_pressed.emit(11.5, 13.5)
    view.mouse_moved.emit(11.6, 13.6)
    seen: list[object] = []

    def look(dialog: PlaceVertexWindow) -> None:
        viewport = view.viewport()
        assert viewport is not None
        at = viewport.mapToGlobal(view.from_sheet(QPointF(10, 13)).toPoint())
        monkeypatch.setattr(view, "cursor_position", lambda: at)
        view.follow_tick()
        p = view.to_sheet(QPointF(viewport.mapFromGlobal(at)))
        seen.append((window.coords_label.text(), format_coordinates(p.x(), p.y())))
        seen.append(window.sheet_cursor.coordinates_hint.lines())
        seen.append(window.cut_tool.item.points()[1].position)  # the dragged point, where the drag had brought it
        dialog.reject()

    answer_menu(lambda menu: (answer_window(look), choose(menu)))
    view.right_pressed.emit(11.6, 13.6)
    (footer, expected), hint, dragged = seen
    assert footer == expected  # the footer follows the mouse
    assert hint == ["y: 13", "x: 10"]  # the vertex under the mouse
    assert dragged == Vec(F(58, 5), F(68, 5))  # it didn't follow the mouse to the vertex


def test_releasing_the_drags_button_with_the_menu_open(qtbot: QtBot, tmp_path: Path) -> None:
    """The left button, held for the drag, is released while the menu is open: the drag doesn't end (the point stays
    where it was brought), the menu stays, and its item can then be clicked."""
    from PyQt6.QtCore import QPointF

    window = make(qtbot, tmp_path)
    view = window.sheet_view
    view.left_pressed.emit(11.5, 14 - inside(window))
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside(window), 13.5)
    view.left_pressed.emit(11.5, 13.5)
    view.mouse_moved.emit(11.6, 13.6)
    seen: list[bool] = []

    def release_then_choose(menu: ContextMenu) -> None:
        viewport = view.viewport()
        assert viewport is not None
        spot = view.from_sheet(QPointF(11.6, 13.6)).toPoint()
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=spot)
        seen.extend([menu.is_open(), window.cut_tool.dragging])
        answer_window(lambda dialog: dialog.reject())
        choose(menu)

    answer_menu(release_then_choose)
    view.right_pressed.emit(11.6, 13.6)
    assert seen == [True, True]
    line = window.editor.cut_line
    assert line is not None and line.points[1].position == Vec(F(23, 2), F(27, 2))  # cancelled: back where it was


def test_with_the_window_open_the_dashed_line_stays_on_its_edge(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PyQt6.QtCore import QPointF

    window = make(qtbot, tmp_path)
    view = window.sheet_view
    view.left_pressed.emit(11.5, 14 - inside(window))  # the line starts at (11.5, 14)
    seen: list[object] = []

    def look(dialog: PlaceVertexWindow) -> None:
        viewport = view.viewport()
        assert viewport is not None
        beyond = viewport.mapToGlobal(view.from_sheet(QPointF(11.7, 12.5)).toPoint())  # below the edge's end
        monkeypatch.setattr(view, "cursor_position", lambda: beyond)
        view.follow_tick()
        seen.append(window.cut_tool.item.rubber_band())
        dialog.reject()

    answer_menu(lambda menu: (answer_window(look), choose(menu)))
    view.right_pressed.emit(12 - inside(window), 13.6)  # the edge x = 12, from y = 13 to 14
    assert seen == [(Vec(F(23, 2), 14), Vec(12, 13))]
