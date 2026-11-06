"""The default net must match docs/idea.txt exactly."""

from collections import Counter

import pytest

from cube_net.core.cube import FACES, SurfacePoint
from cube_net.core.geometry import Box, Rigid90, Vec, signed_area
from cube_net.core.net import EdgeKind, Net, default_net


@pytest.fixture
def net() -> Net:
    return default_net()


def label(point: SurfacePoint) -> str:
    return point.vertex or "?"


def test_counts(net: Net) -> None:
    assert len(net.regions) == 6
    assert len(net.vertices) == 14
    assert len(net.fold_edges()) == 5
    assert len(net.boundary_edges()) == 14
    assert len(net.perimeter()) == 14
    assert len(net.half_edges) == 2 * (5 + 14)


def test_regions_are_unit_squares_of_their_faces(net: Net) -> None:
    assert sorted(r.face for r in net.regions) == list(FACES)
    for region in net.regions:
        polygon = net.region_polygon(region)
        assert signed_area(polygon) == 1  # counter-clockwise unit square
        assert region.placement.k == 0
        for he in net.region_cycle(region):
            assert region.face in he.origin.point.faces
            assert region.placement.apply(he.origin.point.local_in(region.face)) == he.origin.position


def test_total_area_is_six(net: Net) -> None:
    assert sum(signed_area(net.region_polygon(r)) for r in net.regions) == 6


def test_vertex_images(net: Net) -> None:
    """14 images of 8 vertices: A, B 3 times; E, F twice; C, D, G, H once (docs/idea.txt)."""
    counts = Counter(label(v.point) for v in net.vertices)
    assert counts == {"A": 3, "B": 3, "E": 2, "F": 2, "C": 1, "D": 1, "G": 1, "H": 1}
    assert {v.position for v in net.images(SurfacePoint.at_vertex("A"))} == {Vec(11, 14), Vec(10, 13), Vec(11, 10)}
    assert all(v.point.vertex is not None for v in net.boundary_vertices())


def test_folds(net: Net) -> None:
    folds = {"".join(sorted(label(he.origin.point) + label(he.destination.point))) for he in net.fold_edges()}
    assert folds == {"CD", "CH", "DG", "GH", "EF"}
    assert all(he.kind is EdgeKind.FOLD for he in net.fold_edges())


def test_cuts_and_counterparts(net: Net) -> None:
    cuts = Counter("".join(sorted(label(he.origin.point) + label(he.destination.point))) for he in net.boundary_edges())
    assert cuts == {name: 2 for name in ("AC", "BD", "EH", "FG", "AE", "BF", "AB")}
    for he in net.boundary_edges():
        other = net.counterpart(he)
        assert other is not he
        assert net.counterpart(other) is he
        assert (other.origin.point, other.destination.point) == (he.destination.point, he.origin.point)


def test_counterpart_glue_is_a_rigid_90_motion(net: Net) -> None:
    for he in net.boundary_edges():
        other = net.counterpart(he)
        # Gluing maps other's ends onto he's ends (same cube points): always a rotation by k*90 plus a translation.
        Rigid90.from_segments(
            other.destination.position, other.origin.position, he.origin.position, he.destination.position
        )


def test_perimeter_is_clockwise_cycle_of_outside_half_edges(net: Net) -> None:
    perimeter = net.perimeter()
    assert all(he.is_outside for he in perimeter)
    assert all(perimeter[i].destination is perimeter[(i + 1) % 14].origin for i in range(14))
    assert signed_area([he.origin.position for he in perimeter]) == -6


def test_contains(net: Net) -> None:
    assert net.contains(Vec(11, 12))  # H_1
    assert net.contains(Vec(10, 12))  # E_2 on the perimeter
    assert not net.contains(Vec(10, 11))  # left of face 6
    assert not net.contains(Vec(12, 14) + Vec(1, 0))


def test_bounding_box(net: Net) -> None:
    assert net.bounding_box() == Box(Vec(10, 10), Vec(13, 14))
