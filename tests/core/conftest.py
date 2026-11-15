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


def flat_body(faces: dict[int, list[tuple[int, int, str]]]) -> Body:
    """A body given by its starting net: every face's corners on the sheet as (x, y, name), counter-clockwise, all
    placed by the identity (so each face's frame is the sheet's)."""
    return Body(
        {
            n: (tuple(Vec(x, y) for x, y, _ in corners), tuple(name for *_, name in corners))
            for n, corners in faces.items()
        },
        [(n, IDENTITY) for n in faces],
    )


@pytest.fixture
def long_box() -> Body:
    """A 1x1x2 box: the 4 long sides in a row, the bottom below the front, the top above it."""
    return flat_body(
        {
            1: [(0, 0, "A"), (1, 0, "B"), (1, 2, "F"), (0, 2, "E")],
            2: [(1, 0, "B"), (2, 0, "C"), (2, 2, "G"), (1, 2, "F")],
            3: [(2, 0, "C"), (3, 0, "D"), (3, 2, "H"), (2, 2, "G")],
            4: [(3, 0, "D"), (4, 0, "A"), (4, 2, "E"), (3, 2, "H")],
            5: [(0, -1, "D"), (1, -1, "C"), (1, 0, "B"), (0, 0, "A")],
            6: [(0, 2, "E"), (1, 2, "F"), (1, 3, "G"), (0, 3, "H")],
        }
    )


@pytest.fixture
def l_prism() -> Body:
    """3 unit cubes in an L, 1 high: L-shaped bottom (face 1, with a reflex corner) and top (face 2), 6 sides; the
    two sides at the inner corner (5 and 6) hang off side 4."""
    return flat_body(
        {
            1: [(0, 0, "P0"), (2, 0, "P1"), (2, 1, "P2"), (1, 1, "P3"), (1, 2, "P4"), (0, 2, "P5")],
            2: [(0, -3, "T5"), (1, -3, "T4"), (1, -2, "T3"), (2, -2, "T2"), (2, -1, "T1"), (0, -1, "T0")],
            3: [(0, -1, "T0"), (2, -1, "T1"), (2, 0, "P1"), (0, 0, "P0")],
            4: [(2, 0, "P1"), (3, 0, "T1"), (3, 1, "T2"), (2, 1, "P2")],
            5: [(2, 1, "P2"), (3, 1, "T2"), (3, 2, "T3"), (2, 2, "P3")],
            6: [(2, 2, "P3"), (3, 2, "T3"), (3, 3, "T4"), (2, 3, "P4")],
            7: [(0, 2, "P5"), (1, 2, "P4"), (1, 3, "T4"), (0, 3, "T5")],
            8: [(-1, 0, "T0"), (0, 0, "P0"), (0, 2, "P5"), (-1, 2, "T5")],
        }
    )


@pytest.fixture
def pinwheel_box() -> Body:
    """A 2x2x1 box whose top is cut into 4 quarters around its centre M, each attached to a different side: M is a
    vertex of 4 faces, with 4 images in the starting net."""
    return flat_body(
        {
            1: [(0, 0, "P"), (2, 0, "Q"), (2, 2, "R"), (0, 2, "T")],
            2: [(0, -1, "A"), (1, -1, "S"), (2, -1, "B"), (2, 0, "Q"), (0, 0, "P")],
            3: [(2, 0, "Q"), (3, 0, "B"), (3, 1, "E"), (3, 2, "C"), (2, 2, "R")],
            4: [(0, 2, "T"), (2, 2, "R"), (2, 3, "C"), (1, 3, "N"), (0, 3, "D")],
            5: [(-1, 0, "A"), (0, 0, "P"), (0, 2, "T"), (-1, 2, "D"), (-1, 1, "W")],
            6: [(1, -2, "M"), (2, -2, "E"), (2, -1, "B"), (1, -1, "S")],
            7: [(3, 1, "E"), (4, 1, "M"), (4, 2, "N"), (3, 2, "C")],
            8: [(0, 3, "D"), (1, 3, "N"), (1, 4, "M"), (0, 4, "W")],
            9: [(-2, 0, "S"), (-1, 0, "A"), (-1, 1, "W"), (-2, 1, "M")],
        }
    )
