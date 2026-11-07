from collections.abc import Callable
from fractions import Fraction as F

import pytest

from cube_net.core.cutting import MAX_POINTS_AFTER_FIRST
from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import HalfEdge, Net, NetVertex, boundary_vertex_at, default_net


@pytest.fixture
def net() -> Net:
    return default_net()


@pytest.fixture
def cut(net: Net) -> Callable[[str], HalfEdge]:
    labels = vertex_labels(net, PointLabels())
    by_name = {f"{labels[he.origin]}-{labels[he.destination]}": he for he in net.boundary_edges()}
    return lambda name: by_name[name]


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


def positions(editor: Editor) -> list[Vec]:
    assert editor.cut_line is not None
    return [p.position for p in editor.cut_line.points]


def test_corner_cut_from_idea(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    """docs/idea.txt: x on A_1-B_1, y inside face 1, z on B_1-D_1."""
    editor = Editor(net)
    assert editor.state is EditorState.DEFAULT
    assert editor.click(v("11.5", "13.99"), cut("B_1-A_1")) is None  # projected onto the cut
    assert editor.state is EditorState.CUTTING
    assert editor.click(v("11.5", "13.5"), None) is None
    assert editor.click(v("11.99", "13.5"), cut("D_1-B_1")) is None
    assert editor.state is EditorState.CUT_EDITING
    assert positions(editor) == [v("11.5", "14"), v("11.5", "13.5"), v("12", "13.5")]


def test_click_off_any_cut_in_default_does_nothing(net: Net) -> None:
    editor = Editor(net)
    assert editor.click(v("11.5", "12.5"), None) is None
    assert editor.state is EditorState.DEFAULT and editor.cut_line is None


def test_rejection_keeps_the_line_and_reports_the_segment(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    editor.click(v("11.5", "14"), cut("B_1-A_1"))
    rejection = editor.click(v("12.5", "13.5"), None)  # outside the net
    assert rejection is not None
    assert rejection.segment == (v("11.5", "14"), v("12.5", "13.5"))
    assert positions(editor) == [v("11.5", "14")]


def test_two_images_of_the_same_point_may_be_the_ends(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    """From A_1 down through faces 1, 2, 6, 5 to A_3 (allowed, even though nothing can be glued afterwards)."""
    editor = Editor(net)
    editor.click(v("11", "14"), cut("B_1-A_1"))
    for y in ("13.5", "12.5", "11.5", "10.5"):
        assert editor.click(v("11.5", y), None) is None
    assert editor.click(v("11", "10"), cut("A_3-B_3")) is None
    assert editor.state is EditorState.CUT_EDITING


def test_at_most_50_points_after_the_first(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    editor.click(v("10", "12.01"), cut("A_2-E_2"))
    for i in range(MAX_POINTS_AFTER_FIRST):  # a zigzag inside face 4
        x = F(1001, 100) + F(i, 100) * F(97, 100)
        y = F(1202, 100) if i % 2 else F(1298, 100)
        assert editor.click(Vec(x, y), None) is None, i
    assert editor.click(v("10.9", "12.5"), None) is not None  # a 51st point after the first
    assert editor.click(v("10.9", "13"), cut("C_1-A_2")) is None  # but it may still end
    assert editor.state is EditorState.CUT_EDITING


def test_clicks_after_the_line_is_closed_are_ignored_for_now(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    editor.click(v("11.5", "14"), cut("B_1-A_1"))
    editor.click(v("11.5", "13.5"), None)
    editor.click(v("12", "13.5"), cut("D_1-B_1"))
    assert editor.click(v("11.7", "13.7"), None) is None
    assert len(positions(editor)) == 3


def test_candidate(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    assert editor.candidate(v("11.5", "13.9"), cut("B_1-A_1")).position == v("11.5", "14")
    assert editor.candidate(v("11.5", "13.9"), None).position == v("11.5", "13.9")


def vertex_at(net: Net, x: int, y: int) -> NetVertex:
    found = boundary_vertex_at(net, Vec(x, y), F(1, 100))
    assert found is not None
    return found


def test_start_and_end_at_perimeter_vertices(net: Net) -> None:
    """From the reflex corner C_1 across face 2 to G_1 (docs/idea.txt: cuts may start / end at vertices)."""
    editor = Editor(net)
    c1, g1 = vertex_at(net, 11, 13), vertex_at(net, 12, 12)
    assert editor.click(v("11.02", "12.98"), None, c1) is None  # anywhere in the circle: exactly the vertex
    assert editor.cut_line is not None and editor.cut_line.points[0].vertex is c1
    assert editor.click(v("11.5", "12.5"), None) is None
    assert editor.click(v("11.99", "12.01"), None, g1) is None
    assert editor.state is EditorState.CUT_EDITING
    assert positions(editor) == [Vec(11, 13), v("11.5", "12.5"), Vec(12, 12)]


def test_vertex_wins_over_the_cut(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    editor = Editor(net)
    editor.click(v("11.02", "13.98"), cut("B_1-A_1"), vertex_at(net, 11, 14))
    assert positions(editor) == [Vec(11, 14)]


def test_vertex_segment_must_go_into_the_net(net: Net) -> None:
    editor = Editor(net)
    editor.click(v("11", "13"), None, vertex_at(net, 11, 13))  # C_1: the empty quadrant is up-left
    assert editor.click(v("10.5", "13.5"), None) is not None  # outside the net
    assert editor.click(v("10.5", "12.5"), None) is None  # into face 4


def test_ending_at_the_starting_vertex_is_rejected(net: Net) -> None:
    editor = Editor(net)
    c1 = vertex_at(net, 11, 13)
    editor.click(v("11", "13"), None, c1)
    editor.click(v("11.5", "12.5"), None)
    assert editor.click(v("11", "13"), None, c1) is not None
