# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from fractions import Fraction as F
from itertools import permutations

import pytest

from cube_net.core.cube import (
    CUBE,
    DEFAULT_FACE_ORIGINS,
    FACE_CORNERS,
    FACES,
    LOCAL_CORNERS,
    VERTICES,
    CubeTableError,
    CubeTopology,
)
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


def edge(name: str) -> frozenset[str]:
    return frozenset(name)


def sheet_position(face: int, vertex: str) -> Vec:
    return CUBE.default_placement(face).apply(CUBE.corner_local(face, vertex))


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
        assert {v: set(CUBE.vertex_faces(v)) for v in VERTICES} == expected

    def test_twelve_edges_each_between_two_faces(self) -> None:
        assert len(CUBE.edges) == 12
        assert all(len(CUBE.edge_faces(e)) == 2 for e in CUBE.edges)
        assert CUBE.edge_faces(edge("AE")) == {4, 5}  # docs/idea.txt: A_2 - E_2 separates faces 5 and 4
        assert CUBE.edge_faces(edge("CD")) == {1, 2}  # C_1 - D_1

    def test_opposite_faces(self) -> None:
        assert {f: CUBE.opposite(f) for f in FACES} == {1: 6, 6: 1, 2: 5, 5: 2, 3: 4, 4: 3}

    def test_adjacency(self) -> None:
        for f in FACES:
            neighbours = {g for g in FACES if CUBE.are_adjacent(f, g)}
            assert neighbours == set(FACES) - {f, CUBE.opposite(f)}
        assert not CUBE.are_adjacent(1, 1)

    def test_shared_edge(self) -> None:
        assert CUBE.shared_edge(4, 5) == edge("AE")
        assert CUBE.shared_edge(5, 4) == edge("AE")
        with pytest.raises(ValueError, match="not adjacent"):
            CUBE.shared_edge(1, 6)

    def test_corner_local(self) -> None:
        assert CUBE.corner_local(1, "A") == Vec(0, 1)
        with pytest.raises(ValueError, match="not a corner"):
            CUBE.corner_local(1, "E")


class TestDefaultNet:
    def test_corners_land_on_labelled_images(self) -> None:
        images: dict[str, set[Vec]] = {v: set() for v in VERTICES}
        for face in FACES:
            for vertex in CUBE.face_corners(face):
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
            f, g = CUBE.edge_faces(e)
            same = all(sheet_position(f, v) == sheet_position(g, v) for v in e)
            (folds if same else cuts).add("".join(sorted(e)))
        assert cuts == {"AC", "BD", "EH", "FG", "AE", "BF", "AB"}
        assert folds == {"CD", "CH", "DG", "GH", "EF"}

    def test_default_placements_are_translations(self) -> None:
        assert all(CUBE.default_placement(f).k == 0 for f in FACES)


class TestTransitions:
    @pytest.mark.parametrize(("f", "g"), [(f, g) for f, g in permutations(FACES, 2) if CUBE.are_adjacent(f, g)])
    def test_shared_edge_endpoints_map_to_same_cube_vertices(self, f: int, g: int) -> None:
        t = CUBE.transition(f, g)
        for vertex in CUBE.shared_edge(f, g):
            assert t.apply(CUBE.corner_local(f, vertex)) == CUBE.corner_local(g, vertex)

    @pytest.mark.parametrize(("f", "g"), [(f, g) for f, g in permutations(FACES, 2) if CUBE.are_adjacent(f, g)])
    def test_unfolds_next_to_neighbour(self, f: int, g: int) -> None:
        """Face f lands right outside g's unit square, adjacent to the shared edge (orientation is consistent)."""
        center = Vec(F(1, 2), F(1, 2))
        moved_center = CUBE.transition(f, g).apply(center)
        assert (moved_center - center).length_squared() == 1

    @pytest.mark.parametrize(("f", "g"), [(f, g) for f, g in permutations(FACES, 2) if CUBE.are_adjacent(f, g)])
    def test_inverse_direction(self, f: int, g: int) -> None:
        assert CUBE.transition(g, f) == CUBE.transition(f, g).inverse()

    def test_matches_default_net_for_folds(self) -> None:
        """For faces glued along a fold of the default net, the transition is just the default layout."""
        for f, g in [(1, 2), (2, 4), (2, 3), (2, 6), (6, 5)]:
            expected = CUBE.default_placement(g).inverse() @ CUBE.default_placement(f)
            assert CUBE.transition(f, g) == expected

    def test_rotation_for_cut_edge_ac(self) -> None:
        """Face 4 unfolded across AC into face 1's frame lies to the left of face 1 (see Rigid90 tests)."""
        assert CUBE.transition(4, 1) == Rigid90(3, Vec(-1, 1))

    @pytest.mark.parametrize("vertex", VERTICES)
    def test_going_around_a_vertex_misses_90_degrees(self, vertex: str) -> None:
        """Unfolding the 3 faces around a vertex one after another covers only 270 degrees, so the loop
        f -> g -> h -> f is a quarter turn around the vertex, not the identity."""
        f, g, h = sorted(CUBE.vertex_faces(vertex))
        loop = CUBE.transition(h, f) @ CUBE.transition(g, h) @ CUBE.transition(f, g)
        assert loop.k in (1, 3)
        p = CUBE.corner_local(f, vertex)
        assert loop.apply(p) == p


