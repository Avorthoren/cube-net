# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.body import CUBE, Body, BodyError, Side, SurfacePoint
from cube_net.core.geometry import Rigid90, Vec

IDENTITY = Rigid90.identity()

SQUARE = (Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(0, 1))


class TestPillow:
    """Two faces sharing 4 edges: points on two different edges between the same faces."""

    def test_four_edges_between_the_same_two_faces(self, pillow: Body) -> None:
        body = pillow
        assert sorted("".join(sorted(e.names)) for e in body.edges) == ["PQ", "PS", "QR", "RS"]
        assert all(e.faces == {1, 2} for e in body.edges)
        assert body.area == 2

    def test_a_segment_across_a_face_is_not_an_edge(self, pillow: Body) -> None:
        body = pillow
        x, y = Vec(F(1, 2), 0), Vec(0, F(1, 2))  # on PQ and on SP: both points are on faces 1 and 2
        assert SurfacePoint(body, 1, x).faces == SurfacePoint(body, 1, y).faces == {1, 2}
        assert body.edge_through(1, x, y) is None
        assert body.segment_faces(1, x, y) == {1}

    def test_a_segment_along_a_side_is_on_its_edge(self, pillow: Body) -> None:
        body = pillow
        edge = body.edge_through(1, Vec(F(1, 2), 0), Vec(1, 0))
        assert edge is not None and edge.names == {"P", "Q"}
        assert body.segment_faces(1, Vec(F(1, 2), 0), Vec(1, 0)) == {1, 2}

    def test_edge_points_are_the_same_from_both_faces(self, pillow: Body) -> None:
        body = pillow
        assert SurfacePoint(body, 1, Vec(F(1, 4), 0)) == SurfacePoint(body, 2, Vec(F(7, 4), 0))
        assert SurfacePoint(body, 1, Vec(0, F(1, 4))) == SurfacePoint(body, 2, Vec(2, F(1, 4)))


class TestFlatPillow:
    """A face glued to itself."""

    def test_one_face_three_edges(self, flat_pillow: Body) -> None:
        body = flat_pillow
        assert body.face_numbers == (1,)
        assert all(e.faces == {1} for e in body.edges)
        assert len(body.edges) == 3

    def test_a_point_of_a_self_glued_edge_is_one_point(self, flat_pillow: Body) -> None:
        body = flat_pillow
        p, q = SurfacePoint(body, 1, Vec(F(1, 4), 0)), SurfacePoint(body, 1, Vec(F(7, 4), 0))
        assert p == q
        assert p.edge is not None and p.faces == {1}
        assert p.locals_in(1) == [Vec(F(1, 4), 0), Vec(F(7, 4), 0)]
        with pytest.raises(ValueError, match="2 times"):
            p.local_in(1)

    def test_a_vertex_at_two_corners_of_one_face(self, flat_pillow: Body) -> None:
        body = flat_pillow
        assert SurfacePoint(body, 1, Vec(0, 0)) == SurfacePoint(body, 1, Vec(2, 0)) == SurfacePoint.at_vertex(body, "P")
        assert body.vertex_corners("P") == ((1, Vec(0, 0)), (1, Vec(2, 0)))

    def test_segments_on_its_edges(self, flat_pillow: Body) -> None:
        body = flat_pillow
        assert body.edge_through(1, Vec(0, 0), Vec(1, 0)) is body.edge_through(1, Vec(1, 0), Vec(2, 0))
        assert body.edge_through(1, Vec(F(1, 2), 0), Vec(F(1, 2), 1)) is None


class TestQueries:
    def test_sides_through(self) -> None:
        assert CUBE.sides_through(1, Vec(0, 0)) == [Side(1, 0), Side(1, 3)]
        assert CUBE.sides_through(1, Vec(F(1, 2), 0)) == [Side(1, 0)]
        assert CUBE.sides_through(1, Vec(F(1, 2), F(1, 2))) == []

    def test_lookup_errors(self) -> None:
        with pytest.raises(ValueError, match="no such face: 7"):
            CUBE.face(7)
        with pytest.raises(ValueError, match="no such vertex: 'X'"):
            CUBE.vertex_corners("X")

    def test_transitions_are_inverse(self) -> None:
        for edge in CUBE.edges:
            s, t = edge.sides
            assert edge.transition(t) == edge.transition(s).inverse()


def square_pillow(**changes: object) -> Body:
    """The pillow, with some of its description replaced."""
    faces: dict[int, tuple[tuple[Vec, ...], tuple[str, ...]]] = {
        1: (SQUARE, ("P", "Q", "R", "S")),
        2: ((Vec(1, 0), Vec(2, 0), Vec(2, 1), Vec(1, 1)), ("Q", "P", "S", "R")),
    }
    start: list[tuple[int, Rigid90]] = [(1, IDENTITY), (2, IDENTITY)]
    faces.update(changes.get("faces", {}))  # type: ignore[call-overload]
    return Body(faces, changes.get("start", start))  # type: ignore[arg-type]


class TestValidation:
    """Every inconsistent description fails once, at construction, with a readable BodyError."""

    def test_error_is_a_value_error(self) -> None:
        assert issubclass(BodyError, ValueError)

    @pytest.mark.parametrize(
        ("faces", "message"),
        [
            ({4: (SQUARE, ("A", "B", "C", "D"))}, r"faces must be numbered 1, 2, \.\.\., got \[1, 2, 4\]"),
            ({2: (SQUARE[:2], ("Q", "P"))}, r"face 2 needs at least 3 corners, got 2"),
            ({2: (SQUARE, ("Q", "P", "S"))}, r"face 2 has 4 corners but 3 names"),
            ({2: ((Vec(0, 0), Vec(1, 0), Vec(1, 0), Vec(0, 1)), "QPSR")}, r"face 2 has two corners at the same point"),
            ({2: (SQUARE[::-1], ("Q", "P", "S", "R"))}, r"corners of face 2 must be counter-clockwise"),
            ({2: (SQUARE, ("Q", "Q", "S", "R"))}, r"side 0 of face 2 joins vertex Q to itself"),
            ({2: (SQUARE, ("Q", "P", "S", "T"))}, r"1 face sides join vertices"),
            ({2: (SQUARE, ("P", "Q", "R", "S"))}, r"the two sides P-Q run the same way"),
            (
                {2: ((Vec(1, 0), Vec(3, 0), Vec(3, 1), Vec(1, 1)), ("Q", "P", "S", "R"))},
                r"the two sides P-Q have different lengths",
            ),
        ],
    )
    def test_bad_faces(self, faces: dict[int, object], message: str) -> None:
        with pytest.raises(BodyError, match=message):
            square_pillow(faces=faces)

    def test_sides_neither_parallel_nor_perpendicular(self) -> None:
        # A 3-4-5 triangle's sides glued to a square's: equal lengths, but at an angle that isn't a multiple of 90.
        with pytest.raises(BodyError, match=r"neither parallel nor perpendicular"):
            Body(
                {
                    1: ((Vec(0, 0), Vec(5, 0), Vec(5, 5), Vec(0, 5)), ("A", "B", "C", "D")),
                    2: ((Vec(0, 0), Vec(4, 3), Vec(4, 8), Vec(0, 5)), ("B", "A", "D", "C")),
                },
                [(1, IDENTITY), (2, IDENTITY)],
            )

    def test_starting_net_must_place_every_face(self) -> None:
        with pytest.raises(BodyError, match=r"must place every face once, got faces \[1\]"):
            square_pillow(start=[(1, IDENTITY)])
