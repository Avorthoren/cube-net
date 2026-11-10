# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec, quantize
from cube_net.core.net import Net, default_net
from cube_net.core.sheet import sheet_box
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.cut_tool import FLASH_MS, CutTool
from cube_net.ui.sheet.ruler_tool import RulerTool
from cube_net.ui.sheet.sheet_view import SheetView


@pytest.fixture
def setup(qtbot: QtBot) -> tuple[SheetView, CutTool, RulerTool]:
    net: Net = default_net()
    view = SheetView()
    qtbot.addWidget(view)
    view.resize(800, 600)
    view.set_sheet(sheet_box(v.position for v in net.vertices))
    view.set_net(net)
    view.set_press_claim(lambda x, y: net.contains(quantize(x, y)))
    view.show_initial_view(net.bounding_box())
    view.show()
    qtbot.waitExposed(view)
    ruler = RulerTool(view)
    return view, CutTool(view, Editor(net), ruler), ruler


def just_inside_top_of_face_1(view: SheetView) -> tuple[float, float]:
    """Half a hitbox below the cut B_1-A_1 (y = 14), in the middle of it."""
    return 11.5, 14 - net_style.CUT_HITBOX_PX / 2 / view.scale_factor()


def test_click_on_a_cut_starts_the_line(setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
    view, tool, _ = setup
    with qtbot.waitSignal(tool.point_added) as blocker:
        view.left_pressed.emit(*just_inside_top_of_face_1(view))
    assert blocker.args == [Vec(F(115, 10), 14)]  # projected onto the cut
    assert tool.editor.state is EditorState.CUTTING
    assert [p.position for p in tool.item.points()] == [Vec(F(115, 10), 14)]


def test_rubber_band_follows_the_mouse_while_cutting(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, ruler = setup
    view.mouse_moved.emit(11.5, 12.5)
    assert tool.item.rubber_band() is None  # not cutting yet
    view.left_pressed.emit(*just_inside_top_of_face_1(view))
    view.mouse_moved.emit(11.5, 12.5)
    assert tool.item.rubber_band() == (Vec(F(115, 10), 14), Vec(F(115, 10), F(125, 10)))
    ruler.set_active(True)
    view.mouse_moved.emit(11.6, 12.5)
    assert tool.item.rubber_band() is None  # hidden while the ruler is active


def test_ruler_takes_the_clicks(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, ruler = setup
    ruler.set_active(True)
    view.left_pressed.emit(*just_inside_top_of_face_1(view))
    assert tool.editor.state is EditorState.DEFAULT
    assert len(ruler.ruler.points) == 1


def test_rejected_click_flashes_black_for_a_moment(setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
    view, tool, _ = setup
    view.left_pressed.emit(*just_inside_top_of_face_1(view))
    with qtbot.waitSignal(tool.rejected):
        view.left_pressed.emit(12.5, 13.5)  # outside the net
    assert tool.item.flash() == ((Vec(F(115, 10), 14), Vec(F(125, 10), F(135, 10))),)
    qtbot.waitUntil(lambda: tool.item.flash() is None, timeout=FLASH_MS + 500)
    assert len(tool.item.points()) == 1


def test_whole_line_to_cut_editing(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    view.left_pressed.emit(*just_inside_top_of_face_1(view))
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - net_style.CUT_HITBOX_PX / 2 / view.scale_factor(), 13.5)  # on D_1-B_1
    assert tool.editor.state is EditorState.CUT_EDITING
    assert tool.item.points()[-1].position == Vec(12, F(135, 10))
    view.mouse_moved.emit(11.7, 13.2)
    assert tool.item.rubber_band() is None  # no rubber band once the line is closed


def test_area_contains_the_sheet(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    assert tool.item.boundingRect().contains(view.sheet_rect())


def test_click_inside_a_vertex_circle_uses_the_vertex(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    near = net_style.VERTEX_RADIUS_PX / 2 / view.scale_factor()
    view.left_pressed.emit(11 + near, 13 - near)  # inside C_1's circle (and inside face 2)
    assert [p.position for p in tool.item.points()] == [Vec(11, 13)]
    view.mouse_moved.emit(12 - near, 12 + near)  # inside G_1's circle: the rubber band snaps to G_1
    assert tool.item.rubber_band() == (Vec(11, 13), Vec(12, 12))


def click_at(view: SheetView, qtbot: QtBot, x: float, y: float, shift: bool = False) -> None:
    modifier = Qt.KeyboardModifier.ShiftModifier if shift else Qt.KeyboardModifier.NoModifier
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, modifier, view.from_sheet(QPointF(x, y)).toPoint())


def drag_to(view: SheetView, start: tuple[float, float], end: tuple[float, float]) -> None:
    """Press, move and release through the view's signals, at exact sheet positions."""
    view.left_pressed.emit(*start)
    view.mouse_moved.emit(*end)
    view.left_released.emit(*end)


def corner_cut(view: SheetView) -> None:
    """x (11.5, 14), y (11.5, 13.5), z (12, 13.5)."""
    inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.left_pressed.emit(11.5, 14 - inside)
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(12 - inside, 13.5)


def positions(tool: CutTool) -> list[Vec]:
    return [p.position for p in tool.item.points()]


X, Y, Z = Vec(F(23, 2), 14), Vec(F(23, 2), F(27, 2)), Vec(12, F(27, 2))


def test_midpoints_shown_only_in_cut_editing(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    view.left_pressed.emit(*just_inside_top_of_face_1(view))
    view.left_pressed.emit(11.5, 13.5)
    assert tool.item.midpoints() == []
    view.left_pressed.emit(12 - net_style.CUT_HITBOX_PX / 2 / view.scale_factor(), 13.5)
    assert tool.item.midpoints() == [(X + Y) / 2, (Y + Z) / 2]


def test_click_on_a_midpoint_inserts_a_point(setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
    view, tool, _ = setup
    corner_cut(view)
    with qtbot.waitSignal(tool.edited) as blocker:
        click_at(view, qtbot, 11.5, 13.75)
    assert positions(tool) == [X, (X + Y) / 2, Y, Z]
    assert blocker.args == ["insert", 1, (X + Y) / 2]


def test_shift_click_deletes_an_inner_point(setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
    view, tool, _ = setup
    corner_cut(view)
    with qtbot.waitSignal(tool.edited) as blocker:
        click_at(view, qtbot, 11.5, 13.5, shift=True)
    assert positions(tool) == [X, Z]
    assert blocker.args == ["delete", 1, Y]


def test_shift_click_on_an_end_does_nothing(setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
    view, tool, _ = setup
    corner_cut(view)
    click_at(view, qtbot, 12, 13.5, shift=True)
    assert positions(tool) == [X, Y, Z]


def test_rejected_delete_flashes_the_shortcut_then_restores(
    setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
) -> None:
    view, tool, _ = setup
    inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.left_pressed.emit(10.5, 13 - inside)  # on C_1-A_2
    view.left_pressed.emit(11.2, 12.8)
    view.left_pressed.emit(11.5, 13.5)
    view.left_pressed.emit(11.5, 14 - inside)
    before = positions(tool)
    with qtbot.waitSignal(tool.rejected):
        click_at(view, qtbot, 11.2, 12.8, shift=True)
    assert positions(tool) == [before[0], before[2], before[3]]  # P2 and its segments hidden...
    assert tool.item.flash() == ((before[0], before[2]),)  # ...and the shortcut black
    assert tool.item.midpoints() == []
    qtbot.waitUntil(lambda: tool.item.flash() is None, timeout=FLASH_MS + 500)
    assert positions(tool) == before  # back as it was
    assert len(tool.editor.cut_line.points) == 4  # type: ignore[union-attr]


def test_dragging_a_point_previews_then_commits_on_release(
    setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
) -> None:
    view, tool, _ = setup
    corner_cut(view)
    view.left_pressed.emit(11.5, 13.5)
    view.mouse_moved.emit(11.3, 13.25)
    target = Vec(F(113, 10), F(53, 4))
    assert positions(tool) == [X, target, Z]  # on display...
    assert tool.editor.cut_line is not None
    assert tool.editor.cut_line.points[1].position == Y  # ...but not in the editor yet
    with qtbot.waitSignal(tool.edited) as blocker:
        view.left_released.emit(11.3, 13.25)
    assert blocker.args == ["move", 1, target]
    assert tool.editor.cut_line.points[1].position == target


def test_rejected_drag_flashes_and_goes_back(setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
    view, tool, _ = setup
    corner_cut(view)
    with qtbot.waitSignal(tool.rejected):
        drag_to(view, (11.5, 13.5), (10.5, 13.5))  # into the empty corner
    assert positions(tool) == [X, Y, Z]
    bad = Vec(F(21, 2), F(27, 2))
    assert tool.item.flash() == ((X, bad), (bad, Z))
    qtbot.waitUntil(lambda: tool.item.flash() is None, timeout=FLASH_MS + 500)


def test_a_click_without_moving_changes_nothing(setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
    view, tool, _ = setup
    corner_cut(view)
    with qtbot.assertNotEmitted(tool.edited):
        view.left_pressed.emit(11.5, 13.5)
        view.left_released.emit(11.5, 13.5)
    assert positions(tool) == [X, Y, Z]


def test_endpoint_drag_shows_its_image_following(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    corner_cut(view)
    assert Vec(F(23, 2), 10) in tool.item.images()
    drag_to(view, (11.5, 14), (11.75, 14.2))  # slides along A_1-B_1
    assert positions(tool)[0] == Vec(F(47, 4), 14)
    assert Vec(F(47, 4), 10) in tool.item.images()  # the image on A_3-B_3 moved with it


def test_the_ruler_takes_presses_while_editing(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, ruler = setup
    corner_cut(view)
    assert tool.claims(11.5, 13.5)
    ruler.set_active(True)
    assert not tool.claims(11.5, 13.5)
    view.left_pressed.emit(11.5, 13.75)  # a midpoint, but the ruler is on
    assert positions(tool) == [X, Y, Z]
    assert len(ruler.ruler.points) == 1


class TestClaims:
    """Where a press means something, per state; anywhere else a drag pans the sheet."""

    MIDDLE_OF_FACE_2 = 11.5, 12.5

    def test_default_the_perimeter(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        assert tool.claims(10 + h, 12.5) and tool.claims(10, 13)  # a cut, a vertex
        assert not tool.claims(*self.MIDDLE_OF_FACE_2) and not tool.claims(7, 7)

    def test_cutting_the_whole_net(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        view.left_pressed.emit(*just_inside_top_of_face_1(view))
        assert tool.claims(*self.MIDDLE_OF_FACE_2) and tool.claims(10, 13)
        assert not tool.claims(7, 7)

    def test_cut_editing_the_line_and_the_cuts(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        corner_cut(view)
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        assert tool.claims(11.5, 14) and tool.claims(11.5, 13.75) and tool.claims(10 + h, 12.5)
        assert not tool.claims(*self.MIDDLE_OF_FACE_2) and not tool.claims(10, 13) and not tool.claims(7, 7)

    def test_cut_approving_only_the_button(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        rearranged_corner_cut(view)
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        assert tool.claims(*MIDDLE_OF_X2_B3)
        assert not tool.claims(*self.MIDDLE_OF_FACE_2) and not tool.claims(10 + h, 12.5) and not tool.claims(10, 13)

    def test_nothing_for_the_ruler(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        _, tool, ruler = setup
        ruler.set_active(True)
        assert not tool.claims(10, 13)


def half_fold_hitbox(view: SheetView) -> float:
    return net_style.FOLD_HITBOX_PX / 4 / view.scale_factor()


def test_click_in_a_fold_hitbox_lands_on_the_fold(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    view.left_pressed.emit(*just_inside_top_of_face_1(view))
    view.left_pressed.emit(11.5, 13 + half_fold_hitbox(view))  # just above C_1-D_1
    assert positions(tool) == [X, Vec(F(23, 2), 13)]
    assert tool.item.points()[1].fold is not None


def test_rubber_band_snaps_to_a_fold(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    view.left_pressed.emit(*just_inside_top_of_face_1(view))
    view.mouse_moved.emit(11.5, 13 - half_fold_hitbox(view))
    assert tool.item.rubber_band() == (X, Vec(F(23, 2), 13))


def test_drag_snaps_to_a_fold_stays_along_it_and_leaves_it(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    corner_cut(view)
    near = half_fold_hitbox(view)
    view.left_pressed.emit(11.5, 13.5)
    view.mouse_moved.emit(11.5, 13 + near)  # into the hitbox of C_1-D_1
    assert tool.item.points()[1].position == Vec(F(23, 2), 13)
    view.mouse_moved.emit(11.75, 13 - near)  # along it, on the other side of the line
    assert tool.item.points()[1].position == Vec(F(47, 4), 13)
    view.mouse_moved.emit(11.75, 13.25)  # out of the hitbox: free again
    assert tool.item.points()[1].position == Vec(F(47, 4), F(53, 4))
    assert tool.item.points()[1].fold is None
    view.left_released.emit(11.75, 13.25)


def test_inner_point_released_over_a_perimeter_hitbox_is_rejected(
    setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
) -> None:
    view, tool, _ = setup
    corner_cut(view)
    inside_hitbox = 11.5, 14 - net_style.CUT_HITBOX_PX / 2 / view.scale_factor()  # under the cut A_1-B_1
    with qtbot.waitSignal(tool.rejected):
        drag_to(view, (11.5, 13.5), inside_hitbox)
    assert positions(tool) == [X, Y, Z]
    assert tool.item.flash() is not None
    qtbot.waitUntil(lambda: tool.item.flash() is None, timeout=FLASH_MS + 500)


def test_inner_point_released_in_a_vertex_circle_is_rejected(
    setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
) -> None:
    view, tool, _ = setup
    corner_cut(view)
    near = net_style.VERTEX_RADIUS_PX / 2 / view.scale_factor()
    with qtbot.waitSignal(tool.rejected):
        drag_to(view, (11.5, 13.5), (11 + near, 14 - near))  # in A_1's circle
    assert positions(tool) == [X, Y, Z]


def test_endpoint_released_in_a_vertex_circle_lands_on_that_vertex(
    setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
) -> None:
    view, tool, _ = setup
    corner_cut(view)
    near = net_style.VERTEX_RADIUS_PX / 2 / view.scale_factor()
    with qtbot.waitSignal(tool.edited):
        drag_to(view, (11.5, 14), (11 + near, 14 - near))  # the start, into A_1's circle
    assert positions(tool)[0] == Vec(11, 14)
    assert tool.item.points()[0].vertex is not None
    assert Vec(F(23, 2), 10) not in tool.item.images()  # at a vertex there is no separate image any more


def test_endpoint_walks_past_a_vertex_in_one_drag(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    """Replay of the bug report: an end on H_1-E_1, dragged down past E_1 without releasing."""
    view, tool, _ = setup
    inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
    view.left_pressed.emit(12, 13)  # D_1
    view.left_pressed.emit(11 + inside, 11.373)
    view.left_pressed.emit(11 + inside, 11.373)
    for y in (11.3, 11.1, 10.9, 10.713):
        view.mouse_moved.emit(11.03, y)
    assert positions(tool)[1] == Vec(11, F(10713, 1000))
    view.left_released.emit(11.03, 10.713)
    assert tool.editor.cut_line is not None
    assert tool.editor.cut_line.points[1].position == Vec(11, F(10713, 1000))


def highlighted_fold_ends(view: SheetView) -> set[Vec] | None:
    item = view.net_item()
    assert item is not None
    fold = item.highlight_fold()
    return None if fold is None else {fold.origin.position, fold.destination.position}


C_D = {Vec(11, 13), Vec(12, 13)}


def test_fold_highlighted_while_cutting(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, _, ruler = setup
    view.mouse_moved.emit(11.5, 13 + half_fold_hitbox(view))
    assert highlighted_fold_ends(view) is None  # DEFAULT: a click on a fold means nothing
    view.left_pressed.emit(*just_inside_top_of_face_1(view))
    view.mouse_moved.emit(11.5, 13 + half_fold_hitbox(view))
    assert highlighted_fold_ends(view) == C_D
    view.mouse_moved.emit(11.5, 13.5)
    assert highlighted_fold_ends(view) is None
    view.mouse_moved.emit(11.5, 13 - half_fold_hitbox(view))
    assert highlighted_fold_ends(view) == C_D
    view.mouse_left.emit()
    assert highlighted_fold_ends(view) is None
    view.mouse_moved.emit(11.5, 13 + half_fold_hitbox(view))
    ruler.set_active(True)
    assert highlighted_fold_ends(view) is None  # the ruler takes the clicks
    view.mouse_moved.emit(11.5, 13 + half_fold_hitbox(view))
    assert highlighted_fold_ends(view) is None


def test_fold_highlighted_while_dragging_an_inner_point_only(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, _, _ = setup
    corner_cut(view)
    view.mouse_moved.emit(11.5, 13 + half_fold_hitbox(view))
    assert highlighted_fold_ends(view) is None  # not dragging: a click here means nothing
    view.left_pressed.emit(11.5, 13.5)
    view.mouse_moved.emit(11.5, 13 + half_fold_hitbox(view))
    assert highlighted_fold_ends(view) == C_D
    view.left_released.emit(11.5, 13 + half_fold_hitbox(view))
    assert highlighted_fold_ends(view) is None


def test_ending_the_line_clears_the_fold_highlight(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, _, _ = setup
    view.left_pressed.emit(*just_inside_top_of_face_1(view))
    view.left_pressed.emit(11.5, 13.5)
    view.mouse_moved.emit(11.5, 13 + half_fold_hitbox(view))
    assert highlighted_fold_ends(view) == C_D
    view.left_pressed.emit(12 - net_style.CUT_HITBOX_PX / 2 / view.scale_factor(), 13.5)
    assert highlighted_fold_ends(view) is None


def test_press_on_a_vertex_or_the_line_does_not_glue(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    corner_cut(view)
    near = net_style.VERTEX_RADIUS_PX / 2 / view.scale_factor()
    view.left_pressed.emit(11 + near, 10 + near)  # A_3's circle
    assert tool.editor.state is EditorState.CUT_EDITING
    view.left_pressed.emit(11.5 + net_style.CUT_HITBOX_PX / 2 / view.scale_factor(), 13.8)  # beside the new line
    assert tool.editor.state is EditorState.CUT_EDITING


def test_press_on_a_cut_whose_counterpart_is_in_the_same_half_flashes(
    setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
) -> None:
    view, tool, _ = setup
    corner_cut(view)
    with qtbot.waitSignal(tool.rejected):
        view.left_pressed.emit(10.5, 12 + net_style.CUT_HITBOX_PX / 2 / view.scale_factor())  # E_2-H_1
    assert tool.editor.state is EditorState.CUT_EDITING
    assert tool.item.flash() == ((Vec(10, 12), Vec(11, 12)),) or tool.item.flash() == ((Vec(11, 12), Vec(10, 12)),)


def test_press_on_a_cut_rearranges(setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
    view, tool, _ = setup
    corner_cut(view)
    with qtbot.waitSignal(tool.net_changed):
        view.left_pressed.emit(11.75, 10 + net_style.CUT_HITBOX_PX / 2 / view.scale_factor())
    assert tool.editor.state is EditorState.CUT_APPROVING
    assert tool.item.points() == ()
    view.left_pressed.emit(11.5, 12.5)  # further clicks mean nothing for now
    assert tool.editor.state is EditorState.CUT_APPROVING
    with qtbot.waitSignal(tool.net_changed):
        tool.undo()
    assert tool.editor.state is EditorState.CUT_EDITING
    assert len(tool.item.points()) == 3


def rearranged_corner_cut(view: SheetView) -> None:
    corner_cut(view)
    view.left_pressed.emit(11.75, 10 + net_style.CUT_HITBOX_PX / 2 / view.scale_factor())


MIDDLE_OF_X2_B3 = 11.75, 10.0


class TestApproveButton:
    def test_only_in_approving_in_the_middle_of_the_chosen_segment(
        self, setup: tuple[SheetView, CutTool, RulerTool]
    ) -> None:
        view, tool, _ = setup
        assert tool.approve_button.position() is None
        corner_cut(view)
        assert tool.approve_button.position() is None
        view.left_pressed.emit(11.75, 10 + net_style.CUT_HITBOX_PX / 2 / view.scale_factor())
        assert tool.approve_button.position() == Vec(F(47, 4), 10)
        assert tool.approve_button.enabled()
        tool.undo()
        assert tool.approve_button.position() is None

    def test_click_asks_to_approve(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        rearranged_corner_cut(view)
        with qtbot.assertNotEmitted(tool.undo_clicked), qtbot.waitSignal(tool.approve_clicked):
            view.left_pressed.emit(*MIDDLE_OF_X2_B3)
            view.left_released.emit(*MIDDLE_OF_X2_B3)
        assert tool.editor.state is EditorState.CUT_APPROVING  # approving itself is up to the window

    def test_click_beside_it_does_nothing(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        rearranged_corner_cut(view)
        away = net_style.APPROVE_BUTTON_RADIUS_PX * 2 / view.scale_factor()
        with qtbot.assertNotEmitted(tool.approve_clicked), qtbot.assertNotEmitted(tool.undo_clicked):
            view.left_pressed.emit(MIDDLE_OF_X2_B3[0], MIDDLE_OF_X2_B3[1] + away)

    def test_overlap_makes_it_inactive(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(12 - h, 13.5)  # on D_1-B_1
        view.left_pressed.emit(11 + h, 11.5)  # on H_1-E_1
        view.left_pressed.emit(12.75, 13 - h)  # on z_3-B_2: the halves overlap
        assert tool.editor.rearranged is not None and not tool.editor.rearranged.valid
        assert tool.approve_button.position() == Vec(F(51, 4), 13)
        assert not tool.approve_button.enabled()
        with qtbot.assertNotEmitted(tool.approve_clicked), qtbot.waitSignal(tool.undo_clicked):
            view.left_pressed.emit(12.75, 13.0)
            view.left_released.emit(12.75, 13.0)
        assert tool.editor.state is EditorState.CUT_APPROVING  # undoing itself is up to the window

    def test_ruler_takes_the_click(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, ruler = setup
        rearranged_corner_cut(view)
        ruler.set_active(True)
        assert not tool.claims(*MIDDLE_OF_X2_B3)
        with qtbot.assertNotEmitted(tool.approve_clicked):
            view.left_pressed.emit(*MIDDLE_OF_X2_B3)
        assert len(ruler.ruler.points) == 1

    def test_no_panning_from_the_button(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        rearranged_corner_cut(view)
        assert tool.claims(*MIDDLE_OF_X2_B3)


class TestUndoRedo:
    def test_undo_and_redo_follow_the_editor(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        corner_cut(view)
        assert len(tool.item.points()) == 3
        tool.undo()
        assert tool.editor.state is EditorState.CUTTING
        assert len(tool.item.points()) == 2
        tool.redo()
        assert tool.editor.state is EditorState.CUT_EDITING
        assert len(tool.item.points()) == 3

    def test_net_changed_only_when_the_shown_net_changes(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        view, tool, _ = setup
        corner_cut(view)
        with qtbot.assertNotEmitted(tool.net_changed):
            tool.undo()
        with qtbot.assertNotEmitted(tool.net_changed):
            tool.redo()
        view.left_pressed.emit(11.75, 10 + net_style.CUT_HITBOX_PX / 2 / view.scale_factor())
        with qtbot.waitSignal(tool.net_changed):
            tool.undo()

    def test_ignored_while_dragging(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        corner_cut(view)
        points = tool.editor.cut_line
        assert points is not None
        inner = points.points[1].position
        view.left_pressed.emit(float(inner.x), float(inner.y))
        assert tool.dragging
        done = tool.editor.history.done_count
        tool.undo()
        assert tool.editor.history.done_count == done
        assert tool.editor.state is EditorState.CUT_EDITING

    def test_glued_is_for_rearranging_only(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        corner_cut(view)
        with qtbot.waitSignal(tool.glued):
            view.left_pressed.emit(11.75, 10 + net_style.CUT_HITBOX_PX / 2 / view.scale_factor())
        with qtbot.assertNotEmitted(tool.glued):
            tool.undo()
            tool.redo()


def send_drag(view: SheetView, x: float, y: float, shift: bool) -> None:
    """A real mouse move with the left button held (QTest moves carry neither buttons nor modifiers)."""
    pos = QPointF(view.from_sheet(QPointF(x, y)))
    modifier = Qt.KeyboardModifier.ShiftModifier if shift else Qt.KeyboardModifier.NoModifier
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        pos,
        view.viewport().mapToGlobal(pos),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        modifier,
    )
    QApplication.sendEvent(view.viewport(), event)


class TestShift:
    Y = Vec(F(23, 2), F(27, 2))

    def cutting(self, view: SheetView) -> None:
        view.left_pressed.emit(*just_inside_top_of_face_1(view))
        view.left_pressed.emit(11.5, 13.5)

    def test_rubber_band_goes_straight(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        self.cutting(view)
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        view.mouse_moved.emit(11.7, 13.4)
        assert tool.item.rubber_band() == (self.Y, Vec(F(117, 10), F(27, 2)))
        view.mouse_moved.emit(11.6, 13.2)
        assert tool.item.rubber_band() == (self.Y, Vec(F(23, 2), F(132, 10)))

    def test_it_changes_at_once(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        self.cutting(view)
        view.mouse_moved.emit(11.7, 13.4)
        free = tool.item.rubber_band()
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        band = tool.item.rubber_band()
        assert band is not None and band != free and band[1].y == self.Y.y
        qtbot.keyRelease(view, Qt.Key.Key_Shift)
        assert tool.item.rubber_band() == free

    def test_click_adds_where_the_band_ends(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        self.cutting(view)
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        view.mouse_moved.emit(11.7, 13.4)
        view.left_pressed.emit(11.7, 13.4)
        assert tool.item.points()[-1].position == Vec(F(117, 10), F(27, 2))

    def test_ends_on_a_cut_on_its_line(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        self.cutting(view)
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(12 - h, 13.45)
        assert tool.editor.state is EditorState.CUT_EDITING
        assert tool.item.points()[-1].position == Vec(12, F(27, 2))

    def test_what_the_band_points_at_decides_not_the_mouse(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        """The mouse is in the hitbox of a cut, but the straight segment goes elsewhere."""
        view, tool, _ = setup
        view.left_pressed.emit(*just_inside_top_of_face_1(view))
        view.left_pressed.emit(11.7, 13.5)
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(12 - h, 13.2)
        assert tool.editor.state is EditorState.CUTTING
        assert tool.item.points()[-1].position == Vec(F(117, 10), F(132, 10))

    def test_hover_target(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        assert tool.hover_target(11.5, 12.5) is None  # not cutting
        self.cutting(view)
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        assert tool.hover_target(12 - h, 13 + h / 2) is None  # no SHIFT
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        assert tool.hover_target(12 - h, 13 + h / 2) == (None, None)
        target = tool.hover_target(12 - h, 13.45)
        assert target is not None and target[1] is not None

    def test_claims_where_the_band_points(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        view.left_pressed.emit(*just_inside_top_of_face_1(view))
        view.left_pressed.emit(11.1, 13.5)
        off_the_net = 10.95, 13.9
        assert not tool.claims(*off_the_net)
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        assert tool.claims(*off_the_net)  # the band goes straight up, inside the net

    def test_drag_inner_point(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(11.5, 13.5)
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        view.mouse_moved.emit(11.7, 13.2)
        assert tool.item.points()[1].position == Vec(F(23, 2), F(132, 10))
        view.left_released.emit(11.7, 13.2)
        assert positions(tool)[1] == Vec(F(23, 2), F(132, 10))

    def test_shift_during_a_drag_acts_at_once(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(11.5, 13.5)
        view.mouse_moved.emit(11.7, 13.2)
        free = tool.item.points()[1].position
        assert free == Vec(F(117, 10), F(132, 10))
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        assert tool.item.points()[1].position == Vec(F(23, 2), F(132, 10))
        qtbot.keyRelease(view, Qt.Key.Key_Shift)
        assert tool.item.points()[1].position == free

    def test_drag_first_point_is_not_restricted(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(11.5, 14.0)
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        view.mouse_moved.emit(11.3, 13.9)
        assert tool.item.points()[0].position == Vec(F(113, 10), 14)

    def test_drag_last_point_stays_on_the_perimeter(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(12.0, 13.5)
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        view.mouse_moved.emit(11.1, 13.4)
        view.left_released.emit(11.1, 13.4)
        assert positions(tool)[2] == Vec(11, F(27, 2))
        assert tool.editor.cut_line is not None and tool.editor.cut_line.points[2].edge is not None

    def test_inner_point_over_the_perimeter_is_rejected(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        """Its segment goes straight from the first point, which is on the top of face 1: along that cut."""
        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(11.5, 13.5)
        qtbot.keyPress(view, Qt.Key.Key_Shift)
        view.mouse_moved.emit(11.2, 13.95)
        with qtbot.waitSignal(tool.rejected):
            view.left_released.emit(11.2, 13.95)
        assert positions(tool)[1] == self.Y

    def test_shift_click_on_an_inner_point_deletes_on_release(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        view, tool, _ = setup
        corner_cut(view)
        pos = view.from_sheet(QPointF(11.5, 13.5)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, pos)
        assert len(positions(tool)) == 3
        assert tool.dragging
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, pos)
        assert len(positions(tool)) == 2
        assert not tool.dragging

    def test_a_tiny_slip_is_still_a_click(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        corner_cut(view)
        pos = view.from_sheet(QPointF(11.5, 13.5)).toPoint()
        slip = (QApplication.startDragDistance() - 1) / view.scale_factor()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, pos)
        send_drag(view, 11.5, 13.5 - slip, True)
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, pos)
        assert len(positions(tool)) == 2

    def test_shift_drag_moves_instead_of_deleting(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        view, tool, _ = setup
        corner_cut(view)
        modifier = Qt.KeyboardModifier.ShiftModifier
        pos = view.from_sheet(QPointF(11.5, 13.5)).toPoint()
        qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, modifier, pos)
        send_drag(view, 11.55, 13.2, True)
        end = view.from_sheet(QPointF(11.55, 13.2)).toPoint()
        qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, modifier, end)
        line = positions(tool)
        assert len(line) == 3
        assert line[1].x == F(23, 2) and line[1].y != F(27, 2)

    def test_no_shift_while_dragging_means_no_restriction(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        corner_cut(view)
        drag_to(view, (11.5, 13.5), (11.7, 13.2))
        assert positions(tool)[1] == Vec(F(117, 10), F(132, 10))


class TestCursorAt:
    """What the mouse shows is what a click would do."""

    def h(self, view: SheetView) -> float:
        return net_style.CUT_HITBOX_PX / 2 / view.scale_factor()

    def test_default_scissors_on_a_cut_or_a_vertex(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        from cube_net.ui.sheet.cursors import CursorKind

        view, tool, _ = setup
        assert tool.cursor_at(10 + self.h(view), 12.5) is CursorKind.SCISSORS
        assert tool.cursor_at(10, 13) is CursorKind.SCISSORS
        assert tool.cursor_at(11.5, 12.5) is CursorKind.ARROW
        assert tool.cursor_at(7, 7) is CursorKind.ARROW

    def test_cutting_scissors_on_the_net(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        from cube_net.ui.sheet.cursors import CursorKind

        view, tool, _ = setup
        view.left_pressed.emit(*just_inside_top_of_face_1(view))
        assert tool.cursor_at(11.5, 12.5) is CursorKind.SCISSORS
        assert tool.cursor_at(7, 7) is CursorKind.ARROW

    def test_editing_pencil_plus_glue_or_nothing(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        from cube_net.ui.sheet.cursors import CursorKind

        view, tool, _ = setup
        corner_cut(view)
        h = self.h(view)
        assert tool.cursor_at(11.5, 13.5) is CursorKind.PENCIL  # a point
        assert tool.cursor_at(11.5, 13.75) is CursorKind.PLUS  # a segment's middle
        assert tool.cursor_at(11.75, 10 + h) is CursorKind.GLUE  # a cut that can be chosen
        assert tool.cursor_at(10.5, 12 + h) is CursorKind.ARROW  # a useless one
        assert tool.cursor_at(11.5, 12.5) is CursorKind.ARROW
        assert tool.cursor_at(10, 13) is CursorKind.ARROW  # a vertex: nothing to click there

    def test_red_x_over_an_inner_point_while_ctrl_is_held(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        from cube_net.ui.sheet.cursors import CursorKind

        view, tool, _ = setup
        corner_cut(view)
        qtbot.keyPress(view, Qt.Key.Key_Control)
        assert tool.cursor_at(11.5, 13.5) is CursorKind.DELETE  # Y
        assert tool.cursor_at(11.5, 14) is CursorKind.PENCIL  # the first point
        assert tool.cursor_at(12, 13.5) is CursorKind.PENCIL  # the last one
        assert tool.cursor_at(11.5, 13.75) is CursorKind.PLUS
        qtbot.keyRelease(view, Qt.Key.Key_Control)
        assert tool.cursor_at(11.5, 13.5) is CursorKind.PENCIL

    def test_pencil_while_dragging(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        from cube_net.ui.sheet.cursors import CursorKind

        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(11.5, 13.5)
        assert tool.cursor_at(7, 7) is CursorKind.PENCIL

    def test_approving_a_hand_over_the_button_and_a_tooltip(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        from cube_net.ui.sheet.cursors import CursorKind

        view, tool, _ = setup
        rearranged_corner_cut(view)
        assert tool.cursor_at(*MIDDLE_OF_X2_B3) is CursorKind.BUTTON
        assert tool.tooltip_at(*MIDDLE_OF_X2_B3) == "Approve"
        assert tool.cursor_at(11.5, 12.5) is CursorKind.ARROW
        assert tool.tooltip_at(11.5, 12.5) == ""

    def test_the_x_button_says_cancel(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        h = self.h(view)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11 + h, 11.5)
        view.left_pressed.emit(12.75, 13 - h)
        assert not tool.approve_button.enabled()
        assert tool.tooltip_at(12.75, 13.0) == "Cancel"

    def test_nothing_while_the_ruler_is_active(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        from cube_net.ui.sheet.cursors import CursorKind

        view, tool, ruler = setup
        ruler.set_active(True)
        assert tool.cursor_at(10 + self.h(view), 12.5) is CursorKind.ARROW
        corner_cut(view)  # the ruler takes these clicks: still DEFAULT
        assert tool.cursor_at(11.5, 13.5) is CursorKind.ARROW


class TestButtonsActOnRelease:
    """The approve button and the middle circles: a press shows them pressed; they act when released on them."""

    def test_approve_on_release_only(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        rearranged_corner_cut(view)
        with qtbot.assertNotEmitted(tool.approve_clicked):
            view.left_pressed.emit(*MIDDLE_OF_X2_B3)
        assert tool.approve_button.pressed()
        assert tool.busy
        with qtbot.waitSignal(tool.approve_clicked):
            view.left_released.emit(*MIDDLE_OF_X2_B3)
        assert not tool.approve_button.pressed()
        assert not tool.busy

    def test_approve_moved_off_and_released_does_nothing(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        view, tool, _ = setup
        rearranged_corner_cut(view)
        away = MIDDLE_OF_X2_B3[0], MIDDLE_OF_X2_B3[1] + net_style.APPROVE_BUTTON_RADIUS_PX * 3 / view.scale_factor()
        view.left_pressed.emit(*MIDDLE_OF_X2_B3)
        view.mouse_moved.emit(*away)
        assert not tool.approve_button.pressed()  # not pressed while the mouse is off it
        with qtbot.assertNotEmitted(tool.approve_clicked), qtbot.assertNotEmitted(tool.undo_clicked):
            view.left_released.emit(*away)
        assert tool.editor.state is EditorState.CUT_APPROVING

    def test_approve_moved_off_and_back(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        rearranged_corner_cut(view)
        away = MIDDLE_OF_X2_B3[0], MIDDLE_OF_X2_B3[1] + net_style.APPROVE_BUTTON_RADIUS_PX * 3 / view.scale_factor()
        view.left_pressed.emit(*MIDDLE_OF_X2_B3)
        view.mouse_moved.emit(*away)
        view.mouse_moved.emit(*MIDDLE_OF_X2_B3)
        assert tool.approve_button.pressed()
        with qtbot.waitSignal(tool.approve_clicked):
            view.left_released.emit(*MIDDLE_OF_X2_B3)

    def test_midpoint_on_release_only(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(11.5, 13.75)
        assert len(positions(tool)) == 3  # nothing yet
        assert tool.item.pressed_midpoint() == 0
        view.left_released.emit(11.5, 13.75)
        assert len(positions(tool)) == 4
        assert tool.item.pressed_midpoint() is None

    def test_midpoint_moved_off_and_released_does_nothing(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(11.5, 13.75)
        view.mouse_moved.emit(11.5, 13.6)
        assert tool.item.pressed_midpoint() is None
        view.left_released.emit(11.5, 13.6)
        assert len(positions(tool)) == 3

    def test_released_on_another_midpoint_does_nothing(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(11.5, 13.75)  # the first segment's
        view.left_released.emit(11.75, 13.5)  # the second segment's
        assert len(positions(tool)) == 3

    def test_no_undo_while_a_button_is_pressed(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        view, tool, _ = setup
        corner_cut(view)
        view.left_pressed.emit(11.5, 13.75)
        tool.undo()
        assert tool.editor.state is EditorState.CUT_EDITING
        view.left_released.emit(11.5, 13.75)
        assert len(positions(tool)) == 4


def ctrl_press(view: SheetView, qtbot: QtBot, x: float, y: float) -> None:
    pos = view.from_sheet(QPointF(x, y)).toPoint()
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos)


def ctrl_release(view: SheetView, qtbot: QtBot, x: float, y: float) -> None:
    pos = view.from_sheet(QPointF(x, y)).toPoint()
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos)


class TestCtrlClickDeletes:
    """Ctrl+click on an inner point deletes it, when released on the same point; the ends can't be deleted."""

    def test_deletes_on_release(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        corner_cut(view)
        ctrl_press(view, qtbot, 11.5, 13.5)
        assert positions(tool) == [X, Y, Z]  # nothing yet
        assert tool.busy
        assert not tool.dragging  # CTRL doesn't drag
        with qtbot.waitSignal(tool.edited) as blocker:
            ctrl_release(view, qtbot, 11.5, 13.5)
        assert positions(tool) == [X, Z]
        assert blocker.args == ["delete", 1, Y]
        assert not tool.busy

    def test_released_off_the_point_does_nothing(self, setup: tuple[SheetView, CutTool, RulerTool]) -> None:
        from cube_net.ui.sheet.cursors import CursorKind

        view, tool, _ = setup
        corner_cut(view)
        view._press_modifiers = Qt.KeyboardModifier.ControlModifier  # as a real Ctrl+press leaves it
        view.left_pressed.emit(11.5, 13.5)
        view.mouse_moved.emit(11.3, 13.2)
        assert positions(tool) == [X, Y, Z]  # the point doesn't move
        assert tool.cursor_at(11.3, 13.2) is CursorKind.ARROW
        assert tool.cursor_at(11.5, 13.5) is CursorKind.DELETE
        view.left_released.emit(11.3, 13.2)
        assert positions(tool) == [X, Y, Z]
        assert not tool.busy

    def test_an_end_is_dragged_as_usual(self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot) -> None:
        view, tool, _ = setup
        corner_cut(view)
        ctrl_press(view, qtbot, 12, 13.5)
        assert tool.dragging
        ctrl_release(view, qtbot, 12, 13.5)
        assert positions(tool) == [X, Y, Z]

    def test_rejected_when_the_line_would_cross_the_perimeter(
        self, setup: tuple[SheetView, CutTool, RulerTool], qtbot: QtBot
    ) -> None:
        view, tool, _ = setup
        inside = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(10.5, 13 - inside)  # on C_1-A_2
        view.left_pressed.emit(11.2, 12.8)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(11.5, 14 - inside)
        before = positions(tool)
        ctrl_press(view, qtbot, 11.2, 12.8)
        with qtbot.waitSignal(tool.rejected):
            ctrl_release(view, qtbot, 11.2, 12.8)
        assert tool.item.flash() == ((before[0], before[2]),)  # the shortcut in black
        qtbot.waitUntil(lambda: tool.item.flash() is None, timeout=FLASH_MS + 500)
        assert positions(tool) == before
