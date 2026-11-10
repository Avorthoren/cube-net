# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.cutting import closest_straight_point, line_meets_segment, straighten
from cube_net.core.geometry import Vec
from cube_net.core.net import default_net


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


@pytest.mark.parametrize(
    ("p", "expected"),
    [
        pytest.param(v("3", "1.5"), v("3", "1"), id="closer to the horizontal, to the right"),
        pytest.param(v("-1", "0.5"), v("-1", "1"), id="closer to the horizontal, to the left"),
        pytest.param(v("1.5", "4"), v("1", "4"), id="closer to the vertical, up"),
        pytest.param(v("0.5", "-2"), v("1", "-2"), id="closer to the vertical, down"),
        pytest.param(v("2", "2"), v("2", "1"), id="a tie goes to the horizontal"),
        pytest.param(v("1", "1"), v("1", "1"), id="the anchor itself"),
        pytest.param(v("5", "1"), v("5", "1"), id="already horizontal"),
        pytest.param(v("1", "5"), v("1", "5"), id="already vertical"),
    ],
)
def test_straighten(p: Vec, expected: Vec) -> None:
    assert straighten(Vec(1, 1), p) == expected


class TestLineMeetsSegment:
    def test_crossing(self) -> None:
        assert line_meets_segment(Vec(0, 0), Vec(1, 0), Vec(3, -1), Vec(3, 1)) == Vec(3, 0)

    def test_the_line_goes_on_past_its_two_points(self) -> None:
        assert line_meets_segment(Vec(0, 0), Vec(1, 0), Vec(-3, -1), Vec(-3, 1)) == Vec(-3, 0)

    def test_slanted_is_exact(self) -> None:
        assert line_meets_segment(Vec(0, 0), Vec(0, 1), Vec(-1, 1), Vec(2, 2)) == Vec(0, F(4, 3))

    def test_past_the_end_of_the_segment(self) -> None:
        assert line_meets_segment(Vec(0, 0), Vec(1, 0), Vec(3, 1), Vec(3, 2)) is None

    def test_at_the_end_of_the_segment(self) -> None:
        assert line_meets_segment(Vec(0, 0), Vec(1, 0), Vec(3, 0), Vec(3, 2)) == Vec(3, 0)

    def test_parallel(self) -> None:
        assert line_meets_segment(Vec(0, 0), Vec(1, 0), Vec(0, 1), Vec(5, 1)) is None

    def test_along_the_segment(self) -> None:
        assert line_meets_segment(Vec(0, 0), Vec(2, 0), Vec(1, 0), Vec(5, 0)) == Vec(2, 0)

    def test_along_the_line_of_the_segment_but_off_it(self) -> None:
        assert line_meets_segment(Vec(0, 0), Vec(2, 0), Vec(3, 0), Vec(5, 0)) is None

    def test_no_line_without_two_points(self) -> None:
        assert line_meets_segment(Vec(1, 1), Vec(1, 1), Vec(0, 0), Vec(5, 5)) is None


class TestClosestStraightPoint:
    ANCHOR = v("11.5", "13.5")

    def test_on_the_cut_towards_the_mouse(self) -> None:
        found = closest_straight_point(default_net(), self.ANCHOR, v("11.9", "13.6"))
        assert found is not None
        position, cut = found
        assert position == v("12", "13.5")
        assert {cut.origin.position.x, cut.destination.position.x} == {F(12)}

    def test_any_of_the_four_directions(self) -> None:
        net = default_net()
        for p, expected in (
            (v("11", "13.4"), v("11", "13.5")),
            (v("12", "13.6"), v("12", "13.5")),
            (v("11.6", "14"), v("11.5", "14")),
            (v("11.4", "10"), v("11.5", "10")),
        ):
            found = closest_straight_point(net, self.ANCHOR, p)
            assert found is not None and found[0] == expected

    def test_never_the_anchor_itself(self) -> None:
        anchor = v("11.5", "14")  # on the top of face 1
        found = closest_straight_point(default_net(), anchor, anchor)
        assert found is not None and found[0] != anchor

    def test_not_along_a_cut(self) -> None:
        """Sideways from the top of face 1: not the cut it stands on, but the ones it hits at A_1 and B_1."""
        found = closest_straight_point(default_net(), v("11.5", "14"), v("11.6", "14"))
        assert found is not None and found[0] in (Vec(11, 14), Vec(12, 14))
