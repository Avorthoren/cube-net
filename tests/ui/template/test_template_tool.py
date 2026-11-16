# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest
from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Box, Vec
from cube_net.core.template import Fold, TemplateEditor, TemplateProblem, TemplateState
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.cursors import CursorKind
from cube_net.ui.sheet.sheet_view import SheetView
from cube_net.ui.template.template_mode import SHEET
from cube_net.ui.template.template_tool import FLASH_MS, TemplateTool, template_problem_text

# A 2 x 1 rectangle with the middles of its long sides (ids 0..5, counter-clockwise).
PILLOW = [(10, 10), (11, 10), (12, 10), (12, 11), (11, 11), (10, 11)]


@pytest.fixture
def setup(qtbot: QtBot) -> tuple[SheetView, TemplateTool]:
    view = SheetView()
    qtbot.addWidget(view)
    view.resize(800, 600)
    view.set_sheet(SHEET)
    view.show_initial_view(Box(Vec(9, 9), Vec(13, 12)))
    view.show()
    qtbot.waitExposed(view)
    return view, TemplateTool(view, TemplateEditor())


def drawn(view: SheetView, tool: TemplateTool) -> None:
    for x, y in [*PILLOW, PILLOW[0]]:
        view.left_pressed.emit(float(x), float(y))
    assert tool.editor.state is TemplateState.FINALIZATION


def click(view: SheetView, x: float, y: float) -> None:
    view.left_pressed.emit(x, y)
    view.left_released.emit(x, y)


def test_clicks_draw_the_loop_and_its_first_vertex_closes_it(
    setup: tuple[SheetView, TemplateTool], qtbot: QtBot
) -> None:
    view, tool = setup
    assert tool.cursor_at(10, 10) is CursorKind.ARROW  # the usual mouse while drawing
    with qtbot.waitSignal(tool.changed):
        view.left_pressed.emit(10.0, 10.0)
    assert tool.editor.state is TemplateState.LOOPING
    for x, y in PILLOW[1:]:
        view.left_pressed.emit(float(x), float(y))
    near_first = 10 + net_style.VERTEX_RADIUS_PX / 2 / view.scale_factor()
    view.mouse_moved.emit(near_first, 10.0)
    assert tool.item.rubber() == (Vec(10, 11), Vec(10, 10))  # the line ends at the first vertex: a click closes it
    assert tool.item.highlight_vertex() == Vec(10, 10)
    view.left_pressed.emit(near_first, 10.0)
    assert tool.editor.state is TemplateState.FINALIZATION
    assert tool.item.midpoints_shown()


def test_the_first_vertex_closes_only_3_segments(setup: tuple[SheetView, TemplateTool]) -> None:
    view, tool = setup
    view.left_pressed.emit(10.0, 10.0)
    view.left_pressed.emit(11.0, 10.0)
    view.left_pressed.emit(10.0, 10.0)  # not a vertex to snap to yet: a point on the first one, refused
    assert len(tool.editor.template.vertices) == 2


def test_a_crossing_is_refused_and_flashes(setup: tuple[SheetView, TemplateTool], qtbot: QtBot) -> None:
    view, tool = setup
    for x, y in [(10, 10), (12, 10), (12, 12)]:
        view.left_pressed.emit(float(x), float(y))
    with qtbot.waitSignal(tool.rejected) as blocker:
        view.left_pressed.emit(11.0, 9.0)
    assert blocker.args[1] is TemplateProblem.CROSSING
    assert tool.item.flash() == ((Vec(12, 12), Vec(11, 9)),)
    qtbot.waitUntil(lambda: tool.item.flash() == (), timeout=FLASH_MS * 5)


def test_shift_makes_the_segment_straight(
    setup: tuple[SheetView, TemplateTool], monkeypatch: pytest.MonkeyPatch
) -> None:
    view, tool = setup
    view.left_pressed.emit(10.0, 10.0)
    monkeypatch.setattr(view, "shift_held", lambda: True)
    view.left_pressed.emit(12.0, 10.3)
    assert tool.editor.template.vertices[-1].position == Vec(12, 10)


def test_dragging_a_vertex_moves_it(setup: tuple[SheetView, TemplateTool]) -> None:
    view, tool = setup
    drawn(view, tool)
    view.left_pressed.emit(11.0, 11.0)
    view.mouse_moved.emit(11.0, 11.5)
    assert tool.dragging and tool.cursor_at(11.0, 11.5) is CursorKind.PENCIL
    view.left_released.emit(11.0, 11.5)
    assert tool.editor.template.position(4) == Vec(11, F(23, 2))
    assert not tool.dragging


