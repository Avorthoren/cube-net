# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.geometry import Vec
from cube_net.core.geometry.quantize import QUANTUM, quantize, quantize_scalar

finite_floats = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)


class TestQuantizeScalar:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0.0, F(0)),
            (11.0, F(11)),
            (11.4996, F(11500, 1000)),
            (11.5004, F(11500, 1000)),
            (0.1, F(1, 10)),  # 0.1 is not exactly representable, but rounds to exactly 1/10
            (-2.3456, F(-2346, 1000)),
            (3, F(3)),
        ],
    )
    def test_rounds_to_nearest_thousandth(self, value: float, expected: F) -> None:
        assert quantize_scalar(value) == expected

    def test_exact_ties_go_to_even(self) -> None:
        step = F(1, 2)  # 0.25 and 0.75 are exactly representable floats: real ties
        assert quantize_scalar(0.25, step) == 0
        assert quantize_scalar(0.75, step) == 1
        assert quantize_scalar(-0.25, step) == 0

    def test_custom_step(self) -> None:
        assert quantize_scalar(0.26, F(1, 4)) == F(1, 4)
        assert quantize_scalar(7.9, F(1)) == 8

    def test_result_is_fraction(self) -> None:
        assert type(quantize_scalar(1.23)) is F

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_rejected(self, bad: float) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            quantize_scalar(bad)

    @pytest.mark.parametrize("bad", [True, "1.0", None, F(1, 3)])
    def test_non_float_rejected(self, bad: object) -> None:
        with pytest.raises(TypeError):
            quantize_scalar(bad)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad_step", [F(0), F(-1, 1000), 0.001])
    def test_bad_step_rejected(self, bad_step: object) -> None:
        with pytest.raises(ValueError, match="step"):
            quantize_scalar(1.0, bad_step)  # type: ignore[arg-type]

    @given(finite_floats)
    def test_result_on_grid_and_close(self, value: float) -> None:
        q = quantize_scalar(value)
        assert (q / QUANTUM).denominator == 1
        assert abs(q - F(value)) <= QUANTUM / 2

    @given(finite_floats)
    def test_idempotent(self, value: float) -> None:
        q = quantize_scalar(value)
        assert quantize_scalar(float(q)) == q

    @given(finite_floats)
    def test_symmetric_under_negation(self, value: float) -> None:
        assert quantize_scalar(-value) == -quantize_scalar(value)


class TestQuantize:
    def test_returns_exact_vec(self) -> None:
        assert quantize(11.2504, 12.9996) == Vec(F(11250, 1000), 13)

    def test_custom_step(self) -> None:
        assert quantize(0.3, -0.3, F(1, 2)) == Vec(F(1, 2), F(-1, 2))
