# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.geometry.vec import Vec, to_fraction

fractions = st.fractions(max_denominator=1000, min_value=-100, max_value=100)
vecs = st.builds(Vec, fractions, fractions)


class TestConstruction:
    def test_ints_become_fractions(self) -> None:
        v = Vec(1, -2)
        assert type(v.x) is F and type(v.y) is F
        assert v == Vec(F(1), F(-2))

    def test_fractions_kept_exactly(self) -> None:
        v = Vec(F(1, 3), F(-7, 10))
        assert v.x == F(1, 3)
        assert v.y == F(-7, 10)

    @pytest.mark.parametrize("bad", [0.5, 1.0, True, "1", None, complex(1, 0)])
    def test_inexact_or_non_numbers_rejected(self, bad: object) -> None:
        with pytest.raises(TypeError):
            Vec(bad, 0)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            Vec(0, bad)  # type: ignore[arg-type]

    def test_to_fraction_rejects_float(self) -> None:
        with pytest.raises(TypeError):
            to_fraction(0.1)

    def test_immutable(self) -> None:
        v = Vec(1, 2)
        with pytest.raises(AttributeError):
            v.x = F(5)  # type: ignore[misc]


class TestEqualityAndOrdering:
    def test_equal_values_equal_hashes(self) -> None:
        assert Vec(F(2, 4), 1) == Vec(F(1, 2), F(3, 3))
        assert hash(Vec(F(2, 4), 1)) == hash(Vec(F(1, 2), 1))
        assert len({Vec(1, 2), Vec(F(2, 2), 2), Vec(2, 1)}) == 2

    def test_not_equal_to_tuple(self) -> None:
        assert Vec(1, 2) != (1, 2)

    def test_lexicographic_order(self) -> None:
        points = [Vec(1, 0), Vec(0, 5), Vec(0, -1), Vec(1, -3)]
        assert sorted(points) == [Vec(0, -1), Vec(0, 5), Vec(1, -3), Vec(1, 0)]


class TestArithmetic:
    def test_add_sub_neg(self) -> None:
        a, b = Vec(1, F(1, 2)), Vec(F(-1, 3), 2)
        assert a + b == Vec(F(2, 3), F(5, 2))
        assert a - b == Vec(F(4, 3), F(-3, 2))
        assert -a == Vec(-1, F(-1, 2))

    def test_scalar_mul_both_sides_and_div(self) -> None:
        v = Vec(2, F(-3, 4))
        assert v * 2 == Vec(4, F(-3, 2))
        assert 2 * v == v * 2
        assert F(1, 2) * v == Vec(1, F(-3, 8))
        assert v / 4 == Vec(F(1, 2), F(-3, 16))

    def test_div_by_zero(self) -> None:
        with pytest.raises(ZeroDivisionError):
            Vec(1, 1) / 0

    def test_float_scalar_rejected(self) -> None:
        with pytest.raises(TypeError):
            Vec(1, 1) * 0.5  # type: ignore[operator]
        with pytest.raises(TypeError):
            Vec(1, 1) / 0.5  # type: ignore[operator]

    def test_dot_cross_length(self) -> None:
        a, b = Vec(3, 4), Vec(-4, 3)
        assert a.dot(b) == 0
        assert a.cross(b) == 25  # b is counter-clockwise from a
        assert b.cross(a) == -25
        assert a.length_squared() == 25

    def test_is_zero_and_floats(self) -> None:
        assert Vec(0, 0).is_zero()
        assert not Vec(0, F(1, 1000)).is_zero()
        assert Vec(F(1, 4), -3).to_floats() == (0.25, -3.0)

    def test_repr(self) -> None:
        assert repr(Vec(F(1, 2), -3)) == "Vec(1/2, -3)"


class TestRotation:
    @pytest.mark.parametrize(
        ("k", "expected"),
        [(0, Vec(2, 1)), (1, Vec(-1, 2)), (2, Vec(-2, -1)), (3, Vec(1, -2)), (4, Vec(2, 1)), (-1, Vec(1, -2))],
    )
    def test_counter_clockwise_quarter_turns(self, k: int, expected: Vec) -> None:
        assert Vec(2, 1).rotated90(k) == expected

    def test_default_is_one_quarter_turn(self) -> None:
        assert Vec(1, 0).rotated90() == Vec(0, 1)


class TestProperties:
    @given(vecs, vecs, vecs)
    def test_addition_group(self, a: Vec, b: Vec, c: Vec) -> None:
        assert (a + b) + c == a + (b + c)
        assert a + b == b + a
        assert a - a == Vec(0, 0)
        assert a + (-a) == Vec(0, 0)

    @given(vecs, vecs)
    def test_cross_antisymmetric_dot_symmetric(self, a: Vec, b: Vec) -> None:
        assert a.cross(b) == -b.cross(a)
        assert a.dot(b) == b.dot(a)

    @given(vecs, vecs, st.integers(-8, 8))
    def test_rotation_preserves_dot_and_cross(self, a: Vec, b: Vec, k: int) -> None:
        ra, rb = a.rotated90(k), b.rotated90(k)
        assert ra.dot(rb) == a.dot(b)
        assert ra.cross(rb) == a.cross(b)

    @given(vecs, st.integers(-8, 8), st.integers(-8, 8))
    def test_rotations_compose(self, a: Vec, k: int, m: int) -> None:
        assert a.rotated90(k).rotated90(m) == a.rotated90(k + m)
        assert a.rotated90(k).rotated90(-k) == a


class TestArithmeticGivesProperVecs:
    """Arithmetic skips the checks of the constructor: what it makes must still be like any other `Vec`."""

    def test_results_hold_fractions(self) -> None:
        a, b = Vec(1, 2), Vec(F(1, 3), 5)
        for result in (a + b, a - b, -a, a * 2, a * F(1, 2), 3 * a, a / 2, a / F(3, 4)):
            assert isinstance(result, Vec)
            assert isinstance(result.x, F) and isinstance(result.y, F)

    def test_equal_and_hashed_like_any_other(self) -> None:
        made = Vec(1, 2) + Vec(F(1, 2), 1)
        plain = Vec(F(3, 2), 3)
        assert made == plain
        assert hash(made) == hash(plain)
        assert not made < plain and not plain < made

    def test_results_stay_immutable(self) -> None:
        made = Vec(1, 2) + Vec(3, 4)
        with pytest.raises(AttributeError):
            made.x = F(0)  # type: ignore[misc]
