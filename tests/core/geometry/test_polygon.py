from fractions import Fraction as F

import pytest

from cube_net.core.geometry import Vec, polygon_contains, signed_area

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