def corners_with(**changes: str) -> dict[int, tuple[str, ...]]:
    """FACE_CORNERS with some faces replaced, e.g. corners_with(f5="HBFE")."""
    table: dict[int, tuple[str, ...]] = dict(FACE_CORNERS)
    for key, labels in changes.items():
        table[int(key[1:])] = tuple(labels)
    return table


def origins_with(**changes: Vec) -> dict[int, Vec]:
    table = dict(DEFAULT_FACE_ORIGINS)
    for key, origin in changes.items():
        table[int(key[1:])] = origin
    return table


class TestValidation:
    """Every malformed table fails once, at construction, with a CubeTableError and a readable message."""

    def test_default_tables_are_valid(self) -> None:
        CubeTopology(FACE_CORNERS, DEFAULT_FACE_ORIGINS)

    def test_error_is_a_value_error(self) -> None:
        assert issubclass(CubeTableError, ValueError)

    @pytest.mark.parametrize(
        ("table", "message"),
        [
            (
                {f: c for f, c in FACE_CORNERS.items() if f != 6},
                r"expected faces \(1, 2, 3, 4, 5, 6\), got \[1, 2, 3, 4, 5\]",
            ),
            (corners_with(f1="CDB"), r"face 1 must have 4 corners, got 3"),
            (corners_with(f1="ADBA"), r"face 1 has repeated corner labels"),
            (corners_with(f1="CDBX"), r"face 1 has unknown vertex labels \['X'\]"),
            (corners_with(f5="HBFE"), r"vertex A belongs to 2 faces \[1, 4\], expected 3"),
            (corners_with(f6="EFGA"), r"vertex A belongs to 4 faces \[1, 4, 5, 6\], expected 3"),
            (corners_with(f5="FBAE", f6="FEGH"), r"edge FG belongs to faces \[3\], expected 2"),
            (corners_with(f3="BFGD"), r"faces \d and \d have inconsistent orientation"),
            (
                corners_with(f6="EHGF"),
                r"inconsistent orientation: corners of every face must be listed counter-clockwise",
            ),
        ],
    )
    def test_bad_face_corners(self, table: dict[int, tuple[str, ...]], message: str) -> None:
        with pytest.raises(CubeTableError, match=message):
            CubeTopology(table)  # type: ignore[arg-type]

    def test_corners_disagreeing_with_default_net(self) -> None:
        """A valid cube, but face 3 is rotated in its frame, so along its fold with face 2 the labels don't match."""
        table = corners_with(f3="BDGF")
        with pytest.raises(CubeTableError, match=r"faces 2 and 3 touch along a whole side .* differ"):
            CubeTopology(table)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("origins", "message"),
        [
            ({f: o for f, o in DEFAULT_FACE_ORIGINS.items() if f != 5}, r"default net must place faces"),
            (origins_with(f6=Vec(11, 12)), r"faces 2 and 6 overlap in the default net"),
            (origins_with(f6=Vec(F(23, 2), F(23, 2))), r"faces 2 and 6 overlap in the default net"),
            (origins_with(f3=Vec(10, 12), f4=Vec(12, 12)), r"touch along a whole side .* differ"),
            (origins_with(f5=Vec(20, 20)), r"6 faces connected by exactly 5 folds, got 4 folds"),
        ],
    )
    def test_bad_default_origins(self, origins: dict[int, Vec], message: str) -> None:
        with pytest.raises(CubeTableError, match=message):
            CubeTopology(FACE_CORNERS, origins)

    def test_local_corners_counter_clockwise(self) -> None:
        a, b, c, _ = LOCAL_CORNERS
        assert (b - a).cross(c - a) > 0


class TestLookupErrors:
    """Bad arguments to the query methods give readable ValueErrors (no extra cost on the success path)."""

    @pytest.mark.parametrize(
        ("call", "message"),
        [
            (lambda: CUBE.face_corners(7), "no such face: 7"),
            (lambda: CUBE.opposite(0), "no such face: 0"),
            (lambda: CUBE.default_placement(9), "no such face: 9"),
            (lambda: CUBE.vertex_faces("X"), "no such vertex: 'X'"),
            (lambda: CUBE.edge_faces(frozenset("AG")), "no such edge: AG"),
            (lambda: CUBE.corner_local(1, "E"), "vertex E is not a corner of face 1"),
            (lambda: CUBE.shared_edge(1, 6), "faces 1 and 6 are not adjacent"),
            (lambda: CUBE.transition(2, 5), "faces 2 and 5 are not adjacent"),
        ],
    )
    def test_messages(self, call: Callable[[], object], message: str) -> None:
        with pytest.raises(ValueError, match=message):
            call()
