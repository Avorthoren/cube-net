from collections.abc import Callable
from fractions import Fraction as F

from hypothesis import given
from hypothesis import strategies as st
from net_checks import assert_consistent

from cube_net.core.cutting import CutLine, CutPoint, connected_regions, split_net
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
    assert len(split.net.perimeters()) == 2