def test_a_drag_that_breaks_the_loop_goes_back(setup: tuple[SheetView, TemplateTool], qtbot: QtBot) -> None:
    view, tool = setup
    drawn(view, tool)
    view.left_pressed.emit(11.0, 11.0)
    view.mouse_moved.emit(11.0, 9.5)
    with qtbot.waitSignal(tool.rejected):
        view.left_released.emit(11.0, 9.5)
    assert tool.editor.template.position(4) == Vec(11, 11)


def test_a_click_on_a_vertex_then_another_is_a_fold(setup: tuple[SheetView, TemplateTool]) -> None:
    view, tool = setup
    drawn(view, tool)
    click(view, 11.0, 10.0)
    view.mouse_moved.emit(11.0, 10.5)
    assert tool.item.rubber() == (Vec(11, 10), Vec(11, F(21, 2)))
    view.left_pressed.emit(11.0, 11.0)
    assert tool.editor.template.folds == (Fold(1, 4),)
    assert tool.item.rubber() is None


def test_a_fold_given_up(setup: tuple[SheetView, TemplateTool]) -> None:
    view, tool = setup
    drawn(view, tool)
    click(view, 11.0, 10.0)
    tool.cancel()  # Escape
    view.left_pressed.emit(11.0, 11.0)
    assert tool.editor.template.folds == ()


def test_the_middle_circle_inserts_a_vertex(setup: tuple[SheetView, TemplateTool]) -> None:
    view, tool = setup
    drawn(view, tool)
    assert tool.cursor_at(11.5, 11.0) is CursorKind.PLUS
    click(view, 11.5, 11.0)
    assert len(tool.editor.template.vertices) == 7


def test_ctrl_click_deletes(
    setup: tuple[SheetView, TemplateTool], monkeypatch: pytest.MonkeyPatch, qtbot: QtBot
) -> None:
    view, tool = setup
    drawn(view, tool)
    monkeypatch.setattr(view, "press_modifiers", lambda: Qt.KeyboardModifier.ControlModifier)
    with qtbot.waitSignal(tool.warned):  # only 6: none can go
        view.left_pressed.emit(11.0, 10.0)
    assert len(tool.editor.template.vertices) == 6
    monkeypatch.setattr(view, "press_modifiers", lambda: Qt.KeyboardModifier.NoModifier)
    click(view, 11.5, 11.0)  # a seventh vertex
    click(view, 11.0, 10.0)
    view.left_pressed.emit(11.0, 11.0)  # and a fold 1-4
    monkeypatch.setattr(view, "press_modifiers", lambda: Qt.KeyboardModifier.ControlModifier)
    monkeypatch.setattr(view, "ctrl_held", lambda: True)
    assert tool.cursor_at(11.0, 10.5) is CursorKind.DELETE
    view.left_pressed.emit(11.0, 10.5)  # on the fold
    assert tool.editor.template.folds == ()
    view.left_pressed.emit(11.5, 11.0)  # the seventh vertex
    assert len(tool.editor.template.vertices) == 6


def test_a_click_in_a_face_asks_for_its_colour(setup: tuple[SheetView, TemplateTool], qtbot: QtBot) -> None:
    view, tool = setup
    drawn(view, tool)
    with qtbot.waitSignal(tool.face_clicked) as blocker:
        view.left_pressed.emit(10.4, 10.6)
    assert blocker.args == [0]
    tool.set_face_color(0, "#123456")
    assert tool.editor.template.faces[0].color == "#123456"


def test_undo_and_redo(setup: tuple[SheetView, TemplateTool]) -> None:
    view, tool = setup
    drawn(view, tool)
    tool.undo()
    assert tool.editor.state is TemplateState.LOOPING
    tool.redo()
    assert tool.editor.state is TemplateState.FINALIZATION


def test_place_a_vertex(setup: tuple[SheetView, TemplateTool]) -> None:
    _, tool = setup
    placement = tool.placement_at(10.0, 10.0)
    assert placement is not None
    assert tool.place(placement, Vec(F(21, 2), 10)) is None
    assert tool.editor.template.vertices[0].position == Vec(F(21, 2), 10)
    placement = tool.placement_at(9.0, 9.0)
    assert placement is not None
    assert tool.place(placement, Vec(200, 10)) == template_problem_text(TemplateProblem.OFF_THE_SHEET)


def test_the_menu_and_the_coordinates(setup: tuple[SheetView, TemplateTool]) -> None:
    view, tool = setup
    assert tool.menu_offered(None)  # drawing: Place a vertex, Set slope
    drawn(view, tool)
    assert not tool.menu_offered(None)
    assert tool.vertex_at(11.0, 10.0) == Vec(11, 10)
    assert tool.menu_offered(Vec(11, 10))
    assert tool.coordinates_at(11.5, 11.0) == Vec(F(23, 2), 11)  # a middle circle: where the new vertex would be
