# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.cutting.placement import Axis, Constraint, LineKind, Problem, fold_through
from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, Net, default_net


@pytest.fixture
def net() -> Net:
    return default_net()


def edge_between(net: Net, a: Vec, b: Vec) -> HalfEdge:
    return next(he for he in net.boundary_edges() if {he.origin.position, he.destination.position} == {a, b})


def fold_between(net: Net, a: Vec, b: Vec) -> HalfEdge:
    return next(he for he in net.fold_edges() if {he.origin.position, he.destination.position} == {a, b})


def test_free_both_typed(net: Net) -> None:
    free = Constraint.free()
    assert free.kind is LineKind.FREE and free.axis is Axis.BOTH and not free.bound
    assert free.point_from(Axis.BOTH, F(23, 2), F(27, 2)) == Vec(F(23, 2), F(27, 2))


def test_a_vertical_edge_y_typed_x_fixed(net: Net) -> None:
    edge = Constraint.on_edge(edge_between(net, Vec(10, 12), Vec(10, 13)))
    assert edge.axis is Axis.Y and edge.bound
    assert edge.point_from(Axis.Y, F(99), F(61, 5)) == Vec(10, F(61, 5))  # x is the line's, whatever was there
    assert edge.point_from(Axis.X, F(99), F(61, 5)) == Vec(10, F(61, 5))  # x can't be the typed one


def test_a_horizontal_line_x_typed_y_fixed(net: Net) -> None:
    fold = Constraint.on_fold(fold_between(net, Vec(11, 13), Vec(12, 13)))
    assert fold.axis is Axis.X
    assert fold.point_from(Axis.X, F(23, 2), F(99)) == Vec(F(23, 2), 13)


def test_a_slanted_line_either_gives_the_other() -> None:
    slanted = Constraint(LineKind.EDGE, Vec(10, 10), Vec(13, 12))
    assert slanted.axis is Axis.BOTH and slanted.bound
    assert slanted.point_from(Axis.Y, F(0), F(11)) == Vec(F(23, 2), 11)  # x = 10 + (11 - 10) * 3 / 2
    assert slanted.point_from(Axis.X, F(23, 2), F(0)) == Vec(F(23, 2), 11)  # y = 10 + (23/2 - 10) * 2 / 3
    assert slanted.point_from(Axis.X, F(11), F(0)) == Vec(11, F(32, 3))


@pytest.mark.parametrize(("horizontal", "axis"), [(True, Axis.X), (False, Axis.Y)])
def test_shifts_lines(horizontal: bool, axis: Axis) -> None:
    straight = Constraint.straight(Vec(F(23, 2), 14), horizontal)
    assert straight.kind is LineKind.STRAIGHT and straight.axis is axis
    expected = Vec(F(5), 14) if horizontal else Vec(F(23, 2), F(7))
    assert straight.point_from(Axis.BOTH, F(5), F(7)) == expected


class TestProblems:
    def test_an_edge_point_stays_between_its_ends(self, net: Net) -> None:
        edge = Constraint.on_edge(edge_between(net, Vec(10, 12), Vec(10, 13)))
        assert edge.problem(net, Vec(10, F(25, 2))) is None
        assert edge.problem(net, Vec(10, 13)) is None  # its end: that's the vertex
        assert edge.problem(net, Vec(10, F(27, 2))) is Problem.OFF_EDGE

    def test_a_fold_point_stays_between_its_ends_and_inside(self, net: Net) -> None:
        fold = Constraint.on_fold(fold_between(net, Vec(11, 13), Vec(12, 13)))
        assert fold.problem(net, Vec(F(23, 2), 13)) is None
        assert fold.problem(net, Vec(F(25, 2), 13)) is Problem.OFF_FOLD
        assert fold.problem(net, Vec(11, 13)) is Problem.ON_PERIMETER  # its end is a vertex of the perimeter

    def test_a_free_point_strictly_inside(self, net: Net) -> None:
        free = Constraint.free()
        assert free.problem(net, Vec(F(23, 2), F(27, 2))) is None
        assert free.problem(net, Vec(9, 9)) is Problem.OUTSIDE_NET
        assert free.problem(net, Vec(F(23, 2), 14)) is Problem.ON_PERIMETER

    def test_shifts_line_is_unbounded_but_the_point_inside(self, net: Net) -> None:
        straight = Constraint.straight(Vec(F(23, 2), 14), horizontal=False)
        assert straight.problem(net, Vec(F(23, 2), F(27, 2))) is None
        assert straight.problem(net, Vec(F(23, 2), 20)) is Problem.OUTSIDE_NET


