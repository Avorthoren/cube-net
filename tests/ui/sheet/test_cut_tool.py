from fractions import Fraction as F

import pytest
from PyQt6.QtCore import QPointF, Qt
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
    view.set_net_hit_test(lambda x, y: net.contains(quantize(x, y)))
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


def test_claims_only_points_and_midpoints(setup: tuple[SheetView, CutTool, RulerTool]) -> None:
    view, tool, _ = setup
    assert not tool.claims(11.5, 14)  # not editing yet
    corner_cut(view)
    assert tool.claims(11.5, 14) and tool.claims(11.5, 13.75)
    assert not tool.claims(7, 7)


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
        tool.cancel_rearrangement()
    assert tool.editor.state is EditorState.CUT_EDITING
    assert len(tool.item.points()) == 3
