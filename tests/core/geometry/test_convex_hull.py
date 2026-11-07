from fractions import Fraction as F

from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.geometry import Vec, convex_hull, orient, signed_area

grid = st.builds(Vec, st.integers(-5, 5), st.integers(-5, 5))


def test_square_with_inner_collinear_and_duplicate_points() -> None:
    points = [Vec(0, 0), Vec(2, 0), Vec(2, 2), Vec(0, 2), Vec(1, 1), Vec(1, 0), Vec(0, 0), Vec(2, F(1, 2))]
    assert convex_hull(points) == [Vec(0, 0), Vec(2, 0), Vec(2, 2), Vec(0, 2)]


def test_small_inputs() -> None:
    assert convex_hull([]) == []
    assert convex_hull([Vec(1, 1), Vec(1, 1)]) == [Vec(1, 1)]
    assert convex_hull([Vec(3, 0), Vec(1, 1)]) == [Vec(1, 1), Vec(3, 0)]


def test_collinear_points_give_the_two_ends() -> None:
    assert convex_hull([Vec(0, 0), Vec(1, 1), Vec(2, 2), Vec(3, 3)]) == [Vec(0, 0), Vec(3, 3)]


@given(st.lists(grid, min_size=3, max_size=30))
def test_hull_is_convex_ccw_and_contains_all_points(points: list[Vec]) -> None:
    hull = convex_hull(points)
    if len(hull) < 3:
        return
    n = len(hull)
    assert all(orient(hull[i], hull[(i + 1) % n], hull[(i + 2) % n]) == 1 for i in range(n))  # strictly convex
    assert signed_area(hull) > 0
    assert all(orient(hull[i], hull[(i + 1) % n], p) >= 0 for i in range(n) for p in points)
    assert set(hull) <= set(points)
