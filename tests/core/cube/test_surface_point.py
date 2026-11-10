# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cube_net.core.cube import CUBE, FACES, VERTICES
from cube_net.core.cube.surface_point import SurfacePoint, SurfacePointKind
from cube_net.core.geometry import Vec

inner = st.fractions(min_value=0, max_value=1, max_denominator=1000).filter(lambda t: 0 < t < 1)
unit = st.fractions(min_value=0, max_value=1, max_denominator=1000)
edges = st.sampled_from(sorted(CUBE.edges, key=sorted))


def point_on_edge(face: int, edge: frozenset[str], t: F) -> Vec:
    """Local point of `face` at parameter t from the alphabetically first vertex of `edge` to the second."""
    a, b = sorted(edge)
    pa, pb = CUBE.corner_local(face, a), CUBE.corner_local(face, b)
    return pa + (pb - pa) * t


class TestConstruction:
    def test_inside_face(self) -> None:
        p = SurfacePoint(3, Vec(F(1, 3), F(1, 2)))
        assert (p.face, p.local) == (3, Vec(F(1, 3), F(1, 2)))
        assert p.faces == {3}
        assert p.kind is SurfacePointKind.FACE
        assert p.vertex is None and p.edge is None

    def test_on_edge_canonical_is_lower_face(self) -> None:
        # Point on edge EF (faces 5 and 6), created from face 6: stored in face 5's frame.
        p = SurfacePoint(6, Vec(F(1, 2), 0))
        assert (p.face, p.local) == (5, Vec(F(1, 2), 1))
        assert p.faces == {5, 6}
        assert p.edge == frozenset("EF")
        assert p.kind is SurfacePointKind.EDGE

    def test_vertex(self) -> None:
        p = SurfacePoint(4, Vec(1, 1))  # corner C of face 4
        assert p == SurfacePoint.at_vertex("C")
        assert (p.face, p.local) == (1, Vec(0, 0))
        assert p.vertex == "C"
        assert p.faces == {1, 2, 4}
        assert p.kind is SurfacePointKind.VERTEX

    @pytest.mark.parametrize("local", [Vec(-1, 0), Vec(0, F(1001, 1000)), Vec(2, 2)])
    def test_outside_unit_square_rejected(self, local: Vec) -> None:
        with pytest.raises(ValueError, match="outside"):
            SurfacePoint(1, local)

    @pytest.mark.parametrize("face", [0, 7, -1])
    def test_bad_face_rejected(self, face: int) -> None:
        with pytest.raises(ValueError, match="no such face"):
            SurfacePoint(face, Vec(0, 0))

    def test_immutable(self) -> None:
        p = SurfacePoint(1, Vec(0, 0))
        with pytest.raises(AttributeError):
            p.face = 2  # type: ignore[misc]

    def test_repr(self) -> None:
        assert repr(SurfacePoint.at_vertex("A")) == "SurfacePoint(1, Vec(0, 1) A)"
        assert repr(SurfacePoint(6, Vec(F(1, 2), 0))) == "SurfacePoint(5, Vec(1/2, 1) on EF)"
        assert repr(SurfacePoint(3, Vec(F(1, 2), F(1, 2)))) == "SurfacePoint(3, Vec(1/2, 1/2))"


class TestIdeaExample:
    """The corner-cut example from docs/idea.txt: x on AB, y inside face 1, z on BD."""

    def test_x_is_the_same_point_from_faces_1_and_5(self) -> None:
        x_from_1 = SurfacePoint(1, Vec(F(1, 2), 1))  # x_1: middle of A_1 - B_1
        x_from_5 = SurfacePoint(5, Vec(F(1, 2), 0))  # x_2: middle of A_3 - B_3
        assert x_from_1 == x_from_5
        assert hash(x_from_1) == hash(x_from_5)
        assert x_from_1.faces == {1, 5}

    def test_colours(self) -> None:
        y = SurfacePoint(1, Vec(F(1, 2), F(1, 2)))
        z_from_1 = SurfacePoint(1, Vec(1, F(1, 2)))  # z_1 on B_1 - D_1
        z_from_3 = SurfacePoint(3, Vec(F(1, 2), 1))  # z_3 on D_1 - B_2
        assert y.faces == {1}
        assert z_from_1 == z_from_3
        assert z_from_1.faces == {1, 3}


class TestCanonicalForm:
    @pytest.mark.parametrize("vertex", VERTICES)
    def test_vertex_same_from_all_three_faces(self, vertex: str) -> None:
        points = {SurfacePoint(f, CUBE.corner_local(f, vertex)) for f in CUBE.vertex_faces(vertex)}
        assert points == {SurfacePoint.at_vertex(vertex)}

    def test_all_vertices_distinct(self) -> None:
        assert len({SurfacePoint.at_vertex(v) for v in VERTICES}) == 8

    @given(edges, inner)
    def test_edge_point_same_from_both_faces(self, edge: frozenset[str], t: F) -> None:
        f, g = sorted(CUBE.edge_faces(edge))
        p, q = SurfacePoint(f, point_on_edge(f, edge, t)), SurfacePoint(g, point_on_edge(g, edge, t))
        assert p == q
        assert p.edge == q.edge == edge
        assert p.face == f

    @given(edges, inner, inner)
    def test_different_edge_points_differ(self, edge: frozenset[str], t: F, s: F) -> None:
        f = min(CUBE.edge_faces(edge))
        assert (SurfacePoint(f, point_on_edge(f, edge, t)) == SurfacePoint(f, point_on_edge(f, edge, s))) == (t == s)

    @given(st.sampled_from(FACES), inner, inner)
    def test_face_point_kept_as_is(self, face: int, u: F, v: F) -> None:
        p = SurfacePoint(face, Vec(u, v))
        assert (p.face, p.local, p.faces) == (face, Vec(u, v), {face})


class TestLocalIn:
    @given(st.sampled_from(FACES), unit, unit)
    def test_round_trip_through_every_containing_face(self, face: int, u: F, v: F) -> None:
        p = SurfacePoint(face, Vec(u, v))
        assert p.local_in(face) == Vec(u, v)
        for g in p.faces:
            assert SurfacePoint(g, p.local_in(g)) == p

    def test_vertex_in_each_face(self) -> None:
        a = SurfacePoint.at_vertex("A")
        assert {f: a.local_in(f) for f in sorted(a.faces)} == {1: Vec(0, 1), 4: Vec(0, 1), 5: Vec(0, 0)}

    def test_not_on_face_rejected(self) -> None:
        with pytest.raises(ValueError, match="does not lie on face"):
            SurfacePoint(1, Vec(F(1, 2), F(1, 2))).local_in(2)

    @given(edges, inner)
    def test_fold_edges_of_default_net_coincide_on_sheet(self, edge: frozenset[str], t: F) -> None:
        """For an edge that is a fold in the default net, both faces put the point at the same sheet position."""
        f, g = CUBE.edge_faces(edge)
        p = SurfacePoint(f, point_on_edge(f, edge, t))
        on_sheet_f = CUBE.default_placement(f).apply(p.local_in(f))
        on_sheet_g = CUBE.default_placement(g).apply(p.local_in(g))
        is_fold = "".join(sorted(edge)) in {"CD", "CH", "DG", "GH", "EF"}
        assert (on_sheet_f == on_sheet_g) == is_fold
