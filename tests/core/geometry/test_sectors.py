# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.geometry import Rigid90, Vec, sectors_overlap, strictly_within

E, N, W, S = Vec(1, 0), Vec(0, 1), Vec(-1, 0), Vec(0, -1)
NE, NW, SW, SE = Vec(1, 1), Vec(-1, 1), Vec(-1, -1), Vec(1, -1)


@pytest.mark.parametrize(
    ("start", "x", "end", "expected"),
    [
        (E, NE, N, True),  # a quarter
        (E, E, N, False),  # its edges are not inside
        (E, N, N, False),
        (E, SE, N, False),
        (E, N, W, True),  # half a turn
        (E, S, W, False),
        (E, W, W, False),
        (E, W, S, True),  # three quarters
        (E, SE, S, False),
        (E, Vec(2, 0), N, False),  # the length of a direction doesn't matter
        (Vec(5, 0), Vec(1, 1), Vec(0, 3), True),
    ],
)
def test_strictly_within(start: Vec, x: Vec, end: Vec, expected: bool) -> None:
    assert strictly_within(start, x, end) is expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ((E, N), (N, W), False),  # neighbours touching along N
        ((E, N), (W, S), False),  # opposite
        ((E, N), (NE, W), True),  # partly the same
        ((E, N), (E, NE), True),  # the same start
        ((E, N), (SE, NE), True),  # the second starts before and ends inside
        ((E, W), (W, E), False),  # two half-planes on opposite sides of a line: touching
        ((E, W), (E, W), True),  # the same half-plane
        ((E, S), (S, E), False),  # three quarters and the remaining quarter
        ((E, S), (SE, NE), True),  # the quarter around E reaches into the three quarters
    ],
)
def test_sectors_overlap(a: tuple[Vec, Vec], b: tuple[Vec, Vec], expected: bool) -> None:
    assert sectors_overlap(*a, *b) is expected
    assert sectors_overlap(*b, *a) is expected


directions = st.sampled_from([E, N, W, S, NE, NW, SW, SE])


@given(directions, directions, directions, directions, st.integers(0, 3))
def test_turning_everything_changes_nothing(a: Vec, b: Vec, c: Vec, d: Vec, k: int) -> None:
    r = Rigid90(k).apply_vector
    assert sectors_overlap(a, b, c, d) == sectors_overlap(r(a), r(b), r(c), r(d))
