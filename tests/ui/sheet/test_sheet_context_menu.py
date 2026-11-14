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
from cube_net.ui.sheet.move_origin_window import MoveOriginWindow
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


def test_no_menu_while_editing_without_a_drag_off_the_points(qtbot: QtBot, tmp_path: Path) -> None:
    window = make(qtbot, tmp_path)
    view = window.sheet_view
    view.left_pressed.emit(11.5, 14 - inside(window))
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside(window), 13.5)
    assert window.editor.state is EditorState.CUT_EDITING
    view.right_pressed.emit(11.7, 13.8)  # no point there: returns at once, no menu to wait for
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

    assert DemoSheet(QSize(560, 400)).workspace.context_menu is None


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


def choose_item(i: int) -> Callable[[ContextMenu], None]:
    def click(menu: ContextMenu) -> None:
        QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.item_rect(i).center())

    return click


def answer_slope(y: str, x: str) -> None:
    from cube_net.ui.sheet.set_slope_window import SetSlopeWindow

    def answer() -> None:
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, SetSlopeWindow)
        dialog.y.setText(y)
        dialog.x.setText(x)
        dialog.set_button.click()

    QTimer.singleShot(50, answer)


class TestSetSlope:
    def test_disabled_where_theres_no_segment(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        items: list[list[bool]] = []

        def look(menu: ContextMenu) -> None:
            items.append([item.enabled for item in menu.items])
            close(menu)

        answer_menu(look)
        window.sheet_view.right_pressed.emit(11.5, 14 - inside(window))  # DEFAULT
        assert items == [[True, False, False]]  # no point there to move the origin by

    def test_set_while_cutting_said_and_escape_unlocks(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - inside(window))
        answer_menu(lambda menu: (answer_slope("-2", "1"), choose_item(1)(menu)))
        view.right_pressed.emit(11.7, 13.6)
        assert window.cut_tool.slope() == Vec(1, -2)
        assert window.slope_label.isVisible()
        assert window.slope_label.text() == "Slope locked: y -2, x 1 (until the point is placed; Escape unlocks)"
        window.unlock_slope_action.trigger()  # Escape
        assert window.cut_tool.slope() is None and not window.slope_label.isVisible()
        assert not window.unlock_slope_action.isEnabled()  # Escape means nothing else meanwhile

    def test_set_during_a_drag_goes_on_until_a_click(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - inside(window))
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - inside(window), 13.5)
        view.left_pressed.emit(11.5, 13.5)  # Y
        view.mouse_moved.emit(11.6, 13.6)
        answer_menu(lambda menu: (answer_slope("-2", "1"), choose_item(1)(menu)))
        view.right_pressed.emit(11.6, 13.6)
        assert window.cut_tool.dragging and window.cut_tool.slope() == Vec(1, -2)
        view.mouse_moved.emit(11.7, 13.4)  # no button held: it follows, along the slope
        view.left_pressed.emit(11.7, 13.4)
        line = window.editor.cut_line
        assert line is not None and not window.cut_tool.dragging and window.cut_tool.slope() is None
        assert (line.points[1].position - Vec(F(23, 2), 14)).cross(Vec(1, -2)) == 0

    def test_cancel_in_place_a_vertex_unlocks(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - inside(window))
        window.cut_tool.lock_slope(Vec(1, -2))
        answer_menu(lambda menu: (answer_window(lambda dialog: dialog.reject()), choose(menu)))
        view.right_pressed.emit(11.6, 13.6)
        assert window.cut_tool.slope() is None


def test_the_drag_after_set_slope_ends_with_a_real_click_anywhere(qtbot: QtBot, tmp_path: Path) -> None:
    """Through the sheet's own presses (which pan wherever nothing claims them): a click on an empty spot of a face,
    after Escape too, puts the point."""
    from PyQt6.QtCore import QPointF

    for unlock_first in (False, True):
        window = make(qtbot, tmp_path / str(unlock_first))
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - inside(window))
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - inside(window), 13.5)
        view.left_pressed.emit(11.5, 13.5)
        view.mouse_moved.emit(11.6, 13.6)
        answer_menu(lambda menu: (answer_slope("-2", "1"), choose_item(1)(menu)))
        view.right_pressed.emit(11.6, 13.6)
        assert window.cut_tool.dragging
        if unlock_first:
            window.unlock_slope_action.trigger()  # Escape: unlocked, the drag goes on
            assert window.cut_tool.dragging
        viewport = view.viewport()
        assert viewport is not None
        spot = view.from_sheet(QPointF(11.7, 13.4)).toPoint()  # no point, no circle, no cut there
        QTest.mouseMove(viewport, spot)
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=spot)
        assert not window.cut_tool.dragging and not view.is_panning()
        line = window.editor.cut_line
        assert line is not None and line.points[1].position != Vec(F(23, 2), F(27, 2))  # it moved, and stays


