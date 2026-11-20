# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest
from PyQt6.QtCore import QPointF, Qt
from pytestqt.qtbot import QtBot

from cube_net.core.cutting.placement import Action
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


def test_a_fold_line_through_points(setup: tuple[SheetView, TemplateTool]) -> None:
    """From the bottom middle up through a point inside, to the top middle (docs/template_plan.md, §8.4)."""
    view, tool = setup
    drawn(view, tool)
    click(view, 11.0, 10.0)
    view.left_pressed.emit(11.25, 10.5)  # a fold vertex
    assert tool.item.pending() == (Vec(11, 10), Vec(F(45, 4), F(21, 2)))
    view.mouse_moved.emit(11.0, 10.75)
    assert tool.item.rubber() == (Vec(F(45, 4), F(21, 2)), Vec(11, F(43, 4)))  # on from the last point
    assert tool.busy()
    view.left_pressed.emit(11.0, 11.0)
    template = tool.editor.template
    assert template.folds == (Fold(1, 6), Fold(6, 4)) and len(template.faces) == 2
    assert tool.item.pending() == () and not tool.busy()


def test_the_coordinates_over_a_fold_segments_middle(setup: tuple[SheetView, TemplateTool]) -> None:
    """Over the middle circle of a fold (its index past the loop's sides), the hint shows that middle: it used to
    look the segment up among the loop's sides only, and crash (weird_cube.nettemplate, 2026-11-19)."""
    view, tool = setup
    drawn(view, tool)
    click(view, 11.0, 10.0)
    view.left_pressed.emit(11.0, 11.0)
    assert tool.coordinates_at(11.0, 10.5) == Vec(11, F(21, 2))


def test_a_fold_point_outside_gives_the_line_up(setup: tuple[SheetView, TemplateTool]) -> None:
    view, tool = setup
    drawn(view, tool)
    click(view, 11.0, 10.0)
    view.left_pressed.emit(11.25, 10.5)
    view.left_pressed.emit(11.0, 12.0)  # outside the net
    assert not tool.busy() and tool.editor.template.folds == ()


def test_a_fold_vertex_inserted_dragged_and_deleted(setup: tuple[SheetView, TemplateTool]) -> None:
    view, tool = setup
    drawn(view, tool)
    click(view, 11.0, 10.0)
    view.left_pressed.emit(11.0, 11.0)
    assert tool.cursor_at(11.0, 10.5) is CursorKind.PLUS  # the fold's middle circle
    click(view, 11.0, 10.5)
    template = tool.editor.template
    assert len(template.fold_vertices) == 1 and len(template.folds) == 2
    view.left_pressed.emit(11.0, 10.5)  # drag the new fold vertex right
    view.mouse_moved.emit(11.25, 10.5)
    view.left_released.emit(11.25, 10.5)
    assert tool.editor.template.fold_vertices[0].position == Vec(F(45, 4), F(21, 2))
    tool._delete_at(11.25, 10.5)  # Ctrl+click on it: the fold is one segment again
    assert tool.editor.template.folds == (Fold(1, 4),) and len(tool.editor.template.faces) == 2


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


