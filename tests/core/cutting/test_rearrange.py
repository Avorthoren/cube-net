from collections.abc import Callable
from fractions import Fraction as F

import pytest

from cube_net.core.cutting import CutLine, CutPoint, SplitNet, rearrange, split_net
from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.net import HalfEdge, Net


def v(x: str, y: str) -> Vec:
    return Vec(F(x), F(y))


@pytest.fixture
def split(net: Net, cut: Callable[[str], HalfEdge]) -> SplitNet:
    """The corner cut of docs/idea.txt: x (11.5, 14), y (11.5, 13.5), z (12, 13.5)."""
    return split_net(
        net,
        CutLine(
            [
                CutPoint(v("11.5", "14"), cut("B_1-A_1")),
                CutPoint(v("11.5", "13.5")),
                CutPoint(v("12", "13.5"), cut("D_1-B_1")),
            ]
        ),
    )


def cut_between(net: Net, a: Vec, b: Vec) -> HalfEdge:
    return next(he for he in net.boundary_edges() if {he.origin.position, he.destination.position} == {a, b})


def test_corner_piece_moves_under_face_5_as_in_idea(split: SplitNet, consistent: Callable[[Net], None]) -> None:
    """docs/idea.txt: gluing x-B to its image at the bottom of face 5 gives x_2, y_2, z_2 below A_3-B_3."""
    result = rearrange(split, cut_between(split.net, v("11.5", "10"), Vec(12, 10)))
    assert result is not None
    consistent(result.net)
    assert result.motion == Rigid90.translation(Vec(0, -4))
    positions = {w.position for w in result.net.vertices}
    assert {v("11.5", "9.5"), v("12", "9.5")} <= positions  # y_2 and z_2
    assert Vec(12, 14) not in positions  # B_1 went along with the piece
    assert (result.kept.origin.position, result.kept.destination.position) == (
        result.moved.destination.position,
        result.moved.origin.position,
    )


def test_the_clicked_half_stays_the_other_moves(split: SplitNet) -> None:
    """Clicking the piece's own x-B instead: the piece stays, the rest of the net moves up by 4."""
    result = rearrange(split, cut_between(split.net, v("11.5", "14"), Vec(12, 14)))
    assert result is not None
    assert result.motion == Rigid90.translation(Vec(0, 4))
    positions = {w.position for w in result.net.vertices}
    assert Vec(12, 14) in positions  # the piece's B_1
    assert Vec(11, 16) in positions  # C_1 moved up
    assert v("11.5", "13.5") in positions  # y stays on the piece


def test_gluing_with_a_rotation_turns_the_hatch_too(split: SplitNet, consistent: Callable[[Net], None]) -> None:
    """z_3-B_2 on top of face 3: the corner piece turns clockwise and lies on face 3's upper side."""
    result = rearrange(split, cut_between(split.net, v("12.5", "13"), Vec(13, 13)))
    assert result is not None
    consistent(result.net)  # includes: every region's placement still maps its corners onto their positions
    assert result.motion.k == 3
    assert result.motion.apply(Vec(12, 14)) == Vec(13, 13)  # B_1 onto B_2
    assert result.motion.apply(v("12", "13.5")) == v("12.5", "13")  # z_1 onto z_3
    assert result.motion.apply(v("11.5", "14")) == v("13", "13.5")  # x
    moved_regions = [r for r in result.net.regions if r.placement.k == 3]
    assert len(moved_regions) == 1 and moved_regions[0].face == 1


def test_counterpart_in_the_same_half_means_no_rearrangement(split: SplitNet) -> None:
    assert rearrange(split, cut_between(split.net, v("10.5", "12") + Vec(F(-1, 2), 0), Vec(11, 12))) is None  # E_2-H_1


def test_the_split_net_itself_does_not_change(split: SplitNet) -> None:
    before = {w: w.position for w in split.net.vertices}
    assert rearrange(split, cut_between(split.net, v("11.5", "10"), Vec(12, 10))) is not None
    assert {w: w.position for w in split.net.vertices} == before


def test_outside_half_edge_rejected(split: SplitNet) -> None:
    outer = cut_between(split.net, v("11.5", "10"), Vec(12, 10)).twin
    with pytest.raises(ValueError, match="inner half-edge"):
        rearrange(split, outer)
