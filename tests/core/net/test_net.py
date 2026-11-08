from cube_net.core.geometry import Vec
from cube_net.core.net import default_net


def test_copy_is_independent_and_maps_elements() -> None:
    net = default_net()
    copy = net.copy()
    assert copy.net is not net
    he = net.half_edges[0]
    new = copy.edges[he]
    assert new is not he and new.id == he.id and new.next is copy.edges[he.next] and new.twin is copy.edges[he.twin]
    vertex = net.vertices[0]
    copy.vertices[vertex].position = Vec(0, 0)
    assert vertex.position != Vec(0, 0)
    region = net.regions[0]
    assert copy.regions[region].edge is copy.edges[region.edge]


def test_one_perimeter_cycle() -> None:
    net = default_net()
    cycles = net.perimeters()
    assert len(cycles) == 1 and len(cycles[0]) == 14
    assert net.perimeter() == cycles[0]
    assert len(net.boundary_vertices()) == 14
