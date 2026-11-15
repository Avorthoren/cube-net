# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The cube as a body: its tables give the cube of docs/idea.txt and its default net."""

from fractions import Fraction as F
from itertools import permutations

import pytest

from cube_net.core.body import CUBE, FACE_CORNERS, FACES, LOCAL_CORNERS, VERTICES, BodyEdge, Side
from cube_net.core.geometry import Rigid90, Vec

# Vertex images of the default net, exactly as labelled in docs/idea.txt.
DEFAULT_NET_IMAGES: dict[str, set[Vec]] = {
    "A": {Vec(11, 14), Vec(10, 13), Vec(11, 10)},  # A_1, A_2, A_3
    "B": {Vec(12, 14), Vec(13, 13), Vec(12, 10)},  # B_1, B_2, B_3
    "C": {Vec(11, 13)},  # C_1
    "D": {Vec(12, 13)},  # D_1
    "E": {Vec(11, 11), Vec(10, 12)},  # E_1, E_2
    "F": {Vec(12, 11), Vec(13, 12)},  # F_1, F_2
    "G": {Vec(12, 12)},  # G_1
    "H": {Vec(11, 12)},  # H_1
}

PLACEMENTS = dict(CUBE.start)


def edge(name: str) -> BodyEdge:
    return next(e for e in CUBE.edges if e.names == frozenset(name))


def corner_local(face: int, vertex: str) -> Vec:
    return LOCAL_CORNERS[FACE_CORNERS[face].index(vertex)]


def sheet_position(face: int, vertex: str) -> Vec:
    return PLACEMENTS[face].apply(corner_local(face, vertex))


def adjacent(f: int, g: int) -> bool:
    return any(e.faces == {f, g} for e in CUBE.edges)


def transition(f: int, g: int) -> Rigid90:
    """The map from f's frame to g's across their shared edge."""
    e = next(e for e in CUBE.edges if e.faces == {f, g})
    side = next(s for s in e.sides if s.face == f)
    return e.transition(side)


ADJACENT_PAIRS = [(f, g) for f, g in permutations(FACES, 2) if adjacent(f, g)]


class TestCombinatorics:
    def test_vertices_have_three_faces(self) -> None:
        expected = {
            "A": {1, 4, 5},
            "B": {1, 3, 5},
            "C": {1, 2, 4},
            "D": {1, 2, 3},
            "E": {4, 5, 6},
            "F": {3, 5, 6},
            "G": {2, 3, 6},
            "H": {2, 4, 6},
        }
        assert CUBE.vertex_names == VERTICES
        assert {v: set(CUBE.vertex_faces(v)) for v in VERTICES} == expected

    def test_twelve_edges_each_between_two_faces(self) -> None:
        assert len(CUBE.edges) == 12
        assert all(len(e.faces) == 2 for e in CUBE.edges)
        assert edge("AE").faces == {4, 5}  # docs/idea.txt: A_2 - E_2 separates faces 5 and 4
        assert edge("CD").faces == {1, 2}  # C_1 - D_1

    def test_each_face_meets_four_others(self) -> None:
        opposite = {1: 6, 6: 1, 2: 5, 5: 2, 3: 4, 4: 3}
        for f in FACES:
            assert {g for g in FACES if adjacent(f, g)} == set(FACES) - {f, opposite[f]}

    def test_area(self) -> None:
        assert CUBE.area == 6


class TestDefaultNet:
    def test_corners_land_on_labelled_images(self) -> None:
        images: dict[str, set[Vec]] = {v: set() for v in VERTICES}
        for face in FACES:
            for vertex in FACE_CORNERS[face]:
                images[vertex].add(sheet_position(face, vertex))
        assert images == DEFAULT_NET_IMAGES
        assert sum(len(s) for s in images.values()) == 14

    def test_reference_coordinates(self) -> None:
        assert sheet_position(2, "H") == Vec(11, 12)  # H_1
        assert sheet_position(2, "G") == Vec(12, 12)  # G_1
        assert sheet_position(2, "C") == Vec(11, 13)  # C_1

    def test_cut_and_fold_edges(self) -> None:
        """An edge is a fold in the default net iff both its faces place its endpoints at the same sheet points."""
        folds: set[str] = set()
        cuts: set[str] = set()
        for e in CUBE.edges:
            f, g = sorted(e.faces)
            same = all(sheet_position(f, v) == sheet_position(g, v) for v in e.names)
            (folds if same else cuts).add("".join(sorted(e.names)))
        assert cuts == {"AC", "BD", "EH", "FG", "AE", "BF", "AB"}
        assert folds == {"CD", "CH", "DG", "GH", "EF"}

    def test_default_placements_are_translations(self) -> None:
        assert sorted(PLACEMENTS) == list(FACES)
        assert all(p.k == 0 for p in PLACEMENTS.values())


class TestTransitions:
    @pytest.mark.parametrize(("f", "g"), ADJACENT_PAIRS)
    def test_shared_edge_endpoints_map_to_same_cube_vertices(self, f: int, g: int) -> None:
        t = transition(f, g)
        (e,) = (e for e in CUBE.edges if e.faces == {f, g})
        for vertex in e.names:
            assert t.apply(corner_local(f, vertex)) == corner_local(g, vertex)

    @pytest.mark.parametrize(("f", "g"), ADJACENT_PAIRS)
    def test_unfolds_next_to_neighbour(self, f: int, g: int) -> None:
        """Face f lands right outside g's unit square, adjacent to the shared edge (orientation is consistent)."""
        center = Vec(F(1, 2), F(1, 2))
        assert (transition(f, g).apply(center) - center).length_squared() == 1

    @pytest.mark.parametrize(("f", "g"), ADJACENT_PAIRS)
    def test_inverse_direction(self, f: int, g: int) -> None:
        assert transition(g, f) == transition(f, g).inverse()

    def test_matches_default_net_for_folds(self) -> None:
        """For faces glued along a fold of the default net, the transition is just the default layout."""
        for f, g in [(1, 2), (2, 4), (2, 3), (2, 6), (6, 5)]:
            assert transition(f, g) == PLACEMENTS[g].inverse() @ PLACEMENTS[f]

    def test_rotation_for_cut_edge_ac(self) -> None:
        """Face 4 unfolded across AC into face 1's frame lies to the left of face 1 (see Rigid90 tests)."""
        assert transition(4, 1) == Rigid90(3, Vec(-1, 1))

    @pytest.mark.parametrize("vertex", VERTICES)
    def test_going_around_a_vertex_misses_90_degrees(self, vertex: str) -> None:
        """Unfolding the 3 faces around a vertex one after another covers only 270 degrees, so the loop
        f -> g -> h -> f is a quarter turn around the vertex, not the identity."""
        f, g, h = sorted(CUBE.vertex_faces(vertex))
        loop = transition(h, f) @ transition(g, h) @ transition(f, g)
        assert loop.k in (1, 3)
        p = corner_local(f, vertex)
        assert loop.apply(p) == p

    def test_sides_of_an_edge(self) -> None:
        e = edge("AE")
        assert {s.face for s in e.sides} == {4, 5}
        assert e.other(e.sides[0]) == e.sides[1]
        assert all(CUBE.side_edge(s) is e for s in e.sides)
        assert CUBE.side_edge(Side(1, 0)) is edge("CD")
