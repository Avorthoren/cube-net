# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from fractions import Fraction as F

from hypothesis import given
from hypothesis import strategies as st
from net_checks import assert_consistent

from cube_net.core.cutting import CutLine, CutPoint, SplitNet, connected_regions, rearrange, split_net
from cube_net.core.editor import Editor, EditorState
from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, Net, NetVertex, boundary_edge_from, boundary_vertex_at, default_net


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


def vertex(net: Net, x: int, y: int) -> NetVertex:
    found = boundary_vertex_at(net, Vec(x, y), F(1, 100))
    assert found is not None
    return found


def at_vertex(net: Net, x: int, y: int) -> CutPoint:
    w = vertex(net, x, y)
    return CutPoint(w.position, boundary_edge_from(net, w), w)


def halves(net: Net) -> list[int]:
    """The number of regions in each part of the net."""
    parts = {frozenset(connected_regions(r)) for r in net.regions}
    return sorted(len(p) for p in parts)


def test_corner_cut(net: Net, cut: Callable[[str], HalfEdge], consistent: Callable[[Net], None]) -> None:
    """docs/idea.txt: x on A_1-B_1, y inside face 1, z on B_1-D_1."""
    line = CutLine(
        [
            CutPoint(v("11.5", "14"), cut("B_1-A_1")),
            CutPoint(v("11.5", "13.5")),
            CutPoint(v("12", "13.5"), cut("D_1-B_1")),
        ]
    )
    split = split_net(net, line)
    consistent(split.net)
    assert halves(split.net) == [1, 6]
    assert sorted(len(c) for c in split.net.perimeters()) == [4, 18]  # x-y, y-z, z-B, B-x around the corner piece
    assert len(split.line_edges) == 4  # two pieces, two sides each
    assert len(net.vertices) == 14 and len(net.regions) == 6  # the original is untouched


