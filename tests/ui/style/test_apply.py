# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace

from cube_net.ui import palette
from cube_net.ui.sheet import net_style
from cube_net.ui.style import DEFAULT_STYLE, apply_style


def test_everything_reads_the_new_values() -> None:
    apply_style(
        replace(
            DEFAULT_STYLE,
            edge_width=8.0,
            vertex_radius=12.5,
            hatch_columns=4,
            hatch_rows=3,
            dashes_per_edge=7,
            grid_width=0.0,
            grid_color="#ABCDEF",
            face_colors=("#111111", "#222222", "#333333", "#444444", "#555555", "#666666"),
        )
    )
    assert net_style.EDGE_WIDTH_PX == 8.0
    assert net_style.CUT_HITBOX_PX == 8.0 * net_style.CUT_HITBOX_FACTOR
    assert net_style.HIGHLIGHT_WIDTH_PX == net_style.FOLD_HITBOX_PX == net_style.CUT_HITBOX_PX
    assert net_style.VERTEX_RADIUS_PX == 12.5
    assert (net_style.HATCH_COLUMNS, net_style.HATCH_ROWS, net_style.DASHES_PER_EDGE) == (4, 3, 7)
    assert net_style.GRID_WIDTH_PX == 0.0
    assert palette.GRID.name().upper() == "#ABCDEF"
    assert palette.FACE_COLORS[6].name() == "#666666"


def test_and_back() -> None:
    apply_style(replace(DEFAULT_STYLE, edge_width=8.0))
    apply_style(DEFAULT_STYLE)
    assert DEFAULT_STYLE.edge_width == net_style.EDGE_WIDTH_PX
    assert DEFAULT_STYLE.edge_width * net_style.CUT_HITBOX_FACTOR == net_style.CUT_HITBOX_PX
