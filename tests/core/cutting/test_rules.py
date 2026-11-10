# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from fractions import Fraction as F
from math import ceil, lcm

from cube_net.core.cutting import (
    CutLine,
    CutPoint,
    invalid_segments,
    project_onto,
    segment_allowed,
    segment_valid,
    strictly_inside,
)
from cube_net.core.cutting.rules import PROJECTION_STEP
from cube_net.core.geometry import Vec, on_segment
from cube_net.core.net import HalfEdge, Net


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


def test_project_onto_clamps_to_the_cut(cut: Callable[[str], HalfEdge]) -> None:
    top = cut("B_1-A_1")  # y = 14, x from 12 to 11
    assert project_onto(top, v("11.5", "13.9")) == v("11.5", "14")
    assert project_onto(top, v("10.5", "13.9")) == v("11", "14")  # beyond the end: the end itself


def test_strictly_inside(net: Net) -> None:
    assert strictly_inside(net, v("11.5", "12.5"))
    assert strictly_inside(net, v("11", "12.5"))  # on fold C-H: inside the net
    assert not strictly_inside(net, v("10", "12.5"))  # on the perimeter
    assert not strictly_inside(net, v("9.5", "12.5"))  # outside


def line_from(edge: HalfEdge, *points: Vec) -> CutLine:
    first, *rest = points
    return CutLine([CutPoint(first, edge), *(CutPoint(p) for p in rest)])


