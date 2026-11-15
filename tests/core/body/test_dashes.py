# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.body import CUBE, SurfacePoint, dash_layout
from cube_net.core.geometry import Vec
from cube_net.core.net import default_net

# Face 1's corners (C, D, B, A counter-clockwise from its origin) and points from docs/idea.txt.
C, D, B, A = Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(0, 1)
X = Vec(F(1, 2), 1)  # x: middle of AB
Y = Vec(F(1, 2), F(1, 2))  # y: inside face 1


def test_edge_uses_both_faces_from_its_first_vertex() -> None:
    layout = dash_layout(CUBE, 1, B, A)
    assert layout.faces == (1, 5)
    assert layout.start == SurfacePoint.at_vertex(CUBE, "A") and layout.offset == 0


def test_direction_does_not_matter() -> None:
    assert dash_layout(CUBE, 1, A, B) == dash_layout(CUBE, 1, B, A)


def test_part_of_an_edge_continues_the_edge_pattern() -> None:
    layout = dash_layout(CUBE, 1, X, B)
    assert layout.faces == (1, 5)
    assert layout.start == SurfacePoint(CUBE, 1, X) and layout.offset == 0.5


def test_the_same_edge_from_the_other_face() -> None:
    # In face 5, A is at (0, 0) and B at (1, 0).
    assert dash_layout(CUBE, 5, Vec(1, 0), Vec(F(1, 2), 0)) == dash_layout(CUBE, 1, B, X)


def test_inside_a_face_uses_face_colour_and_white() -> None:
    layout = dash_layout(CUBE, 1, X, Y)
    assert layout.faces == (1, None)
    assert layout.offset == 0
    assert layout.start == dash_layout(CUBE, 1, Y, X).start


def test_counterparts_in_default_net_have_identical_patterns() -> None:
    net = default_net()

    def layout_of(he):  # type: ignore[no-untyped-def]
        assert he.region is not None
        to_local = he.region.placement.inverse()
        a, b = to_local.apply(he.origin.position), to_local.apply(he.destination.position)
        return dash_layout(CUBE, he.region.face, a, b)

    for he in net.boundary_edges():
        assert layout_of(he) == layout_of(net.counterpart(he))


def test_vertex_to_vertex_diagonal_is_inside_face() -> None:
    assert dash_layout(CUBE, 1, A, D).faces == (1, None)


def test_degenerate() -> None:
    with pytest.raises(ValueError, match="degenerate"):
        dash_layout(CUBE, 1, A, A)
