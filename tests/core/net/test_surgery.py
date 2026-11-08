from fractions import Fraction as F

import pytest

from cube_net.core.cube import SurfacePoint
from cube_net.core.geometry import Vec
from cube_net.core.net import EdgeKind, HalfEdge, Net, default_net
from cube_net.core.net.surgery import add_edge, corner, new_vertex, outgoing, split_edge


@pytest.fixture
def net() -> Net:
    return default_net()


def edge_between(net: Net, a: Vec, b: Vec) -> HalfEdge:
    return next(he for he in net.half_edges if (he.origin.position, he.destination.position) == (a, b))


def test_split_edge_on_both_sides(net: Net) -> None:
    he = edge_between(net, Vec(11, 13), Vec(12, 13))  # the fold C-D, seen from face 1
    mid = Vec(F(23, 2), 13)
    w = split_edge(net, he, mid, SurfacePoint(1, Vec(F(1, 2), 0)))
    assert he.destination is w and he.next.origin is w and he.next.destination.position == Vec(12, 13)
    assert he.twin.origin is w and he.twin.destination.position == Vec(11, 13)
    assert he.next.twin.destination is w and he.next.twin.origin.position == Vec(12, 13)
    assert he.next.kind is EdgeKind.FOLD and he.next.region is he.region
    assert sorted(o.destination.position for o in outgoing(w)) == [Vec(11, 13), Vec(12, 13)]


def test_outgoing_lists_every_edge_at_a_vertex(net: Net) -> None:
    c1 = next(v for v in net.vertices if v.position == Vec(11, 13))
    assert sorted(he.destination.position for he in outgoing(c1)) == sorted(
        [Vec(11, 14), Vec(10, 13), Vec(11, 12), Vec(12, 13)]
    )


def test_add_edge_dead_end_then_dividing_a_region(net: Net) -> None:
    region = next(r for r in net.regions if r.face == 1)
    a = next(v for v in net.vertices if v.position == Vec(11, 14))
    b = next(v for v in net.vertices if v.position == Vec(12, 13))
    center = new_vertex(net, Vec(F(23, 2), F(27, 2)), SurfacePoint(1, Vec(F(1, 2), F(1, 2))))

    first = add_edge(net, a, center, region, EdgeKind.BOUNDARY)
    assert first.twin.next is corner(a, region) or first.next is first.twin
    assert len(net.regions) == 6  # a dead end doesn't divide anything
    assert len(net.region_cycle(region)) == 6

    second = add_edge(net, center, b, region, EdgeKind.BOUNDARY)
    assert len(net.regions) == 7
    part = second.twin.region
    assert part is not None and part is not second.region and part.face == 1
    assert sorted(len(net.region_cycle(r)) for r in (second.region, part) if r is not None) == [4, 4]


def test_corner_of_a_vertex_not_on_the_region(net: Net) -> None:
    region = next(r for r in net.regions if r.face == 1)
    far = next(v for v in net.vertices if v.position == Vec(11, 10))
    with pytest.raises(ValueError, match="not on the boundary"):
        corner(far, region)
