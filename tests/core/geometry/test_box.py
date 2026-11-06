from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.geometry import Box, Vec

vecs = st.builds(Vec, st.fractions(-50, 50, max_denominator=100), st.fractions(-50, 50, max_denominator=100))


class TestBox:
    def test_size_and_center(self) -> None:
        b = Box(Vec(10, 10), Vec(13, 14))
        assert (b.width, b.height) == (3, 4)
        assert b.center == Vec(F(23, 2), 12)

    def test_corners_out_of_order_rejected(self) -> None:
        with pytest.raises(ValueError, match="out of order"):
            Box(Vec(1, 0), Vec(0, 1))

    def test_degenerate_allowed(self) -> None:
        b = Box(Vec(1, 1), Vec(1, 1))
        assert b.width == 0 and b.contains(Vec(1, 1))

    def test_around(self) -> None:
        assert Box.around([Vec(3, -1), Vec(0, 2), Vec(1, 5)]) == Box(Vec(0, -1), Vec(3, 5))

    def test_around_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one point"):
            Box.around([])

    def test_expanded(self) -> None:
        assert Box(Vec(10, 10), Vec(13, 14)).expanded(5) == Box(Vec(5, 5), Vec(18, 19))

    def test_contains_is_closed(self) -> None:
        b = Box(Vec(0, 0), Vec(1, 1))
        assert b.contains(Vec(0, 1)) and b.contains(Vec(F(1, 2), F(1, 2)))
        assert not b.contains(Vec(F(-1, 1000), 0))

    @given(st.lists(vecs, min_size=1, max_size=20))
    def test_around_contains_all_and_is_tight(self, points: list[Vec]) -> None:
        b = Box.around(points)
        assert all(b.contains(p) for p in points)
        assert {b.lo.x, b.hi.x} <= {p.x for p in points}
        assert {b.lo.y, b.hi.y} <= {p.y for p in points}
