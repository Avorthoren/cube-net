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
