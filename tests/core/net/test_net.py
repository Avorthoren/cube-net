# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

from cube_net.core.body import Body
from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.net import EdgeKind, RegionSpec, build_net, default_net


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


def test_body_edges_of_half_edges() -> None:
    net = default_net()
    for fold in net.fold_edges():
        edge = net.body_edge_of(fold)
        assert edge is not None and net.segment_faces(fold) == edge.faces
    for cut in net.boundary_edges():
        assert net.body_edge_of(cut) is not None  # the cross is cut along cube edges only
        assert net.body_edge_of(cut.twin) is net.body_edge_of(cut)  # seen from the outside too


def test_a_seam_across_a_face_between_points_of_two_edges(pillow: Body) -> None:
    """In the pillow, face 1 divided along x-y, from its side PQ to its side SP: both ends lie on faces 1 and 2, yet
    the seam isn't on an edge of the body."""
    p, q, r, s = Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(0, 1)
    x, y = Vec(F(1, 2), 0), Vec(0, F(1, 2))
    identity = Rigid90.identity()
    net = build_net(
        pillow,
        [
            RegionSpec(1, identity, [p, x, y]),
            RegionSpec(1, identity, [x, q, r, s, y]),
            RegionSpec(2, identity, [q, Vec(F(3, 2), 0), Vec(2, 0), Vec(2, F(1, 2)), Vec(2, 1), r]),
        ],
    )
    (seam,) = (he for he in net.half_edges if (he.origin.position, he.destination.position) == (x, y))
    assert seam.kind is EdgeKind.SEAM
    assert net.body_edge_of(seam) is None
    assert net.segment_faces(seam) == {1}
    (fold,) = net.fold_edges()
    assert net.segment_faces(fold) == {1, 2}


def test_centroid_of_the_cube_net() -> None:
    """Six unit squares: four in a column x 11..12, y 10..14, and two either side of the one at y 12..13."""
    assert default_net().centroid() == Vec(F(23, 2), F(73, 6))
