import pytest

from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.net import EdgeKind, Net, NetInvariantError, default_net, validate_net


@pytest.fixture
def net() -> Net:
    return default_net()


def test_default_net_is_valid(net: Net) -> None:
    validate_net(net)


def test_broken_link(net: Net) -> None:
    net.half_edges[0].next.prev = net.half_edges[5]
    with pytest.raises(NetInvariantError, match="next/prev"):
        validate_net(net)


def test_vertex_moved_away_from_its_placement(net: Net) -> None:
    net.vertices[0].position = Vec(100, 100)
    with pytest.raises(NetInvariantError):
        validate_net(net)


def test_wrong_placement(net: Net) -> None:
    net.regions[0].placement = Rigid90(1, Vec(0, 0))
    with pytest.raises(NetInvariantError, match="placement"):
        validate_net(net)


def test_seam_left_behind(net: Net) -> None:
    fold = net.fold_edges()[0]
    fold.kind = EdgeKind.SEAM
    with pytest.raises(NetInvariantError, match="seam"):
        validate_net(net)


def test_two_perimeter_cycles_are_not_a_finished_net() -> None:
    from fractions import Fraction as F

    from cube_net.core.cutting import CutLine, CutPoint, split_net

    net = default_net()
    top = next(he for he in net.boundary_edges() if he.origin.position == Vec(12, 14))
    right = next(he for he in net.boundary_edges() if he.destination.position == Vec(12, 14))
    line = CutLine([CutPoint(Vec(F(23, 2), 14), top), CutPoint(Vec(12, F(27, 2)), right)])
    split = split_net(net, line)
    with pytest.raises(NetInvariantError, match="perimeter cycles"):
        validate_net(split.net)