def test_with_ctrl_a_fold_is_highlighted_only_where_a_click_deletes_it(
    setup: tuple[SheetView, TemplateTool], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Over a fold vertex, Ctrl+click deletes the vertex: none of its segments lights up (2026-11-20)."""
    view, tool = setup
    drawn(view, tool)
    click(view, 11.0, 10.0)
    view.left_pressed.emit(11.25, 10.5)  # a fold vertex
    view.left_pressed.emit(11.0, 11.0)
    monkeypatch.setattr(view, "ctrl_held", lambda: True)
    view.mouse_moved.emit(11.25, 10.5)  # on the fold vertex
    assert tool.item.highlight_fold() is None and tool.cursor_at(11.25, 10.5) is CursorKind.DELETE
    view.mouse_moved.emit(11.125, 10.25)  # in the middle of a segment of the line
    assert tool.item.highlight_fold() == (Vec(11, 10), Vec(F(45, 4), F(21, 2)))


def test_a_double_click_in_a_face_asks_for_its_colour(setup: tuple[SheetView, TemplateTool], qtbot: QtBot) -> None:
    view, tool = setup
    drawn(view, tool)
    with qtbot.waitSignal(tool.face_double_clicked) as blocker:
        view.left_double_clicked.emit(10.4, 10.6)
    assert blocker.args == [0]
    tool.set_face_color(0, "#123456")
    assert tool.editor.template.faces[0].color == "#123456"


def test_a_click_in_a_face_drags_the_sheet(setup: tuple[SheetView, TemplateTool], qtbot: QtBot) -> None:
    view, tool = setup
    drawn(view, tool)
    assert not tool.claims(10.4, 10.6)  # the view pans
    asked: list[int] = []
    tool.face_double_clicked.connect(asked.append)
    click(view, 10.4, 10.6)
    assert asked == []


def test_a_double_click_on_a_vertex_or_while_folding_asks_nothing(
    setup: tuple[SheetView, TemplateTool], qtbot: QtBot
) -> None:
    view, tool = setup
    drawn(view, tool)
    asked: list[int] = []
    tool.face_double_clicked.connect(asked.append)
    view.left_double_clicked.emit(10.0, 10.0)  # on a vertex
    click(view, 10.0, 10.0)  # a fold starts there
    view.left_double_clicked.emit(10.4, 10.6)
    assert asked == []


def test_a_real_double_click(setup: tuple[SheetView, TemplateTool], qtbot: QtBot) -> None:
    from PyQt6.QtCore import QPoint

    view, tool = setup
    drawn(view, tool)
    p = view.from_sheet(QPointF(10.4, 10.6))
    with qtbot.waitSignal(tool.face_double_clicked):
        qtbot.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(round(p.x()), round(p.y())))


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
    assert tool.placement_at(11.5, 10.5) is not None  # drawing: Place a vertex
    drawn(view, tool)
    assert tool.placement_at(11.5, 10.5) is None and tool.slope_at(11.5, 10.5) is None
    assert tool.vertex_at(11.5, 10.5) is None  # inside the net, nothing drawn: no item, so no menu
    assert tool.vertex_at(11.0, 10.0) == Vec(11, 10)  # Move the origin
    assert tool.coordinates_at(11.5, 11.0) == Vec(F(23, 2), 11)  # a middle circle: where the new vertex would be


def test_while_drawing_a_vertex_is_one_for_the_menu(setup: tuple[SheetView, TemplateTool]) -> None:
    """Move the origin on the loop's vertices before it's closed; Assign the vertex only after."""
    from cube_net.ui.sheet.sheet_context_menu import ASSIGN_VERTEX, MOVE_ORIGIN, SheetContextMenu

    view, tool = setup
    view.left_pressed.emit(10.0, 10.0)
    assert tool.vertex_at(10.0, 10.0) == Vec(10, 10)
    assert tool.coordinates_at(10.0, 10.0) == Vec(10, 10)
    menu = SheetContextMenu(view, tool, assign=lambda _p: None)
    shown = menu.menu(tool.placement_at(10.0, 10.0), None, tool.vertex_at(10.0, 10.0))
    assert shown.items[MOVE_ORIGIN].enabled and not shown.items[ASSIGN_VERTEX].enabled
    shown.deleteLater()
    tool.move_origin(tool.editor.origin.moved(Vec(10, 10), Vec(0, 0), None))
    assert tool.editor.origin.shown(Vec(10, 10)) == Vec(0, 0)
    assert tool.editor.state is TemplateState.LOOPING
    tool.undo()
    assert tool.editor.origin.shown(Vec(10, 10)) == Vec(10, 10)
    assert len(tool.editor.template.vertices) == 1  # only the move was undone


def test_assign_the_vertex_once_the_loop_is_closed(setup: tuple[SheetView, TemplateTool]) -> None:
    from cube_net.ui.sheet.sheet_context_menu import ASSIGN_VERTEX, SheetContextMenu

    view, tool = setup
    assert not tool.can_assign()
    drawn(view, tool)
    assert tool.can_assign()
    menu = SheetContextMenu(view, tool, assign=lambda _p: None)
    shown = menu.menu(None, None, tool.vertex_at(11.0, 10.0))
    assert shown.items[ASSIGN_VERTEX].enabled
    shown.deleteLater()
    view.left_pressed.emit(11.0, 10.0)
    view.mouse_moved.emit(11.0, 9.5)  # dragging it
    assert not tool.can_assign()


def test_vertices_at_one_point_are_picked_by_direction(setup: tuple[SheetView, TemplateTool]) -> None:
    """A square with a triangular hole whose top corner touches the top side at (12, 14): T_1 and T_2 share that
    point; the mouse picks by direction."""
    from cube_net.ui.template.corners import owned_arcs

    view, tool = setup
    view.show_initial_view(Box(Vec(9, 9), Vec(15, 15)))
    loop = [(10, 10), (14, 10), (14, 14), (12, 14), (13, 12), (11, 12), (12, 14), (10, 14)]
    for x, y in [*loop, loop[0]]:
        view.left_pressed.emit(float(x), float(y))
    assert tool.editor.state is TemplateState.FINALIZATION
    t1, t2 = 3, 6  # in the order drawn
    step = net_style.VERTEX_RADIUS_PX / 2 / view.scale_factor()
    assert tool.vertex_id_at(12 + step, 14 - step / 3) == t1  # right of the hole
    assert tool.vertex_id_at(12 - step, 14 - step / 3) == t2  # left of it
    assert tool.vertex_id_at(12, 14 - step) is None  # in the hole
    view.mouse_moved.emit(12 + step, 14 - step / 3)
    assert tool.item.highlight_vertex() == Vec(12, 14)
    assert tool.item.highlight_arcs() == owned_arcs(tool.editor.template, t1)


class TestHoles:
    """Draw hole in a 4 x 3 rectangle (docs/template_plan.md, §8.5)."""

    RECTANGLE = ((10, 10), (14, 10), (14, 13), (10, 13))

    def rectangle(self, view: SheetView, tool: TemplateTool) -> None:
        for x, y in [*self.RECTANGLE, self.RECTANGLE[0]]:
            view.left_pressed.emit(float(x), float(y))
        assert tool.editor.state is TemplateState.FINALIZATION

    def test_drawn_and_closed_by_clicks(self, setup: tuple[SheetView, TemplateTool]) -> None:
        view, tool = setup
        self.rectangle(view, tool)
        assert tool.can_start_hole()
        tool.start_hole()
        assert tool.drawing_hole and not tool.can_start_hole() and tool.claims(9.0, 9.0)
        assert not tool.item.midpoints_shown()
        for x, y in [(11, 11), (13, 11), (13, 12)]:
            view.left_pressed.emit(float(x), float(y))
        view.mouse_moved.emit(11.0, 12.0)
        assert tool.item.rubber() == (Vec(13, 12), Vec(11, 12))  # on from the hole's last point
        view.left_pressed.emit(11.0, 12.0)
        assert tool.placement_at(12.0, 12.5) is not None and tool.slope_at(12.0, 12.5) is not None  # Place, Set slope
        view.left_pressed.emit(11.0, 11.0)  # its first vertex closes it
        assert not tool.drawing_hole and tool.editor.template.holes[0].closed
        assert tool.item.midpoints_shown()

    def test_escape_before_the_first_point(self, setup: tuple[SheetView, TemplateTool]) -> None:
        view, tool = setup
        self.rectangle(view, tool)
        tool.start_hole()
        tool.cancel()
        assert not tool.drawing_hole
        view.left_pressed.emit(12.0, 12.0)  # an ordinary click again: nothing
        assert tool.editor.template.holes == ()

    def test_a_point_outside_the_net_is_refused(self, setup: tuple[SheetView, TemplateTool], qtbot: QtBot) -> None:
        view, tool = setup
        self.rectangle(view, tool)
        tool.start_hole()
        with qtbot.waitSignal(tool.rejected):
            view.left_pressed.emit(16.0, 12.0)
        assert tool.editor.template.holes == () and tool.drawing_hole

    def test_a_typed_point(self, setup: tuple[SheetView, TemplateTool]) -> None:
        view, tool = setup
        self.rectangle(view, tool)
        tool.start_hole()
        placement = tool.placement_at(11.0, 11.0)
        assert placement is not None
        assert tool.place(placement, Vec(F(23, 2), F(23, 2))) is None
        assert tool.editor.template.holes[0].vertices[0].position == Vec(F(23, 2), F(23, 2))

    def test_the_right_click_menu_while_drawing_a_hole(self, setup: tuple[SheetView, TemplateTool]) -> None:
        """Place a vertex and Set slope, as while drawing the loop (asked for on 2026-11-19)."""
        view, tool = setup
        self.rectangle(view, tool)
        tool.start_hole()
        assert not tool.can_assign()
        start = tool.placement_at(11.0, 11.0)
        assert start is not None and start.action is Action.START and tool.slope_at(11.0, 11.0) is None
        view.left_pressed.emit(11.0, 11.0)
        assert tool.slope_at(13.0, 12.0) == Vec(2, 1)
        tool.lock_slope(Vec(2, 1))
        placement = tool.placement_at(12.0, 13.0)
        assert placement is not None and placement.action is Action.ADD
        assert tool.place(placement, Vec(13, 12)) is None  # on the locked slope's line
        assert [v.position for v in tool.editor.template.holes[0].vertices] == [Vec(11, 11), Vec(13, 12)]
        assert tool.slope is None  # placing it used the lock up, as for the loop
        view.left_pressed.emit(12.0, 12.5)
        assert len(tool.editor.template.holes[0].vertices) == 3


def test_the_right_click_menu_while_drawing_a_fold_line(setup: tuple[SheetView, TemplateTool]) -> None:
    """Place a vertex and Set slope for the line's next point, as for the loop's (2026-11-20: there was no menu)."""
    from cube_net.ui.sheet.sheet_context_menu import SheetContextMenu

    view, tool = setup
    drawn(view, tool)
    menu = SheetContextMenu(view, tool)
    assert not menu.offered_at(11.5, 10.5)  # inside a face, nothing drawn: nothing to choose
    click(view, 11.0, 10.0)  # a fold line starts at (11, 10)
    assert [item.enabled for item in menu.items_at(11.5, 10.5)] == [True, True, False]
    placement = tool.placement_at(11.5, 10.5)
    assert placement is not None and placement.action is Action.ADD
    assert tool.slope_at(12.0, 11.0) == Vec(1, 1)
    tool.lock_slope(Vec(1, 2))
    assert tool.coordinates_at(12.0, 10.5) == Vec(F(57, 5), F(54, 5))  # on the slope's line, nearest the mouse
    assert tool.place(placement, Vec(F(45, 4), F(21, 2))) is None  # typed: the line's next point
    assert tool.slope is None  # unlocked once the point is there, as for the loop
    assert tool.placement_at(11.0, 11.0) is None  # on a vertex: a click ends the line there, nothing to type
    assert menu.offered_at(11.0, 11.0)  # but Set slope and Move the origin are there
    click(view, 11.0, 11.0)
    assert len(tool.editor.template.fold_vertices) == 1 and len(tool.editor.template.faces) == 2
