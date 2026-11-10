# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.cube import CUBE, FACES, LOCAL_CORNERS
from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.net import EdgeKind, NetBuildError, NetInvariantError, RegionSpec, build_net

ID = Rigid90()


def square(face: int, origin: Vec) -> RegionSpec:
    """Unit square of `face`, translated so its local (0,0) is at `origin`."""
    p = Rigid90.translation(origin)
    return RegionSpec(face, p, [p.apply(c) for c in LOCAL_CORNERS])


def default_squares(**moved: Vec) -> list[RegionSpec]:
    """The default net's squares; `moved` overrides origins, e.g. default_squares(f5=Vec(20, 20))."""
    origins = {f: CUBE.default_placement(f).t for f in FACES}
    for key, origin in moved.items():
        origins[int(key[1:])] = origin
    return [square(f, origins[f]) for f in FACES]


def test_default_squares_build() -> None:
    net = build_net(default_squares())
    assert len(net.regions) == 6 and len(net.fold_edges()) == 5


def test_shared_side_inside_a_face_is_seam() -> None:
    """Face 2 cut along its diagonal G-C into two triangles: the diagonal is a SEAM, the cube edges stay FOLDs."""
    specs = [s for s in default_squares() if s.face != 2]
    p = CUBE.default_placement(2)
    h, g, d, c = (p.apply(corner) for corner in LOCAL_CORNERS)
    specs += [RegionSpec(2, p, [h, g, c]), RegionSpec(2, p, [g, d, c])]
    net = build_net(specs)
    inner = [he for he in net.half_edges if he.region is not None and he.twin.region is not None and he.id < he.twin.id]
    assert sorted(he.kind.name for he in inner) == ["FOLD"] * 5 + ["SEAM"]
    assert all(he.kind is EdgeKind.FOLD for he in net.fold_edges())  # fold_edges() never lists seams


def test_too_few_corners() -> None:
    with pytest.raises(NetBuildError, match="needs at least 3 corners"):
        build_net([RegionSpec(1, ID, [Vec(0, 0), Vec(1, 0)])])


def test_clockwise_rejected() -> None:
    with pytest.raises(NetBuildError, match="must be counter-clockwise"):
        build_net([RegionSpec(1, ID, [Vec(0, 0), Vec(0, 1), Vec(1, 1), Vec(1, 0)])])


def test_disagreeing_regions_rejected() -> None:
    """Face 1 at the origin and face 2 right next to it: sheet point (1, 0) would be D (face 1) and H (face 2)."""
    with pytest.raises(NetBuildError, match="regions disagree at Vec"):
        build_net([square(1, Vec(0, 0)), square(2, Vec(1, 0))])


def test_overlapping_regions_rejected() -> None:
    with pytest.raises(NetBuildError, match="regions overlap along"):
        build_net([square(2, Vec(0, 0)), square(2, Vec(0, 0))])


def test_touching_parts_not_supported() -> None:
    """Two diagonal quarters of face 2 touch only at its center."""
    q = F(1, 2)
    specs = [
        RegionSpec(2, ID, [Vec(0, 0), Vec(q, 0), Vec(q, q), Vec(0, q)]),
        RegionSpec(2, ID, [Vec(q, q), Vec(1, q), Vec(1, 1), Vec(q, 1)]),
    ]
    with pytest.raises(NetBuildError, match="two perimeter segments start at Vec"):
        build_net(specs)


def test_disconnected_rejected() -> None:
    with pytest.raises(NetBuildError, match="must be a single cycle"):
        build_net(default_squares(f5=Vec(20, 20)))


def test_incomplete_net_rejected() -> None:
    """A single face is not a cube net: its cuts have no counterparts."""
    with pytest.raises(NetInvariantError, match="has no counterpart"):
        build_net([square(2, Vec(0, 0))])
