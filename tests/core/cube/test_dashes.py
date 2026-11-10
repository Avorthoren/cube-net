# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.cube import DASH_LENGTH, SurfacePoint, dash_layout
from cube_net.core.geometry import Vec
from cube_net.core.net import default_net

A, B, D = (SurfacePoint.at_vertex(v) for v in "ABD")
X = SurfacePoint(1, Vec(F(1, 2), 1))  # x from docs/idea.txt: middle of AB
Y = SurfacePoint(1, Vec(F(1, 2), F(1, 2)))  # y: inside face 1


def test_ten_dashes_of_each_colour_per_cube_edge() -> None:
    assert 1 / DASH_LENGTH == 20


def test_cube_edge_uses_both_faces_from_first_vertex() -> None:
    layout = dash_layout(B, A)
    assert layout.faces == (1, 5)
    assert layout.start == A and layout.offset == 0


def test_direction_does_not_matter() -> None:
    assert dash_layout(A, B) == dash_layout(B, A)


def test_part_of_an_edge_continues_the_edge_pattern() -> None:
    layout = dash_layout(X, B)
    assert layout.faces == (1, 5)
    assert layout.start == X and layout.offset == F(1, 2)


def test_inside_a_face_uses_face_colour_and_white() -> None:
    layout = dash_layout(X, Y)
    assert layout.faces == (1, None)
    assert layout.offset == 0
    assert layout.start == dash_layout(Y, X).start


def test_counterparts_in_default_net_have_identical_patterns() -> None:
    net = default_net()
    for he in net.boundary_edges():
        other = net.counterpart(he)
        assert dash_layout(he.origin.point, he.destination.point) == dash_layout(
            other.origin.point, other.destination.point
        )


def test_vertex_to_vertex_diagonal_is_inside_face() -> None:
    assert dash_layout(A, D).faces == (1, None)


def test_errors() -> None:
    with pytest.raises(ValueError, match="degenerate"):
        dash_layout(A, A)
    with pytest.raises(ValueError, match="single face"):
        dash_layout(A, SurfacePoint.at_vertex("G"))
