# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

from cube_net.core.geometry import Vec, quantize
from cube_net.core.origin import DEFAULT_ORIGIN, Origin


def test_the_default_shows_the_sheet_coordinates() -> None:
    assert DEFAULT_ORIGIN.shown(Vec(11, 13)) == Vec(11, 13)
    assert DEFAULT_ORIGIN.point is None and DEFAULT_ORIGIN.name is None


def test_moved_by_a_point_shows_it_where_typed() -> None:
    origin = DEFAULT_ORIGIN.moved(Vec(11, 13), Vec(F(1, 3), -2), "C_1")
    assert origin.shown(Vec(11, 13)) == Vec(F(1, 3), -2)
    assert origin.shown(Vec(12, 14)) == Vec(F(4, 3), -1)  # a shift: the axes keep their directions
    assert origin.sheet(Vec(F(1, 3), -2)) == Vec(11, 13)
    assert (origin.point, origin.name) == (Vec(11, 13), "C_1")


def test_moving_again_starts_from_the_sheet_not_the_last_origin() -> None:
    once = DEFAULT_ORIGIN.moved(Vec(11, 13), Vec(0, 0), "C_1")
    twice = once.moved(Vec(12, 13), Vec(5, 5), "D_1")
    assert twice.shown(Vec(12, 13)) == Vec(5, 5)
    assert twice.shown(Vec(11, 13)) == Vec(4, 5)


def test_rounding_to_thousandths_of_the_shown_coordinates() -> None:
    assert DEFAULT_ORIGIN.quantize(11.2344, 13.0006) == quantize(11.2344, 13.0006)
    origin = Origin(Vec(F(1, 3), 0))
    p = origin.quantize(1.0, 2.0004)
    assert origin.shown(p) == Vec(F(667, 1000), F(2, 1))  # 1 - 1/3 = 0.6666... -> 0.667
    assert p == Vec(F(667, 1000) + F(1, 3), 2)
