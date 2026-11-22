# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Iterator

import pytest

from cube_net.core.body import CUBE
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.template import body_from_template
from cube_net.ui import palette


@pytest.fixture(autouse=True)
def the_cubes_colours_again() -> Iterator[None]:
    yield
    palette.set_face_colors(CUBE.colors, CUBE)


def test_the_open_projects_body_gets_its_colours() -> None:
    palette.set_face_colors(("#111111", *CUBE.colors[1:]), CUBE)
    assert palette.face_color(CUBE, 1).name().upper() == "#111111"


def test_another_body_keeps_its_own_colours() -> None:
    torus = body_from_template(cube_with_a_hole().state.template)
    palette.set_face_colors(("#111111",) * len(torus.face_numbers), torus)
    assert palette.face_color(torus, 2).name().upper() == "#111111"
    assert palette.face_color(CUBE, 2).name().upper() == CUBE.colors[1]


def test_the_colours_in_place() -> None:
    torus = body_from_template(cube_with_a_hole().state.template)
    colors = ("#111111",) * len(torus.face_numbers)
    palette.set_face_colors(colors, torus)
    assert palette.face_colors_in_place() == (colors, torus)
