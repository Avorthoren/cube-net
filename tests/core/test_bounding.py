from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.bounding import min_area_rectangle
from cube_net.core.geometry import Box, Rigid90, Vec, signed_area
from cube_net.core.net import default_net

grid = st.builds(Vec, st.integers(-6, 6), st.integers(-6, 6))
motions = st.builds(Rigid90, st.integers(0, 3), st.builds(Vec, st.fractions(-5, 5), st.fractions(-5, 5)))


def test_default_net_is_axis_aligned_3_by_4() -> None:
    """docs/idea.txt: 12.000 square units, an axis-aligned 3 x 4 rectangle."""
    r = min_area_rectangle(v.position for v in default_net().vertices)
    assert r.area == 12
    assert set(r.corners) == {Vec(10, 10), Vec(13, 10), Vec(13, 14), Vec(10, 14)}


def test_rotated_square_beats_axis_aligned_box() -> None:
    diamond = [Vec(0, 1), Vec(1, 0), Vec(2, 1), Vec(1, 2)]  # a square of side sqrt(2), turned by 45 degrees
    r = min_area_rectangle(diamond)
    assert r.area == 2  # not 4 (its axis-aligned box)
    assert set(r.corners) == set(diamond)


def test_rational_tilt_is_exact() -> None:
    # A 3-4-5 rectangle tilted along (4, 3): area exactly 5 * 10 = 50.
    a, b = Vec(0, 0), Vec(4, 3)
    d = Vec(-6, 8)
    r = min_area_rectangle([a, b, b + d, a + d])
    assert r.area == 50
    assert isinstance(r.area, F)


def test_degenerate_inputs() -> None:
    assert min_area_rectangle([Vec(1, 1)]).area == 0
    assert min_area_rectangle([Vec(0, 0), Vec(3, 1), Vec(6, 2)]).area == 0
    with pytest.raises(ValueError, match="at least one point"):
        min_area_rectangle([])


def test_corners_counter_clockwise() -> None:
    r = min_area_rectangle([Vec(0, 0), Vec(5, 1), Vec(4, 4), Vec(-1, 3)])
    assert signed_area(list(r.corners)) == r.area


@given(st.lists(grid, min_size=3, max_size=20))
def test_contains_all_points_and_not_larger_than_axis_box(points: list[Vec]) -> None:
    r = min_area_rectangle(points)
    box = Box.around(points)
    assert r.area <= box.width * box.height
    a, b, _, d = r.corners
    u, v = b - a, d - a
    for p in points:
        if r.area == 0:
            break
        q = p - a
        assert 0 <= q.dot(u) <= u.dot(u)
        assert 0 <= q.dot(v) <= v.dot(v)


@given(st.lists(grid, min_size=3, max_size=20), motions)
def test_area_does_not_depend_on_position_or_quarter_turns(points: list[Vec], m: Rigid90) -> None:
    assert min_area_rectangle(points).area == min_area_rectangle([m.apply(p) for p in points]).area