class TestMoveTheOrigin:
    """Right click on a drawn point -> Move the origin: the point gets the typed coordinates, nothing else moves."""

    @staticmethod
    def answer(act: Callable[[ContextMenu], None]) -> list[list[bool]]:
        """Once the menu is up, do this to it; tells which of its items were enabled."""
        enabled: list[list[bool]] = []

        def answer() -> None:
            menu = open_menu()
            enabled.append([item.enabled for item in menu.items])
            act(menu)

        QTimer.singleShot(0, answer)
        return enabled

    @staticmethod
    def type_coordinates(y: tuple[str, str], x: tuple[str, str], accept: bool = True) -> list[Vec]:
        """Once the window is up, type y and x (numerator, denominator); it tells what it started with."""
        started: list[Vec] = []

        def answer() -> None:
            dialog = QApplication.activeModalWidget()
            assert isinstance(dialog, MoveOriginWindow)
            started.append(dialog.coordinates() or Vec(0, 0))
            dialog.y.numerator.setText(y[0])
            dialog.y.denominator.setText(y[1])
            dialog.x.numerator.setText(x[0])
            dialog.x.denominator.setText(x[1])
            (dialog.move_button if accept else dialog.cancel_button).click()

        QTimer.singleShot(50, answer)
        return started

    def move(self, window: MainWindow, at: tuple[float, float], y: tuple[str, str], x: tuple[str, str]) -> list[Vec]:
        started = self.type_coordinates(y, x)
        self.answer(choose_item(2))
        window.sheet_view.right_pressed.emit(*at)
        return started

    def test_a_vertex_gets_the_typed_coordinates(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        c1 = Vec(11, 13)
        started = self.move(window, (11.0, 13.0), ("-1", "2"), ("5", "1"))
        assert started == [c1]  # the hint's coordinates
        origin = window.editor.origin
        assert origin.shown(c1) == Vec(5, F(-1, 2))
        assert origin.shown(Vec(12, 13)) == Vec(6, F(-1, 2))  # a parallel shift
        assert origin.name == "C_1"
        assert window.is_dirty
        window.sheet_view.mouse_moved.emit(11.0, 13.0)
        assert window.coords_label.text() == format_coordinates(5, -0.5)
        assert window.sheet_cursor.coordinates() == Vec(5, F(-1, 2))

    def test_the_items_over_a_point_and_elsewhere(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        view = window.sheet_view
        on_vertex = self.answer(close)
        view.right_pressed.emit(11.0, 13.0)
        in_a_face = self.answer(close)
        view.right_pressed.emit(11.5, 13.5)
        assert on_vertex == [[False, False, True]] and in_a_face == [[False, False, False]]
        view.left_pressed.emit(11.5, 14 - inside(window))
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - inside(window), 13.5)
        on_a_line_point = self.answer(close)
        view.right_pressed.emit(11.5, 13.5)  # CUT_EDITING, no drag: only this item
        assert on_a_line_point == [[False, False, True]]
        view.left_pressed.emit(11.5, 13.5)
        view.mouse_moved.emit(11.6, 13.6)
        dragging = self.answer(close)
        view.right_pressed.emit(11.6, 13.6)
        assert dragging[0][2] is False  # never while dragging

    def test_cancel_and_the_same_coordinates_change_nothing(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        self.type_coordinates(("7", "1"), ("7", "1"), accept=False)
        self.answer(choose_item(2))
        window.sheet_view.right_pressed.emit(11.0, 13.0)
        self.move(window, (11.0, 13.0), ("13", "1"), ("11", "1"))
        assert window.editor.origin.position == Vec(0, 0)
        assert not window.editor.history.can_undo

    def test_undo_and_redo_tell_the_points_coordinates(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        told: list[tuple[str | None, Vec]] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.tell_origin_moved", lambda _parent, name, at: told.append((name, at))
        )
        window = make(qtbot, tmp_path)
        self.move(window, (11.0, 13.0), ("0", "1"), ("0", "1"))
        assert told == []  # not when it's moved
        window.undo_action.trigger()
        assert window.editor.origin.position == Vec(0, 0)
        window.redo_action.trigger()
        assert window.editor.origin.position == Vec(11, 13)
        assert told == [("C_1", Vec(11, 13)), ("C_1", Vec(0, 0))]

    def test_place_a_vertex_types_from_the_origin(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = make(qtbot, tmp_path)
        self.move(window, (11.0, 13.0), ("0", "1"), ("0", "1"))  # C_1 is (0, 0)
        started: list[Vec] = []

        def typed(dialog: PlaceVertexWindow) -> None:
            started.append(Vec(dialog.x.value() or 0, dialog.y.value() or 0))
            dialog.x.numerator.setText("1")
            dialog.x.denominator.setText("2")
            dialog.place_button.click()

        answer_menu(lambda menu: (answer_window(typed), choose(menu)))
        window.sheet_view.right_pressed.emit(11.25, 14 - inside(window))  # the top edge of face 1, y = 14
        assert started == [Vec(F(1, 4), 1)]
        line = window.editor.cut_line
        assert line is not None and [p.position for p in line.points] == [Vec(F(23, 2), 14)]
