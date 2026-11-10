# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from cube_net.core.cube import CUBE, FACES, LOCAL_CORNERS
from cube_net.core.geometry import Box, Vec
from cube_net.core.sheet import SHEET_MARGIN, sheet_box


def test_margin_is_five_units() -> None:
    assert SHEET_MARGIN == 5


def test_default_net_sheet() -> None:
    """The default cross spans [10, 13] x [10, 14], so the sheet is [5, 18] x [5, 19]."""
    corners = [CUBE.default_placement(f).apply(c) for f in FACES for c in LOCAL_CORNERS]
    assert sheet_box(corners) == Box(Vec(5, 5), Vec(18, 19))
