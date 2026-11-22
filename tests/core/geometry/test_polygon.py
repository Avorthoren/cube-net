# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.geometry import Vec, area_centroid, polygon_contains, signed_area

SQUARE = [Vec(0, 0), Vec(2, 0), Vec(2, 2), Vec(0, 2)]
L_SHAPE = [Vec(0, 0), Vec(2, 0), Vec(2, 1), Vec(1, 1), Vec(1, 2), Vec(0, 2)]  # non-convex


def test_signed_area_orientation() -> None:
    assert signed_area(SQUARE) == 4
    assert signed_area(list(reversed(SQUARE))) == -4
    assert signed_area(L_SHAPE) == 3
    assert signed_area([Vec(0, 0), Vec(1, 0), Vec(0, F(1, 3))]) == F(1, 6)


@pytest.mark.parametrize(
    ("p", "expected"),
    [
        (Vec(1, 1), True),
        (Vec(0, 0), True),  # corner
        (Vec(1, 0), True),  # on a side
        (Vec(3, 1), False),
        (Vec(F(-1, 1000), 1), False),
    ],
)
def test_contains_square(p: Vec, expected: bool) -> None:
    assert polygon_contains(SQUARE, p) is expected


@pytest.mark.parametrize(
    ("p", "expected"),
    [
        (Vec(F(1, 2), F(3, 2)), True),  # in the upper arm
        (Vec(F(3, 2), F(1, 2)), True),  # in the right arm
        (Vec(F(3, 2), F(3, 2)), False),  # in the notch
        (Vec(1, F(3, 2)), True),  # on the reflex side
        (Vec(1, 1), True),  # the reflex corner
        (Vec(2, F(3, 2)), False),  # on the line of a side, but outside
    ],
)
def test_contains_non_convex(p: Vec, expected: bool) -> None:
    assert polygon_contains(L_SHAPE, p) is expected


def test_contains_orientation_independent() -> None:
    assert polygon_contains(list(reversed(L_SHAPE)), Vec(F(1, 2), F(3, 2)))
    assert not polygon_contains(list(reversed(L_SHAPE)), Vec(F(3, 2), F(3, 2)))


class TestAreaCentroid:
    def test_a_square_and_an_l(self) -> None:
        assert area_centroid([SQUARE]) == Vec(1, 1)
        # The L: squares (0..2) x (0..1) and (0..1) x (1..2), of areas 2 and 1.
        assert area_centroid([L_SHAPE]) == Vec(F(5, 6), F(5, 6))

    def test_a_hole_is_taken_away(self) -> None:
        """A 4 x 4 square with a 2 x 2 hole near its corner: (16 * (2, 2) - 4 * (3/2, 3/2)) / 12."""
        outer = [Vec(0, 0), Vec(4, 0), Vec(4, 4), Vec(0, 4)]
        hole = [Vec(F(1, 2), F(1, 2)), Vec(F(5, 2), F(1, 2)), Vec(F(5, 2), F(5, 2)), Vec(F(1, 2), F(5, 2))]
        assert area_centroid([outer], [hole]) == (Vec(2, 2) * 16 - Vec(F(3, 2), F(3, 2)) * 4) / 12

    @pytest.mark.parametrize("outer_reversed", [False, True])
    @pytest.mark.parametrize("hole_reversed", [False, True])
    def test_the_way_loops_run_doesnt_matter(self, outer_reversed: bool, hole_reversed: bool) -> None:
        outer = [Vec(0, 0), Vec(4, 0), Vec(4, 4), Vec(0, 4)]
        hole = [Vec(1, 1), Vec(2, 1), Vec(2, 2), Vec(1, 2)]
        solids = [list(reversed(outer)) if outer_reversed else outer]
        holes = [list(reversed(hole)) if hole_reversed else hole]
        assert area_centroid(solids, holes) == (Vec(2, 2) * 16 - Vec(F(3, 2), F(3, 2))) / 15

    def test_solids_side_by_side_add_up(self) -> None:
        right = [p + Vec(2, 0) for p in reversed(SQUARE)]  # (run the other way: no matter)
        assert area_centroid([SQUARE, right]) == Vec(2, 1)

    def test_a_slit_weighs_nothing(self) -> None:
        """Into the square's top side and back out the same way."""
        slit = [Vec(0, 0), Vec(2, 0), Vec(2, 2), Vec(1, 2), Vec(1, 1), Vec(1, 2), Vec(0, 2)]
        assert area_centroid([slit]) == Vec(1, 1)

    def test_no_area(self) -> None:
        assert area_centroid([]) is None
        assert area_centroid([[Vec(0, 0), Vec(1, 1)]]) is None
        assert area_centroid([SQUARE], [SQUARE]) is None  # all taken away
