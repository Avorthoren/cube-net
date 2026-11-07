from fractions import Fraction as F

import pytest
from pytestqt.qtbot import QtBot

from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec
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
    assert tool.item.flash() == (Vec(F(115, 10), 14), Vec(F(125, 10), F(135, 10)))
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
