# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fixtures for all core tests: bodies other than the cube (docs/template_plan.md, §2.1)."""

import pytest

from cube_net.core.body import Body
from cube_net.core.geometry import Rigid90, Vec

IDENTITY = Rigid90.identity()


@pytest.fixture
def pillow() -> Body:
    """Two unit squares glued along all 4 sides: faces 1 and 2 share the edges PQ, QR, RS and SP. Its template:
    P_1 (0,0), Q_1 (1,0), P_2 (2,0), S_2 (2,1), R_1 (1,1), S_1 (0,1), with the fold Q_1-R_1."""
    return Body(
        {
            1: ((Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(0, 1)), ("P", "Q", "R", "S")),
            2: ((Vec(1, 0), Vec(2, 0), Vec(2, 1), Vec(1, 1)), ("Q", "P", "S", "R")),
        },
        [(1, IDENTITY), (2, IDENTITY)],
    )


@pytest.fixture
def flat_pillow() -> Body:
    """The pillow's template without its fold: one face glued to itself along 3 pairs of its sides."""
    corners = (Vec(0, 0), Vec(1, 0), Vec(2, 0), Vec(2, 1), Vec(1, 1), Vec(0, 1))
    return Body({1: (corners, ("P", "Q", "P", "S", "R", "S"))}, [(1, IDENTITY)])