def test_images_divide_the_counterparts(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    line = CutLine(
        [
            CutPoint(v("11.5", "14"), cut("B_1-A_1")),
            CutPoint(v("11.5", "13.5")),
            CutPoint(v("12", "13.5"), cut("D_1-B_1")),
        ]
    )
    positions = {w.position for w in split_net(net, line).net.vertices}
    assert v("11.5", "10") in positions  # x_2 on A_3-B_3
    assert v("12.5", "13") in positions  # z_3 on D_1-B_2


def test_every_stop_has_two_copies(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    line = CutLine(
        [
            CutPoint(v("11.5", "14"), cut("B_1-A_1")),
            CutPoint(v("11.5", "13.5")),
            CutPoint(v("12", "13.5"), cut("D_1-B_1")),
        ]
    )
    result = split_net(net, line).net
    for position in (v("11.5", "14"), v("11.5", "13.5"), v("12", "13.5")):
        assert sum(w.position == position for w in result.vertices) == 2


def test_crossing_fold_edges_divides_them_and_the_regions(
    net: Net, cut: Callable[[str], HalfEdge], consistent: Callable[[Net], None]
) -> None:
    """From the top of face 1 down to the bottom of face 5: through 4 faces, splitting each."""
    line = CutLine([CutPoint(v("11.5", "14"), cut("B_1-A_1")), CutPoint(v("11.5", "10"), cut("A_3-B_3"))])
    split = split_net(net, line)
    consistent(split.net)
    assert len(split.net.regions) == 10
    assert halves(split.net) == [5, 5]
    assert len(split.net.fold_edges()) == 8  # C-D, G-H and E-F each divided in two, C-H and D-G untouched
    assert len(split.line_edges) == 8


def test_along_a_whole_fold_cuts_off_a_face(net: Net, consistent: Callable[[Net], None]) -> None:
    """From C_1 to D_1 along the fold: face 1 comes off, no region is divided."""
    line = CutLine([at_vertex(net, 11, 13), at_vertex(net, 12, 13)])
    split = split_net(net, line)
    consistent(split.net)
    assert halves(split.net) == [1, 5]
    assert len(split.net.regions) == 6
    assert len(split.net.fold_edges()) == 4


def test_a_point_on_a_fold_and_then_along_it(
    net: Net, cut: Callable[[str], HalfEdge], consistent: Callable[[Net], None]
) -> None:
    line = CutLine(
        [
            CutPoint(v("11.2", "14"), cut("B_1-A_1")),
            CutPoint(v("11.2", "13")),  # on the fold C-D
            CutPoint(v("11.8", "13")),  # along it
            CutPoint(v("11.8", "14"), cut("B_1-A_1")),
        ]
    )
    split = split_net(net, line)
    consistent(split.net)
    assert halves(split.net) == [1, 7]  # the box is one region; face 1 falls apart into a left and a right strip


def test_both_ends_on_one_cut(net: Net, cut: Callable[[str], HalfEdge], consistent: Callable[[Net], None]) -> None:
    top = cut("B_1-A_1")
    line = CutLine([CutPoint(v("11.2", "14"), top), CutPoint(v("11.5", "13.5")), CutPoint(v("11.8", "14"), top)])
    split = split_net(net, line)
    consistent(split.net)
    assert halves(split.net) == [1, 6]
    assert sum(w.position.y == 10 for w in split.net.vertices) == 4  # A_3, both images, B_3


def test_two_images_of_one_point_as_the_ends(
    net: Net, cut: Callable[[str], HalfEdge], consistent: Callable[[Net], None]
) -> None:
    """z on B-D, from z_1 to z_3: a closed loop on the cube. It still splits the net, and every cut stays paired."""
    z1 = CutPoint(v("12", "13.5"), cut("D_1-B_1"))
    z3 = CutPoint(v("12.5", "13"), cut("B_2-D_1"))
    line = CutLine([z1, CutPoint(v("11.5", "13.5")), CutPoint(v("11.5", "12.5")), CutPoint(v("12.5", "12.5")), z3])
    split = split_net(net, line)
    consistent(split.net)
    assert len(halves(split.net)) == 2


column = st.fractions(F(1101, 100), F(1199, 100), max_denominator=1000)


@given(column, column, column)
def test_random_lines_down_the_column_stay_consistent(top: F, middle: F, bottom: F) -> None:
    net = default_net()
    first = next(he for he in net.boundary_edges() if he.origin.position == Vec(12, 14))
    last = next(he for he in net.boundary_edges() if he.origin.position == Vec(11, 10))
    line = CutLine([CutPoint(Vec(top, 14), first), CutPoint(Vec(middle, F(25, 2))), CutPoint(Vec(bottom, 10), last)])
    split = split_net(net, line)
    assert_consistent(split.net)
    assert len(halves(split.net)) == 2


def cut_names(split: SplitNet, cuts: frozenset[HalfEdge]) -> set[frozenset[Vec]]:
    return {frozenset((he.origin.position, he.destination.position)) for he in cuts}


class TestSameHalfCuts:
    """The user's example: a straight line from B_1 to K_1 on H_1-E_1 of the default net."""

    def split(self, net: Net, cut: Callable[[str], HalfEdge]) -> SplitNet:
        k1 = CutPoint(v("11", "11.5"), cut("H_1-E_1"))
        return split_net(net, CutLine([at_vertex(net, 12, 14), k1]))

    def test_both_images_of_the_part_next_to_h1(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        names = cut_names(self.split(net, cut), self.split(net, cut).same_half_cuts)
        h1 = Vec(11, 12)
        assert frozenset((h1, v("11", "11.5"))) in names  # H_1-K_1
        assert frozenset((h1, v("10.5", "12"))) in names  # H_1-K_2

    def test_the_parts_that_can_be_glued_are_not_there(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        names = cut_names(self.split(net, cut), self.split(net, cut).same_half_cuts)
        assert frozenset((v("11", "11.5"), Vec(11, 11))) not in names  # K_1-E_1
        assert frozenset((v("10.5", "12"), Vec(10, 12))) not in names  # K_2-E_2
        assert frozenset((Vec(11, 14), Vec(12, 14))) not in names  # A_1-B_1
        assert frozenset((Vec(11, 10), Vec(12, 10))) not in names  # A_3-B_3

    def test_exactly_the_cuts_rearrange_refuses(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        split = self.split(net, cut)
        for he in split.net.boundary_edges():
            if he in split.line_edges:
                assert he not in split.same_half_cuts  # the new line itself is never in the set
            else:
                assert (rearrange(split, he) is None) == (he in split.same_half_cuts)

    def test_a_closed_loop_leaves_only_such_cuts(self, net: Net, cut: Callable[[str], HalfEdge]) -> None:
        line = CutLine([CutPoint(v("11.5", "14"), cut("B_1-A_1")), CutPoint(v("11.5", "10"), cut("A_3-B_3"))])
        split = split_net(net, line)
        assert split.same_half_cuts == frozenset(split.net.boundary_edges()) - split.line_edges


# Cube with a hole's net: where its perimeter touches itself, the corner U3 of one face (sheet (49, 54)) is in the
# middle of a cut of the face next to it (from (49, 53) to (49, 55)), and the cuts of two faces lie along each other
# (from (49, 50) to (49, 51)).
U3 = Vec(49, 54)
I2 = Vec(53, 49)


def torus_editor() -> Editor:
    from cube_net.core.history import History
    from cube_net.core.project.builtin_templates import cube_with_a_hole
    from cube_net.core.project.from_template import project_from_template

    project = project_from_template(cube_with_a_hole())
    editor = Editor(project.state.net)
    editor.load(project.state, History())
    return editor


def the_unit_cut_around(net: Net, p: Vec) -> HalfEdge:
    """The cut of `net`, one unit long, with `p` in its middle (the first one, if two lie along each other)."""
    return next(
        he
        for he in net.boundary_edges()
        if (he.destination.position - he.origin.position).length_squared() == 1
        and (he.origin.position + he.destination.position) / 2 == p
    )


def cut_from_vertex(editor: Editor, start: Vec, end: Vec, cut: HalfEdge) -> None:
    vertex = next(v for v in editor.net.vertices if v.position == start)
    editor.click(start, None, vertex=vertex)
    editor.click(end, cut)
    assert editor.state is EditorState.CUT_EDITING


def approved_somehow(cut: Callable[[], Editor]) -> bool:
    """The line `cut` makes (in a new editor each time) can be rearranged and approved: the new net is a valid one."""
    from cube_net.core.net.validate import validate_net

    split = cut().split()
    for chosen in split.net.boundary_edges():
        if chosen in split.line_edges or chosen in split.same_half_cuts:
            continue
        editor = cut()
        ends = (chosen.origin.position, chosen.destination.position)
        editor.glue(
            next(
                he
                for he in editor.split().net.boundary_edges()
                if (he.origin.position, he.destination.position) == ends
            )
        )
        if editor.rearranged is not None and editor.rearranged.valid:
            editor.approve()
            validate_net(editor.net)
            return True
    return False


def test_a_line_from_a_corner_in_the_middle_of_another_faces_cut() -> None:
    end = Vec(F(154, 3), 55)  # on the face's top side, from (53, 55) to (49, 55)

    def cut() -> Editor:
        editor = torus_editor()
        top = next(he for he in editor.net.boundary_edges() if he.origin.position == Vec(53, 55))
        cut_from_vertex(editor, U3, end, top)
        return editor

    split = cut().split()  # (it couldn't be connected: the corner isn't on that face)
    assert len(halves(split.net)) == 2
    assert_consistent(split.net)
    assert approved_somehow(cut)


def test_a_line_ending_where_the_cuts_of_two_faces_lie_along_each_other() -> None:
    end = Vec(49, F(101, 2))

    def cut() -> Editor:
        editor = torus_editor()
        cut_from_vertex(editor, I2, end, the_unit_cut_around(editor.net, end))  # on the face the line doesn't cross
        return editor

    split = cut().split()  # (it couldn't be connected: the end was on the other face's cut)
    assert len(halves(split.net)) == 2
    assert_consistent(split.net)  # (no rearrangement of these halves is valid: they'd overlap)
