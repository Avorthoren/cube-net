# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import itertools
from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.cutting import pieces, region_at, surface_point_at
from cube_net.core.geometry import Vec
from cube_net.core.net import Net


def test_split_at_folds_with_faces(net: Net) -> None:
    ps = pieces(net, Vec(F(23, 2), 14), Vec(F(23, 2), F(23, 2)))  # down through faces 1, 2, 6
    assert [(p.start, p.end) for p in ps] == [
        (Vec(F(23, 2), 14), Vec(F(23, 2), 13)),
        (Vec(F(23, 2), 13), Vec(F(23, 2), 12)),
        (Vec(F(23, 2), 12), Vec(F(23, 2), F(23, 2))),
    ]
    assert [sorted(p.start_point.faces & p.end_point.faces) for p in ps] == [[1], [2], [6]]


def test_segment_along_a_fold_has_both_faces(net: Net) -> None:
    (piece,) = pieces(net, Vec(11, F(25, 2)), Vec(11, F(51, 4)))  # on fold C-H
    assert piece.start_point.faces & piece.end_point.faces == {2, 4}


def test_surface_point_at(net: Net) -> None:
    assert surface_point_at(net, Vec(11, 14)).vertex == "A"
    assert surface_point_at(net, Vec(F(23, 2), F(27, 2))).faces == {1}
    with pytest.raises(ValueError, match="not on the net"):
        surface_point_at(net, Vec(0, 0))
    assert region_at(net, Vec(0, 0)) is None


def test_leaving_the_net_is_an_error(net: Net) -> None:
    with pytest.raises(ValueError, match="leaves the net"):
        pieces(net, Vec(F(21, 2), F(25, 2)), Vec(F(21, 2), F(21, 2)))


def test_crossings_from_c1_into_face_6(net: Net) -> None:
    """The user's example: from C_1 to a point inside face 6 crosses the cube edge H_1-G_1."""
    from cube_net.core.cutting import crossings

    (crossing,) = crossings(net, [Vec(11, 13), Vec(F(23, 2), F(23, 2))])
    assert crossing == Vec(F(34, 3), 12)
    assert surface_point_at(net, crossing).faces == {2, 6}


def test_crossings_in_order_and_without_the_line_s_own_points(net: Net) -> None:
    from cube_net.core.cutting import crossings

    # Down through faces 1, 2, 6; the second point is exactly on the fold G-H, so it is not a crossing.
    line = [Vec(F(23, 2), 14), Vec(F(23, 2), 12), Vec(F(23, 2), F(21, 2))]
    assert crossings(net, line) == [Vec(F(23, 2), 13), Vec(F(23, 2), 11)]
    assert crossings(net, [Vec(F(23, 2), F(27, 2)), Vec(F(47, 4), F(53, 4))]) == []  # inside one face


column_x = st.fractions(F(1101, 100), F(1199, 100))


@given(column_x, st.fractions(F(1301, 100), F(1399, 100)), column_x, st.fractions(F(1001, 100), F(1099, 100)))
def test_every_piece_between_vertices_stays_in_one_face(x1: F, y1: F, x2: F, y2: F) -> None:
    """The user's rule: after splitting at crossings, no piece has points strictly inside two different faces."""
    from cube_net.core.cube import SurfacePointKind
    from cube_net.core.cutting import crossings
    from cube_net.core.net import default_net

    net = default_net()
    line = [Vec(x1, y1), Vec(x2, y2)]  # from face 1 down to face 5, across faces 2 and 6 (the column x in [11, 12])
    stops = [line[0], *crossings(net, line), line[1]]
    assert len(stops) == 5  # three cube edges crossed
    for a, b in itertools.pairwise(stops):
        mid = surface_point_at(net, (a + b) / 2)
        assert mid.kind in (SurfacePointKind.FACE, SurfacePointKind.EDGE)
        for p in (a, b):
            assert mid.faces <= surface_point_at(net, p).faces  # both ends lie on the piece's face


def test_zero_length_segment_has_no_pieces(net: Net) -> None:
    assert pieces(net, Vec(11, 12), Vec(11, 12)) == []
