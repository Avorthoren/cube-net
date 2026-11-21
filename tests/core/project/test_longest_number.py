# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace
from fractions import Fraction as F

from cube_net.core.geometry import MAX_NUMBER_DIGITS, Vec
from cube_net.core.origin import Origin
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.project.longest_number import longest_number
from cube_net.core.project.project import new_project


def test_a_new_project_has_short_numbers() -> None:
    assert 0 < longest_number(new_project()) <= 2


def test_the_longest_numerator_or_denominator_anywhere() -> None:
    project = new_project()
    origin = Origin(Vec(F(-(10**30) - 1, 7), 0), Vec(0, 0))
    assert longest_number(replace(project, state=replace(project.state, origin=origin))) == 31
    origin = Origin(Vec(F(1, 10**40), 0), Vec(0, 0))
    assert longest_number(replace(project, state=replace(project.state, origin=origin))) == 41


def test_a_templates_too() -> None:
    document = cube_with_a_hole()
    long = Vec(F(1, 10**MAX_NUMBER_DIGITS), 0)
    assert longest_number(replace(document, state=replace(document.state, origin=Origin(long, long)))) == (
        MAX_NUMBER_DIGITS + 1
    )


def test_the_built_in_template_keeps_to_the_limit() -> None:
    assert longest_number(cube_with_a_hole()) <= MAX_NUMBER_DIGITS
