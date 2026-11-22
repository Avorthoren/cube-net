# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from fractions import Fraction as F

from cube_net.core.cutting import on_the_perimeter, segment_crossings
from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, Net


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


def test_a_point_on_the_perimeter(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    assert on_the_perimeter(net, v("11.5", "14")) is cut("B_1-A_1")
    assert on_the_perimeter(net, v("11.5", "13.5")) is None  # inside face 1
    assert on_the_perimeter(net, v("9", "9")) is None  # outside the net


def test_crossings_in_order_along_the_segment(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    """Across face 1 from left to right, from outside to outside: in at its left side, out at its right one."""
    crossings = segment_crossings(net, v("10.5", "13.5"), v("12.5", "13.5"))
    assert crossings is not None
    assert [c.position for c in crossings] == [v("11", "13.5"), v("12", "13.5")]
    assert all(c.edge is not None for c in crossings)


def test_crossings_are_exact_not_rounded(net: Net) -> None:
    """Where a segment crosses a cut is a rational point on it already: kept as it is (83/6 isn't on any grid of
    thousandths), not moved to a nearby one."""
    crossings = segment_crossings(net, Vec(10, F(27, 2)), Vec(13, F(29, 2)))  # in at face 1's left side, out at its top
    assert crossings is not None
    assert [c.position for c in crossings] == [Vec(11, F(83, 6)), Vec(F(23, 2), 14)]


def test_touching_the_perimeter_is_no_crossing(net: Net) -> None:
    assert segment_crossings(net, v("11.5", "14"), v("12.5", "12")) is None  # through the vertex D_1 at (12, 13)
    assert segment_crossings(net, v("11.2", "14"), v("11.8", "14")) is None  # along a cut
    assert segment_crossings(net, v("11.5", "14"), v("11.5", "13.5")) == []  # from its own end: fine
    assert segment_crossings(net, v("11.5", "13.5"), v("11.5", "13.5")) == []
