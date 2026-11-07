from fractions import Fraction as F

import pytest

from cube_net.core.geometry import Vec
from cube_net.core.ruler import Ruler, distance, squared_distance


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
