# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Iterator
from dataclasses import replace

import pytest

from cube_net.core.body import CUBE
from cube_net.ui import palette
from cube_net.ui.style import DEFAULT_CUBE_LOOK, DEFAULT_STYLE, Look, apply_style
from cube_net.ui.style.apply import style_in_place

# A project's look that isn't the default one.
OTHER = Look(replace(DEFAULT_STYLE, edge_width=1.5, hatch_rows=2.0), ("#111111", *CUBE.colors[1:]), CUBE)


@pytest.fixture(autouse=True)
def the_cubes_colours_again() -> Iterator[None]:
    yield
    palette.set_face_colors(CUBE.colors, CUBE)


def test_the_built_in_cubes_look() -> None:
    assert Look(DEFAULT_STYLE, CUBE.colors, CUBE) == DEFAULT_CUBE_LOOK


def test_a_look_used_for_a_while() -> None:
    apply_style(OTHER.style)
    palette.set_face_colors(OTHER.face_colors, OTHER.body)
    with DEFAULT_CUBE_LOOK.used():
        assert style_in_place() == DEFAULT_STYLE
        assert palette.face_colors_in_place() == (CUBE.colors, CUBE)
    assert style_in_place() == OTHER.style
    assert palette.face_colors_in_place() == (OTHER.face_colors, CUBE)


def test_the_look_before_it_again_even_after_an_error() -> None:
    with pytest.raises(RuntimeError), OTHER.used():
        raise RuntimeError
    assert style_in_place() == DEFAULT_STYLE
    assert palette.face_colors_in_place() == (CUBE.colors, CUBE)
