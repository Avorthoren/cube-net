from fractions import Fraction as F

from cube_net.core.cube import SurfacePoint
from cube_net.core.editor import Editor
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels, cut_line_labels
from cube_net.core.net import boundary_edge_at, boundary_vertex_at, default_net


def click(editor: Editor, x: str, y: str) -> None:
    p = Vec(F(x), F(y))
    vertex = boundary_vertex_at(editor.net, p, F(1, 100))
    editor.click(p, boundary_edge_at(editor.net, p, F(1, 20)), vertex)


def test_corner_cut_labels() -> None:
    """x, y, z of docs/idea.txt become I, J, K: I_1 and I_2 (x_1, x_2), J_1, K_1 and K_2 (z_1, z_3)."""
    editor = Editor(default_net())
    for x, y in (("11.5", "13.99"), ("11.5", "13.5"), ("11.99", "13.5")):
        click(editor, x, y)
    assert editor.cut_line is not None
    labels = {str(label): position for position, label in cut_line_labels(editor.net, editor.cut_line, PointLabels())}
    assert labels == {
        "I_1": Vec(F(23, 2), 14),
        "I_2": Vec(F(23, 2), 10),
        "J_1": Vec(F(23, 2), F(27, 2)),
        "K_1": Vec(12, F(27, 2)),
        "K_2": Vec(F(25, 2), 13),
    }


def test_points_at_existing_vertices_are_left_to_the_net() -> None:
    editor = Editor(default_net())
    click(editor, "11", "13")  # C_1
    click(editor, "11.5", "12.5")
    assert editor.cut_line is not None
    labels = [str(label) for _, label in cut_line_labels(editor.net, editor.cut_line, PointLabels())]
    assert labels == ["I_1"]


def test_names_are_stable_across_calls() -> None:
    editor, names = Editor(default_net()), PointLabels()
    click(editor, "11.5", "13.99")
    click(editor, "11.5", "13.5")
    assert editor.cut_line is not None
    first = cut_line_labels(editor.net, editor.cut_line, names)
    assert cut_line_labels(editor.net, editor.cut_line, names) == first


def test_crossings_are_labelled_in_order_along_the_line() -> None:
    """From C_1 into face 6: the crossing with H_1-G_1 gets the first new name, then the point in face 6."""
    editor = Editor(default_net())
    click(editor, "11", "13")
    click(editor, "11.5", "11.5")
    assert editor.cut_line is not None
    labels = [(str(label), position) for position, label in cut_line_labels(editor.net, editor.cut_line, PointLabels())]
    assert labels == [("I_1", Vec(F(34, 3), 12)), ("J_1", Vec(F(23, 2), F(23, 2)))]


def test_a_moved_point_keeps_its_letter_and_uses_up_no_names() -> None:
    editor, names = Editor(default_net()), PointLabels()
    for x, y in (("11.5", "13.99"), ("11.5", "13.5"), ("11.99", "13.5")):
        click(editor, x, y)
    assert editor.cut_line is not None
    for y in ("13.4", "13.3", "13.2"):  # as if the inner point were dragged through several positions
        assert editor.move_point(1, editor.drag_target(1, Vec(F(23, 2), F(y)))) is None
        labels = {str(label) for _, label in cut_line_labels(editor.net, editor.cut_line, names)}
        assert labels == {"I_1", "I_2", "J_1", "K_1", "K_2"}
    assert names.upcoming() == "I"  # still nothing registered


def test_a_name_already_registered_is_used() -> None:
    editor, names = Editor(default_net()), PointLabels()
    click(editor, "11.5", "13.99")
    assert editor.cut_line is not None
    assert names.register(SurfacePoint(1, Vec(F(1, 2), 1))) == "I"  # the same cube point, named earlier
    names.register(SurfacePoint(2, Vec(F(1, 2), F(1, 2))))
    click(editor, "11.5", "13.5")
    labels = [str(label) for _, label in cut_line_labels(editor.net, editor.cut_line, names)]
    assert labels == ["I_1", "I_2", "K_1"]  # I is known; J is taken, so the new point previews K
