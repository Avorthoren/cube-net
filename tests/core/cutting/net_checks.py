"""A structural consistency check for nets, shared by the tests in this folder."""

from fractions import Fraction as F

from cube_net.core.geometry import signed_area
from cube_net.core.net import Net


def assert_consistent(net: Net) -> None:
    """Everything that must hold for any net, split or not: the links, the areas, and where the regions are."""
    for he in net.half_edges:
        assert he.next.prev is he and he.prev.next is he
        assert he.twin.twin is he and he.twin is not he
        assert he.next.origin is he.twin.origin, f"{he} doesn't lead to {he.next}"
        assert he.next.region is he.region
        assert he.origin.position != he.destination.position
    for v in net.vertices:
        assert v.edge.origin is v
    for he in net.half_edges:
        assert he.origin in net.vertices
    total = F(0)
    for region in net.regions:
        assert region.edge.region is region
        polygon = net.region_polygon(region)
        assert signed_area(polygon) > 0, f"{region} isn't counter-clockwise"
        total += signed_area(polygon)
        for he in net.region_cycle(region):
            assert region.face in he.origin.point.faces
            assert region.placement.apply(he.origin.point.local_in(region.face)) == he.origin.position
    assert total == 6
    assert {he for cycle in net.perimeters() for he in cycle} == {he for he in net.half_edges if he.region is None}
    net.reindex()  # every cut has exactly two images
    for he in net.boundary_edges():
        other = net.counterpart(he)
        assert net.counterpart(other) is he
        d1, d2 = he.destination.position - he.origin.position, other.destination.position - other.origin.position
        assert d1.length_squared() == d2.length_squared()
