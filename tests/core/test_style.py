# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace

import pytest

from cube_net.core.style import Style, StyleError

# Some valid style (the defaults are the UI's style files').
STYLE = Style(
    hatch_columns=8,
    hatch_rows=2,
    dashes_per_edge=10,
    edge_width=4.0,
    vertex_radius=6.0,
    grid_color="#D3D3D3",
    grid_width=1.0,
)


@pytest.mark.parametrize(
    "values",
    [
        {"hatch_columns": 0},
        {"hatch_rows": 31},
        {"hatch_rows": 2.5},
        {"hatch_rows": True},
        {"dashes_per_edge": 0},
        {"edge_width": 0.5},
        {"edge_width": 15.5},
        {"edge_width": "4"},
        {"vertex_radius": 31.0},
        {"grid_width": -0.1},
        {"grid_width": 5.5},
        {"grid_color": "#12345"},
        {"grid_color": "red"},
        {"grid_color": None},
    ],
)
def test_out_of_range(values: dict[str, object]) -> None:
    with pytest.raises(StyleError):
        replace(STYLE, **values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "values",
    [
        {"hatch_columns": 1, "hatch_rows": 30},
        {"dashes_per_edge": 30},
        {"edge_width": 1.0},
        {"edge_width": 15},
        {"vertex_radius": 1.0},
        {"grid_width": 0.0},
        {"grid_width": 5.0},
    ],
)
def test_the_ends_of_the_ranges(values: dict[str, object]) -> None:
    replace(STYLE, **values)  # type: ignore[arg-type]