def test_the_fold_a_point_is_on(net: Net) -> None:
    fold = fold_through(net, Vec(F(23, 2), 13))
    assert fold is not None and {fold.origin.position, fold.destination.position} == {Vec(11, 13), Vec(12, 13)}
    assert fold_through(net, Vec(F(23, 2), F(27, 2))) is None


class TestNearest:
    """The point of the line closest to a point (where the dashed line ends while a point is placed by typing)."""

    def test_an_edge_between_its_ends(self, net: Net) -> None:
        edge = Constraint.on_edge(edge_between(net, Vec(10, 12), Vec(10, 13)))
        assert edge.nearest(Vec(F(21, 2), F(25, 2))) == Vec(10, F(25, 2))  # straight across
        assert edge.nearest(Vec(F(21, 2), 20)) == Vec(10, 13)  # beyond its end: its end
        assert edge.nearest(Vec(10, 11)) == Vec(10, 12)  # even along its own line (another edge goes on there)

    def test_a_slanted_edge(self) -> None:
        slanted = Constraint(LineKind.EDGE, Vec(10, 10), Vec(13, 14))
        assert slanted.nearest(Vec(14, 10)) == Vec(F(286, 25), F(298, 25))  # t = 12/25 along it
        assert slanted.nearest(Vec(20, 20)) == Vec(13, 14)

    def test_a_fold_between_its_ends(self, net: Net) -> None:
        fold = Constraint.on_fold(fold_between(net, Vec(11, 13), Vec(12, 13)))
        assert fold.nearest(Vec(F(23, 2), F(27, 2))) == Vec(F(23, 2), 13)
        assert fold.nearest(Vec(15, 13)) == Vec(12, 13)

    def test_shifts_line_has_no_ends(self) -> None:
        straight = Constraint.straight(Vec(F(23, 2), 14), horizontal=False)
        assert straight.nearest(Vec(12, 5)) == Vec(F(23, 2), 5)

    def test_free_is_where_it_is(self) -> None:
        assert Constraint.free().nearest(Vec(1, 2)) == Vec(1, 2)


class TestLockedSlope:
    def test_along_a_slanted_slope_both_typed(self) -> None:
        line = Constraint.along(Vec(10, F(25, 2)), Vec(2, 1))
        assert line.kind is LineKind.STRAIGHT and line.axis is Axis.BOTH and line.bound
        assert line.point_from(Axis.X, F(11), F(0)) == Vec(11, 13)
        assert line.point_from(Axis.Y, F(0), F(13)) == Vec(11, 13)
        assert line.nearest(Vec(15, 15)) == Vec(15, 15)  # on it: (10, 12.5) + 2.5 * (2, 1); no ends

    def test_fixed_nothing_typed(self, net: Net) -> None:
        edge = Constraint.on_edge(edge_between(net, Vec(10, 12), Vec(10, 13))).fixed_at(Vec(10, F(51, 4)))
        assert edge.axis is Axis.NONE and edge.bound and edge.kind is LineKind.EDGE
        assert edge.point_from(Axis.X, F(0), F(0)) == Vec(10, F(51, 4))
        assert edge.nearest(Vec(0, 0)) == Vec(10, F(51, 4))
