# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from fractions import Fraction as F

from cube_net.core.cutting import CutPoint, real_cut
from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, Net


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


def test_a_line_across_the_net_is_one_piece_dividing_it(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    line = [
        CutPoint(v("11.5", "14"), cut("B_1-A_1")),
        CutPoint(v("11.5", "13.5")),
        CutPoint(v("11", "13.5"), cut("A_2-C_1")),
    ]
    real = real_cut(net, line)
    assert real is not None and real.pieces == ((0, 2),) and real.dividing == 0 and real.divides_at_end
    assert [p.position for p in real.piece_line(0).points] == [p.position for p in line]


def test_off_the_net_and_back(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    """Out of face 1 into the empty corner on its left: the line divides the net where it leaves it, before its end."""
    line = [CutPoint(v("11.5", "14"), cut("B_1-A_1")), CutPoint(v("10.5", "13.5"))]
    real = real_cut(net, line)
    assert real is not None
    assert [s.own for s in real.stops] == [True, False, True] and real.inside == (True, False)
    assert real.dividing == 0 and not real.divides_at_end
    assert real.stops[1].point.position == v("11", "13.75") and real.stops[1].point.edge is not None


def test_an_open_line_has_no_piece_yet(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    real = real_cut(net, [CutPoint(v("11.5", "14"), cut("B_1-A_1")), CutPoint(v("11.5", "13.5"))])
    assert real is not None and real.pieces == () and real.dividing is None


def test_none_where_a_segment_touches_the_perimeter(net: Net, cut: Callable[[str], HalfEdge]) -> None:
    assert real_cut(net, [CutPoint(v("11.5", "14"), cut("B_1-A_1")), CutPoint(v("12.5", "12"))]) is None