def test_first_segment_into_the_net(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    line = line_from(cut("B_1-A_1"), v("11.5", "14"))
    assert segment_allowed(net, line, CutPoint(v("11.5", "13.5")))
    assert not segment_allowed(net, line, CutPoint(v("11.5", "14.5")))  # out of the net
    assert not segment_allowed(net, line, CutPoint(v("11.8", "14"), cut("B_1-A_1")))  # along its own cut


def test_crossing_or_touching_the_perimeter_is_rejected(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    line = line_from(cut("A_2-E_2"), v("10", "12.5"), v("10.5", "12.5"))
    assert not segment_allowed(net, line, CutPoint(v("11.5", "11.5")))  # leaves face 4 through E_2-H_1
    assert not segment_allowed(net, line, CutPoint(v("11.5", "13.5")))  # passes exactly through C_1 (reflex corner)
    assert segment_allowed(net, line, CutPoint(v("11.5", "12.5")))  # crosses fold C-H: fine


def test_crossing_or_going_back_along_itself_is_rejected(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    line = line_from(cut("B_1-A_1"), v("11.5", "14"), v("11.5", "13"), v("11.8", "12.5"))
    assert not segment_allowed(net, line, CutPoint(v("11.2", "13.8")))  # crosses the first segment
    assert not segment_allowed(net, line, CutPoint(v("11.65", "12.75")))  # back along the previous segment
    assert not segment_allowed(net, line, CutPoint(v("11.5", "13")))  # onto an earlier point
    assert segment_allowed(net, line, CutPoint(v("12", "11.5"), cut("G_1-F_1")))  # ending on a cut


def test_end_on_the_start_is_rejected(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    top = cut("B_1-A_1")
    line = line_from(top, v("11.5", "14"), v("11.5", "13.5"))
    assert not segment_allowed(net, line, CutPoint(v("11.5", "14"), top))
    assert segment_allowed(net, line, CutPoint(v("11.7", "14"), top))  # same cut, other point: fine


def test_segment_valid_checks_any_segment_of_the_line(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    top = cut("B_1-A_1")
    good = [CutPoint(v("11.5", "14"), top), CutPoint(v("11.5", "13.5")), CutPoint(v("11.7", "14"), top)]
    assert all(segment_valid(net, good, i) for i in range(2))
    assert invalid_segments(net, good, (0, 1)) == []
    outside = [good[0], CutPoint(v("10.5", "13.5")), good[2]]  # the middle point is in the empty corner
    assert invalid_segments(net, outside, (0, 1)) == [0, 1]
    crossing = [
        CutPoint(v("11.2", "14"), top),
        CutPoint(v("11.8", "13.5")),
        CutPoint(v("11.2", "13.5")),
        CutPoint(v("11.8", "14"), top),
    ]
    assert invalid_segments(net, crossing, (0, 1, 2)) == [0, 2]  # the first and the last segments cross
    assert invalid_segments(net, good, (-1, 2, 5)) == []  # indices outside the line are ignored


class TestProjectionStaysSimple:
    """The numbers must not double in length with every generation of cuts (docs/plan.md, M10)."""

    def slanted(self) -> HalfEdge:
        from cube_net.core.cube import SurfacePoint
        from cube_net.core.net import EdgeKind, NetVertex

        a = NetVertex(0, Vec(F(1, 3), F(1, 7)), SurfacePoint(1, Vec(0, 0)))
        b = NetVertex(1, Vec(F(14, 3), F(22, 7)), SurfacePoint(1, Vec(1, 1)))
        edge, twin = HalfEdge(0, a, EdgeKind.BOUNDARY, None), HalfEdge(1, b, EdgeKind.BOUNDARY, None)
        edge.twin, twin.twin = twin, edge
        return edge

    def test_it_is_exactly_on_the_cut(self) -> None:
        edge = self.slanted()
        a, b = edge.origin.position, edge.destination.position
        p = project_onto(edge, v("2.5", "1.5"))
        assert on_segment(p, a, b)

    def test_it_is_near_the_exact_closest_point(self) -> None:
        edge = self.slanted()
        a, b = edge.origin.position, edge.destination.position
        d = b - a
        for query in (v("2.5", "1.5"), v("1.234", "0.777"), v("4.001", "2.999")):
            exact = a + d * ((query - a).dot(d) / d.length_squared())
            step = project_onto(edge, query) - exact
            assert step.length_squared() <= PROJECTION_STEP**2

    def test_the_denominator_does_not_square(self) -> None:
        edge = self.slanted()
        a, b = edge.origin.position, edge.destination.position
        limit = lcm(a.x.denominator, a.y.denominator, b.x.denominator, b.y.denominator)
        length = (b - a).length_squared()
        p = project_onto(edge, v("2.5", "1.5"))
        steps = ceil((abs((b - a).x) + abs((b - a).y)) / PROJECTION_STEP)
        assert max(p.x.denominator, p.y.denominator) <= limit * steps
        assert length.denominator > 1  # what the exact projection would have divided by

    def test_the_ends_are_reached(self) -> None:
        edge = self.slanted()
        assert project_onto(edge, Vec(-5, -5)) == edge.origin.position
        assert project_onto(edge, Vec(50, 50)) == edge.destination.position

    def test_a_very_short_cut_has_just_its_ends(self) -> None:
        from cube_net.core.cube import SurfacePoint
        from cube_net.core.net import EdgeKind, NetVertex

        a = NetVertex(0, Vec(0, 0), SurfacePoint(1, Vec(0, 0)))
        b = NetVertex(1, Vec(F(1, 5000), 0), SurfacePoint(1, Vec(1, 1)))
        edge, twin = HalfEdge(0, a, EdgeKind.BOUNDARY, None), HalfEdge(1, b, EdgeKind.BOUNDARY, None)
        edge.twin, twin.twin = twin, edge
        assert project_onto(edge, Vec(F(1, 20000), 0)) == a.position
        assert project_onto(edge, Vec(F(1, 6000), 0)) == b.position

    def test_on_a_cut_along_the_grid_it_is_as_before(self, cut: Callable[[str], HalfEdge]) -> None:
        top = cut("B_1-A_1")
        assert project_onto(top, v("11.123", "13.9")) == v("11.123", "14")
        assert project_onto(top, v("11.987", "14.5")) == v("11.987", "14")
