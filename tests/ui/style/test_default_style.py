# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace

from cube_net.ui import palette
from cube_net.ui.sheet import net_style
from cube_net.ui.style import DEFAULT_STYLE, fitted


def test_the_defaults_are_what_the_style_files_say() -> None:
    assert DEFAULT_STYLE.edge_width == net_style.EDGE_WIDTH_PX
    assert DEFAULT_STYLE.vertex_radius == net_style.VERTEX_RADIUS_PX
    assert (DEFAULT_STYLE.hatch_columns, DEFAULT_STYLE.hatch_rows) == (net_style.HATCH_COLUMNS, net_style.HATCH_ROWS)
    assert DEFAULT_STYLE.dashes_per_unit == net_style.DASHES_PER_UNIT
    assert DEFAULT_STYLE.grid_color == palette.GRID.name().upper()


class TestFitted:
    def test_too_small_vertices_are_raised_to_the_least(self) -> None:
        from cube_net.ui.style.default_style import least_vertex_radius

        style = replace(DEFAULT_STYLE, edge_width=4.3, vertex_radius=2.0)
        assert least_vertex_radius(4.3) == 3.1  # 3.01, rounded up to the tenth the fields show
        assert fitted(style).vertex_radius == 3.1

    def test_large_enough_ones_stay(self) -> None:
        assert fitted(DEFAULT_STYLE) is DEFAULT_STYLE
