# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.geometry import Vec, quantize
from cube_net.ui.main_window import format_coordinates
from cube_net.ui.sheet.coordinates_text import (
    MAX_DIGITS,
    TOO_LONG,
    coordinate_lines,
    copied_text,
    decimal_text,
    is_exact,
)


def test_the_example() -> None:
    assert coordinate_lines(Vec(F(5405, 539), F(-892392, 7255))) == [
        "y: -892392/7255 ≈ -123.004",
        "x:    5405/539  ≈   10.028",  # the slashes, the signs and the decimal points under each other
    ]


def test_exact_ones_say_so_and_are_reduced() -> None:
    assert coordinate_lines(Vec(F(13123, 1000), F(7625, 1000))) == [
        "y:    61/8    =  7.625",
        "x: 13123/1000 = 13.123",
    ]


def test_an_integer_is_just_that_number() -> None:
    assert coordinate_lines(Vec(F(101, 8), F(17))) == [
        "y:  17",
        "x: 101/8 = 12.625",
    ]
    assert coordinate_lines(Vec(F(12), F(-3))) == ["y: -3", "x: 12"]


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (F(0), "0.000"),
        (F(-3, 10000), "-0.000"),  # a tiny negative keeps its sign
        (F(1, 2000), "0.000"),  # an exact tie: to the even thousandth, as `quantize`
        (F(3, 2000), "0.002"),
        (F(-1234567, 1000), "-1234.567"),
        (F(2, 3), "0.667"),
    ],
)
def test_decimals(value: F, text: str) -> None:
    assert decimal_text(value) == text


def test_exact_or_not() -> None:
    assert is_exact(F(61, 8)) and is_exact(F(12)) and not is_exact(F(2, 3))


def test_numbers_too_long_for_the_hint() -> None:
    long = 10**MAX_DIGITS + 1  # one digit too many
    longest = 10**MAX_DIGITS - 1  # just short enough
    lines = coordinate_lines(Vec(F(long, 3), F(7, long)))
    assert lines == [
        f"y: {'7':>8}/{TOO_LONG} ≈ {'0':>10}.000",
        f"x: {TOO_LONG}/{'3':<8} ≈ 3333333333.667",
    ]
    assert str(longest) in coordinate_lines(Vec(F(longest), F(0)))[1]


def test_the_copied_text_has_every_number() -> None:
    long = 10**MAX_DIGITS + 1
    assert copied_text(Vec(F(long, 3), F(7, long))) == (
        f"y: {'7':>11}/{long} ≈ {'0':>10}.000\nx: {long}/{'3':<11} ≈ 3333333333.667"
    )
    assert copied_text(Vec(F(61, 8), F(12))) == "\n".join(coordinate_lines(Vec(F(61, 8), F(12))))


@given(
    st.floats(min_value=-10_000, max_value=10_000, allow_nan=False),
    st.floats(min_value=-10_000, max_value=10_000, allow_nan=False),
)
def test_a_point_placed_where_the_mouse_is_shows_the_footers_digits(x: float, y: float) -> None:
    """A point made at the mouse is quantized; its hint shows what the footer showed when it was made."""
    point = quantize(x, y)
    footer = format_coordinates(x, y)
    expected_x, expected_y = (part.split(": ")[1] for part in footer.split("   "))
    if point.x != 0 or not expected_x.startswith("-"):  # -0.000 in the footer is 0 once quantized
        assert decimal_text(point.x) == expected_x
    if point.y != 0 or not expected_y.startswith("-"):
        assert decimal_text(point.y) == expected_y
