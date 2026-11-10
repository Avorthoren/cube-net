# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F
from random import Random

import pytest

from cube_net.core.geometry import Vec
from cube_net.core.ruler import Ruler, distance, restricted_point, squared_distance


def test_distance() -> None:
    assert squared_distance(Vec(11, 12), Vec(F(25, 2), F(53, 4))) == F(61, 16)
    assert distance(Vec(0, 0), Vec(3, 4)) == 5.0
    assert distance(Vec(11, 12), Vec(F(25, 2), F(53, 4))) == pytest.approx(1.9526, abs=1e-4)


def test_points_and_segments() -> None:
    ruler = Ruler()
    assert ruler.points == () and ruler.last is None and ruler.segments() == []
    a, b, c = Vec(0, 0), Vec(1, 0), Vec(1, 1)
    for p in (a, b, c):
        ruler.add(p)
    assert ruler.points == (a, b, c)
    assert ruler.last == c
    assert ruler.segments() == [(a, b), (b, c)]
    ruler.clear()
    assert ruler.points == ()


def test_total_length_sums_before_rounding() -> None:
    ruler = Ruler()
    assert ruler.total_length() == 0.0
    ruler.add(Vec(0, 0))
    assert ruler.total_length() == 0.0
    # Three segments of length 0.0004 each: rounding each to 3 decimals first would give 0.000 instead of 0.001.
    for i in range(1, 4):
        ruler.add(Vec(F(4 * i, 10000), 0))
    assert f"{ruler.total_length():.3f}" == "0.001"
    ruler.add(Vec(F(12, 10000), 1))
    assert ruler.total_length() == pytest.approx(0.0012 + 1)


class TestRestrictedPoint:
    def test_without_points_nothing_to_restrict(self) -> None:
        assert restricted_point((), Vec(F(3, 2), 2)) == Vec(F(3, 2), 2)

    @pytest.mark.parametrize(
        ("p", "expected"),
        [((3, F(3, 2)), (3, 1)), ((F(3, 2), 4), (1, 4)), ((2, 2), (2, 1))],
        ids=["horizontal", "vertical", "a tie goes horizontal"],
    )
    def test_first_segment(self, p: tuple[F, F], expected: tuple[F, F]) -> None:
        assert restricted_point([Vec(1, 1)], Vec(*p)) == Vec(*expected)

    def test_parallel_to_a_slanted_previous_segment(self) -> None:
        points = [Vec(0, 0), Vec(2, 1)]
        on_the_line = Vec(F(61, 10), F(61, 20))
        q = restricted_point(points, on_the_line + Vec(F(-1, 100), F(1, 50)))
        assert (q - points[1]).cross(Vec(2, 1)) == 0
        assert (q - on_the_line).length_squared() < F(1, 10**4)

    def test_perpendicular_to_a_slanted_previous_segment(self) -> None:
        points = [Vec(0, 0), Vec(2, 1)]
        q = restricted_point(points, Vec(F(9, 10), F(31, 10)))
        assert (q - points[1]).dot(Vec(2, 1)) == 0

    def test_whichever_is_closer(self) -> None:
        points = [Vec(0, 0), Vec(1, 0)]
        assert restricted_point(points, Vec(5, 1)) == Vec(5, 0)
        assert restricted_point(points, Vec(F(3, 2), 5)) == Vec(1, 5)

    def test_a_zero_length_segment_does_not_count(self) -> None:
        points = [Vec(0, 0), Vec(2, 1), Vec(2, 1)]
        q = restricted_point(points, Vec(6, 3))
        assert (q - Vec(2, 1)).cross(Vec(2, 1)) == 0

    def test_only_equal_points_is_like_the_first_segment(self) -> None:
        assert restricted_point([Vec(1, 1), Vec(1, 1)], Vec(3, F(6, 5))) == Vec(3, 1)

    def test_numbers_stay_small_along_a_long_ruler(self) -> None:
        """Every point would multiply the denominators otherwise."""
        rng = Random(3)
        points = [Vec(0, 0), Vec(F(1234, 1000), F(567, 1000))]
        for _ in range(60):
            last = points[-1]
            p = last + Vec(F(rng.randint(-3000, 3000), 1000), F(rng.randint(-3000, 3000), 1000))
            points.append(restricted_point(points, p))
        assert max(max(q.x.denominator, q.y.denominator) for q in points) < 10**12
        for a, b, c in zip(points, points[1:], points[2:], strict=False):
            if a != b and b != c:
                d, e = b - a, c - b
                assert d.cross(e) == 0 or d.dot(e) == 0

    def test_it_is_near_the_exact_point_on_its_line(self) -> None:
        points = [Vec(0, 0), Vec(3, 7)]
        d = Vec(3, 7)
        for x in range(50):
            p = Vec(F(30 + x, 10), F(70 + 2 * x, 10))
            q = restricted_point(points, p)
            exact = points[1] + d * ((p - points[1]).dot(d) / d.length_squared())
            if (q - points[1]).cross(d) == 0:
                assert abs((q - exact).x) + abs((q - exact).y) <= F(1, 1000)
