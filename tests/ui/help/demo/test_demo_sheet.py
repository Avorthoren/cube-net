# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import QPoint, QPointF, QSize, Qt
from pytestqt.qtbot import QtBot

from cube_net.core.editor import EditorState
from cube_net.ui.help.demo.demo_sheet import FRAME_MS, DemoSheet
from cube_net.ui.help.demo.steps import Keys, Move, RightClick, ToItem, Type, Wait, click
from cube_net.ui.sheet.cursors import CursorKind
from cube_net.ui.sheet.sheet_context_menu import MOVE_ORIGIN, PLACE_VERTEX


def make(qtbot: QtBot) -> DemoSheet:
    sheet = DemoSheet(QSize(560, 400))
    qtbot.addWidget(sheet)
    sheet.show()
    qtbot.waitExposed(sheet)
    return sheet


def test_the_waits_of_a_script(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    waits = list(sheet.play([Move((11.5, 12.5), 0), Move((11.6, 12.5), FRAME_MS * 3), Wait(500)]))
    assert waits == [FRAME_MS] * 4 + [500]
    assert list(sheet.play([Move((11.5, 12.5), 300), Wait(500)], instant=True)) == []


def test_scripted_clicks_reach_the_tools(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    for _ in sheet.play([Move((11.0, 14.0), 0), *click()], instant=True):
        pass
    assert sheet.workspace.editor.state is EditorState.CUTTING
    assert sheet.pointer.kind() is CursorKind.SCISSORS


def test_the_users_mouse_means_nothing(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    viewport = sheet.view.viewport()
    assert viewport is not None
    at = sheet.view.from_sheet(QPointF(11.0, 14.0)).toPoint()
    qtbot.mouseClick(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at)
    assert sheet.workspace.editor.state is EditorState.DEFAULT
    qtbot.mouseMove(viewport, QPoint(5, 5))
    assert sheet.mouse() is None


def test_held_keys_go_with_the_mouse(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    for _ in sheet.play([Move((11.5, 12.5), 0), Keys(Qt.KeyboardModifier.ControlModifier)], instant=True):
        pass
    assert sheet.view.ctrl_held()


def test_no_vertex_labels(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    item = sheet.view.net_item()
    assert item is not None and item.labels() is None
    for _ in sheet.play([Move((11.0, 14.0), 0), *click(), Move((11.6, 12.2), 0), *click()], instant=True):
        pass
    assert item.labels() is None and sheet.workspace.cut_tool.item.labels() == ()


def test_the_bounding_rectangle_if_wanted(qtbot: QtBot) -> None:
    from cube_net.core.geometry import Vec

    assert DemoSheet(QSize(560, 400)).bounding_item is None
    sheet = DemoSheet(QSize(560, 400), bounds=True)
    qtbot.addWidget(sheet)
    assert sheet.bounding_item is not None
    assert set(sheet.bounding_item.corners()) == {Vec(10, 10), Vec(13, 10), Vec(13, 14), Vec(10, 14)}
    assert not sheet.bounding_item.success()  # 12 isn't below a new project's target


def test_no_coordinates_hint_in_the_animations(qtbot: QtBot) -> None:
    """They show the very essence of the application, as little as possible besides."""
    from cube_net.ui.sheet.coordinates_hint import CoordinatesHint

    sheet = DemoSheet(QSize(560, 400))
    assert sheet.workspace.sheet_cursor is None
    assert sheet.findChildren(CoordinatesHint) == []


def play(sheet: DemoSheet, steps: list) -> None:
    for _ in sheet.play(steps, instant=True):
        pass


# A cut started at the default net's A_1, and the mouse on the net beside it.
CUTTING = [Move((11.0, 14.0), 0), *click(), Move((11.4, 12.6), 0)]


def test_a_right_click_opens_the_sheets_menu_there(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    play(sheet, [*CUTTING, RightClick()])
    menu = sheet.menu
    assert menu is not None and menu.isVisible()
    assert [item.enabled for item in menu.items] == [True, True, False]  # no drawn point under the mouse to move to
    play(sheet, [ToItem(PLACE_VERTEX)])
    assert menu.current() == PLACE_VERTEX  # highlighted under the mouse
    assert sheet.pointer.kind() is CursorKind.ARROW


def test_a_click_off_its_items_closes_the_menu(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    play(sheet, [*CUTTING, RightClick(), ToItem(MOVE_ORIGIN), *click()])  # disabled
    assert sheet.menu is None and sheet.place_window is None
    assert sheet.workspace.editor.state is EditorState.CUTTING  # the click didn't reach the sheet


def test_place_a_vertex_typed_into_its_window(qtbot: QtBot) -> None:
    from fractions import Fraction as F

    from cube_net.core.geometry import Vec

    sheet = make(qtbot)
    play(sheet, [*CUTTING, RightClick(), ToItem(PLACE_VERTEX), *click()])
    window = sheet.place_window
    assert window is not None and window.isVisible() and window.focusWidget() is window.y.numerator
    play(sheet, [Type("25\t2\t23\t2")])  # the numerator typed, its denominator is 1 until typed too
    assert [field.text() for field in (window.y.numerator, window.y.denominator)] == ["25", "2"]
    assert [field.text() for field in (window.x.numerator, window.x.denominator)] == ["23", "2"]
    play(sheet, [Type("\n")])
    assert window.message.isHidden(), window.message.text()
    assert sheet.place_window is None
    line = sheet.workspace.editor.cut_line
    assert line is not None and line.last.position == sheet.workspace.editor.origin.sheet(Vec(F(23, 2), F(25, 2)))


def test_the_built_in_cubes_look_whatever_is_in_place(qtbot: QtBot) -> None:
    """Help's animations look the same whatever is open: another style, a body's colours, a template."""
    from dataclasses import replace

    from PyQt6.QtGui import QImage

    from cube_net.core.body import CUBE
    from cube_net.ui import palette
    from cube_net.ui.style import DEFAULT_CUBE_LOOK, DEFAULT_STYLE, apply_style
    from cube_net.ui.style.apply import style_in_place

    def picture() -> QImage:
        sheet = make(qtbot)
        play(sheet, [*CUTTING, Move((11.6, 12.2), 0), *click()])
        return sheet.grab().toImage().convertToFormat(QImage.Format.Format_ARGB32)

    plain = picture()
    other = replace(DEFAULT_STYLE, edge_width=1.0, vertex_radius=3.0, hatch_columns=1.0, dashes_per_unit=2.0)
    colors = ("#111111",) * len(CUBE.colors)
    apply_style(other)
    palette.set_face_colors(colors, CUBE)
    try:
        assert make(qtbot).look == DEFAULT_CUBE_LOOK
        assert picture() == plain
        assert style_in_place() == other and palette.face_colors_in_place() == (colors, CUBE)  # still the project's
    finally:
        palette.set_face_colors(CUBE.colors, CUBE)
