from dataclasses import replace

import pytest

from cube_net.ui import palette
from cube_net.ui.sheet import net_style
from cube_net.ui.style import DEFAULT_STYLE, StyleError


def test_the_defaults_are_what_the_style_files_say() -> None:
    assert DEFAULT_STYLE.edge_width == net_style.EDGE_WIDTH_PX
    assert DEFAULT_STYLE.vertex_radius == net_style.VERTEX_RADIUS_PX
    assert (DEFAULT_STYLE.hatch_columns, DEFAULT_STYLE.hatch_rows) == (net_style.HATCH_COLUMNS, net_style.HATCH_ROWS)
    assert DEFAULT_STYLE.dashes_per_edge == net_style.DASHES_PER_EDGE
    assert DEFAULT_STYLE.face_colors[0] == palette.FACE_COLORS[1].name().upper()
    assert DEFAULT_STYLE.grid_color == palette.GRID.name().upper()


@pytest.mark.parametrize(
    "values",
    [
        {"hatch_columns": 0},
        {"hatch_rows": 31},
        {"dashes_per_edge": 0},
        {"edge_width": 0.5},
        {"edge_width": 15.5},
        {"vertex_radius": 31.0},
        {"grid_width": -0.1},
        {"grid_width": 5.5},
        {"grid_color": "#12345"},
        {"grid_color": "red"},
        {"face_colors": ("#000000",) * 5},
        {"face_colors": ("#00000g",) * 6},
    ],
)
def test_out_of_range(values: dict[str, object]) -> None:
    with pytest.raises(StyleError):
        replace(DEFAULT_STYLE, **values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "values",
    [
        {"hatch_columns": 1, "hatch_rows": 30},
        {"dashes_per_edge": 30},
        {"edge_width": 1.0},
        {"edge_width": 15.0},
        {"vertex_radius": 1.0},
        {"grid_width": 0.0},
        {"grid_width": 5.0},
    ],
)
def test_the_ends_of_the_ranges(values: dict[str, object]) -> None:
    replace(DEFAULT_STYLE, **values)  # type: ignore[arg-type]


class TestFitted:
    def test_too_small_vertices_are_raised_to_the_least(self) -> None:
        from cube_net.ui.style.style import least_vertex_radius

        style = replace(DEFAULT_STYLE, edge_width=4.3, vertex_radius=2.0)
        assert least_vertex_radius(4.3) == 3.1  # 3.01, rounded up to the tenth the fields show
        assert style.fitted().vertex_radius == 3.1

    def test_large_enough_ones_stay(self) -> None:
        assert DEFAULT_STYLE.fitted() is DEFAULT_STYLE
