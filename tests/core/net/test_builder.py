# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later


import pytest

from cube_net.core.body import CUBE, FACES, LOCAL_CORNERS, Body, SurfacePoint
from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.net import EdgeKind, NetBuildError, NetInvariantError, RegionSpec, build_net, validate_net
from cube_net.core.net.builder import _turn
from cube_net.core.net.elements import HalfEdge, NetVertex, Region

ID = Rigid90()


def square(face: int, origin: Vec) -> RegionSpec:
    """Unit square of `face`, translated so its local (0,0) is at `origin`."""
    p = Rigid90.translation(origin)
    return RegionSpec(face, p, [p.apply(c) for c in LOCAL_CORNERS])


def default_squares(**moved: Vec) -> list[RegionSpec]:
    """The default net's squares; `moved` overrides origins, e.g. default_squares(f5=Vec(20, 20))."""
    origins = {f: {p.face: p.placement for p in CUBE.start}[f].t for f in FACES}
    for key, origin in moved.items():
        origins[int(key[1:])] = origin
    return [square(f, origins[f]) for f in FACES]


def test_default_squares_build() -> None:
    net = build_net(CUBE, default_squares())
    assert len(net.regions) == 6 and len(net.fold_edges()) == 5


def test_shared_side_inside_a_face_is_seam() -> None:
    """Face 2 cut along its diagonal G-C into two triangles: the diagonal is a SEAM, the cube edges stay FOLDs."""
    specs = [s for s in default_squares() if s.face != 2]
    p = {p.face: p.placement for p in CUBE.start}[2]
    h, g, d, c = (p.apply(corner) for corner in LOCAL_CORNERS)
    specs += [RegionSpec(2, p, [h, g, c]), RegionSpec(2, p, [g, d, c])]
    net = build_net(CUBE, specs)
    inner = [he for he in net.half_edges if he.region is not None and he.twin.region is not None and he.id < he.twin.id]
    assert sorted(he.kind.name for he in inner) == ["FOLD"] * 5 + ["SEAM"]
    assert all(he.kind is EdgeKind.FOLD for he in net.fold_edges())  # fold_edges() never lists seams


def test_too_few_corners() -> None:
    with pytest.raises(NetBuildError, match="needs at least 3 corners"):
        build_net(CUBE, [RegionSpec(1, ID, [Vec(0, 0), Vec(1, 0)])])


def test_clockwise_rejected() -> None:
    with pytest.raises(NetBuildError, match="must be counter-clockwise"):
        build_net(CUBE, [RegionSpec(1, ID, [Vec(0, 0), Vec(0, 1), Vec(1, 1), Vec(1, 0)])])


def test_different_points_at_one_position_are_different_vertices() -> None:
    """Face 1 at the origin and face 2 right next to it: sheet point (1, 0) is D (face 1) and H (face 2), two vertices
    (and the sides between them aren't shared: this is no net)."""
    with pytest.raises(NetInvariantError, match="no counterpart"):
        build_net(CUBE, [square(1, Vec(0, 0)), square(2, Vec(1, 0))])


def test_overlapping_regions_rejected() -> None:
    with pytest.raises(NetBuildError, match="regions overlap along"):
        build_net(CUBE, [square(2, Vec(0, 0)), square(2, Vec(0, 0))])


def test_parts_touching_at_a_point(pillow: Body) -> None:
    """The pillow's two faces, apart, meeting only at R: one vertex, which the perimeter passes twice."""
    specs = [
        RegionSpec(1, ID, [Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(0, 1)]),
        RegionSpec(2, Rigid90(1, Vec(2, 0)), [Vec(2, 1), Vec(2, 2), Vec(1, 2), Vec(1, 1)]),
    ]
    net = build_net(pillow, specs)
    validate_net(net)
    (r,) = [v for v in net.vertices if v.position == Vec(1, 1)]
    assert [he.origin for he in net.perimeter()].count(r) == 2
    assert net.fold_edges() == []


def test_disconnected_rejected() -> None:
    with pytest.raises(NetBuildError, match="must be a single cycle"):
        build_net(CUBE, default_squares(f5=Vec(20, 20)))


def test_incomplete_net_rejected() -> None:
    """A single face is not a cube net: its cuts have no counterparts."""
    with pytest.raises(NetInvariantError, match="has no counterpart"):
        build_net(CUBE, [square(2, Vec(0, 0))])


def test_at_a_slits_tip_the_perimeter_goes_back() -> None:
    """The tip T of a slit, its two sides of different lengths (one goes on to R, the other only to U): arriving at T
    up the slit, the perimeter goes back down it, not along a fold or round the other side."""

    def vertex(i: int, x: int, y: int) -> NetVertex:
        return NetVertex(i, Vec(x, y), SurfacePoint(CUBE, 1, Vec(0, 0)))

    t, r, u, fold_end = vertex(0, 1, 1), vertex(1, 1, 3), vertex(2, 1, 2), vertex(3, 1, 0)
    left, right = Region(0, 1, ID), Region(1, 2, ID)
    side_up = HalfEdge(0, t, EdgeKind.BOUNDARY, left)  # T -> R, the net on its left
    arriving = HalfEdge(1, r, EdgeKind.BOUNDARY, None)  # R -> T, on the perimeter
    side_up.twin, arriving.twin = arriving, side_up
    down_slit = HalfEdge(2, t, EdgeKind.BOUNDARY, None)  # T -> U: the other side's way out, on the perimeter
    other_side = HalfEdge(3, u, EdgeKind.BOUNDARY, right)
    down_slit.twin, other_side.twin = other_side, down_slit
    fold = HalfEdge(4, t, EdgeKind.FOLD, right)
    fold.twin = HalfEdge(5, fold_end, EdgeKind.FOLD, left)
    assert _turn(arriving, [side_up, down_slit, fold]) is down_slit
