from fractions import Fraction as F

import pytest

from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import HalfEdge, Net, boundary_edge_at, default_net

HITBOX = F(1, 20)


@pytest.fixture
def net() -> Net:
    return default_net()


def name(net: Net, he: HalfEdge | None) -> str | None:
    """E.g. "A_2-E_2" for the cut from A_2 to E_2 (labels as in docs/idea.txt)."""
    if he is None:
        return None
    labels = vertex_labels(net, PointLabels())
    return f"{labels[he.origin]}-{labels[he.destination]}"


@pytest.mark.parametrize(
    ("p", "expected"),
    [
        (Vec(F(1002, 100), F(25, 2)), "A_2-E_2"),  # just inside face 4, next to its left side
        (Vec(F(1004, 100), F(25, 2)), "A_2-E_2"),
        (Vec(F(998, 100), F(25, 2)), None),  # just outside the net
        (Vec(F(1006, 100), F(25, 2)), None),  # inside, but farther than the hitbox
        (Vec(F(23, 2), F(25, 2)), None),  # middle of face 2: no cut near
        (Vec(F(23, 2), F(1302, 100)), None),  # next to C_1 - D_1, which is a fold, not a cut
        (Vec(F(1104, 100), F(1397, 100)), "B_1-A_1"),  # near corner A_1: the closer cut wins (0.03 vs 0.04)
        (Vec(F(1105, 100), F(1398, 100)), "B_1-A_1"),
        (Vec(F(1101, 100), F(1395, 100)), "A_1-C_1"),  # 0.01 from the left side, 0.05 from the top
    ],
)
def test_hits(net: Net, p: Vec, expected: str | None) -> None:
    assert name(net, boundary_edge_at(net, p, HITBOX)) == expected


def test_on_the_cut_itself_counts(net: Net) -> None:
    assert name(net, boundary_edge_at(net, Vec(10, F(25, 2)), HITBOX)) == "A_2-E_2"


def test_beyond_the_ends_of_a_cut_does_not_count(net: Net) -> None:
    # Left of face 6 there is no net; the cut E_1 - H_1 (x = 11, y in [11, 12]) is not reached from y = 12.5.
    assert boundary_edge_at(net, Vec(F(1102, 100), F(125, 10)), HITBOX) is None


def test_tie_is_deterministic(net: Net) -> None:
    corner = Vec(F(1102, 100), F(1398, 100))  # exactly as far from B_1-A_1 as from A_1-C_1
    first = boundary_edge_at(net, corner, HITBOX)
    assert first is not None
    assert boundary_edge_at(net, corner, HITBOX) is first
    assert first.id == min(he.id for he in net.boundary_edges() if name(net, he) in ("B_1-A_1", "A_1-C_1"))


def test_vertex_at(net: Net) -> None:
    from cube_net.core.net import boundary_vertex_at

    radius = F(1, 10)
    a1 = boundary_vertex_at(net, Vec(F(1105, 100), F(1395, 100)), radius)  # 0.07 from A_1 = (11, 14)
    assert a1 is not None and a1.position == Vec(11, 14)
    assert boundary_vertex_at(net, Vec(F(1095, 100), F(1405, 100)), radius) is a1  # outside the net, still the circle
    assert boundary_vertex_at(net, Vec(F(1115, 100), 14), radius) is None  # 0.15 away
    assert boundary_vertex_at(net, Vec(F(23, 2), F(25, 2)), radius) is None


def test_edge_from_vertex(net: Net) -> None:
    from cube_net.core.net import boundary_edge_from, boundary_vertex_at

    c1 = boundary_vertex_at(net, Vec(11, 13), F(1, 100))
    assert c1 is not None
    he = boundary_edge_from(net, c1)
    assert he.origin is c1 and he.twin.region is None


class TestFoldEdgeAt:
    half_width = F(1, 20)

    def names(self, net: Net, he: HalfEdge | None) -> set[Vec] | None:
        return None if he is None else {he.origin.position, he.destination.position}

    def test_strip_on_both_sides_of_the_fold(self, net: Net) -> None:
        from cube_net.core.net import fold_edge_at

        ch = {Vec(11, 13), Vec(11, 12)}  # the fold C_1-H_1 between faces 4 and 2
        for x in (F(1097, 100), 11, F(1103, 100)):
            assert self.names(net, fold_edge_at(net, Vec(x, F(25, 2)), self.half_width)) == ch

    def test_outside_the_strip_and_beyond_the_ends(self, net: Net) -> None:
        from cube_net.core.net import fold_edge_at

        assert fold_edge_at(net, Vec(F(1107, 100), F(25, 2)), self.half_width) is None  # too far to the side
        assert fold_edge_at(net, Vec(F(1097, 100), 11), self.half_width) is None  # past E_1, along the fold E_1-F_1
        assert fold_edge_at(net, Vec(10, F(25, 2)), self.half_width) is None  # A_2-E_2 is a cut, not a fold

    def test_closest_wins_but_preferred_stays(self, net: Net) -> None:
        from cube_net.core.net import fold_edge_at

        near_corner = Vec(F(1102, 100), F(1201, 100))  # near H_1: 0.02 from C_1-H_1, 0.01 from H_1-G_1
        closest = fold_edge_at(net, near_corner, self.half_width)
        assert self.names(net, closest) == {Vec(11, 12), Vec(12, 12)}
        other = fold_edge_at(net, Vec(11, F(25, 2)), self.half_width)
        assert other is not None
        assert fold_edge_at(net, near_corner, self.half_width, prefer=other) is other
        assert fold_edge_at(net, Vec(F(23, 2), F(25, 2)), self.half_width, prefer=other) is None  # left its hitbox
