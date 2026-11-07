from fractions import Fraction as F

import pytest

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
