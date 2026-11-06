"""`CubeTopology`: faces, vertices, edges of the unit cube and how face frames connect (docs/plan.md, section 3.2).

Every face has its own local frame: `(u, v)` in `[0, 1]^2`, with the face seen from outside the cube and `u`, `v`
oriented counter-clockwise (like x, y on the sheet). Frames are chosen so that in the default net (docs/idea.txt)
every face is placed by a pure translation, e.g. face 2 local `(0, 0)` is sheet `(11, 12)`.

Everything else (which faces meet at an edge or a vertex, how one face's frame continues into its neighbour's) is
derived from the table of face corners below, which is just the default net from docs/idea.txt written down.
"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import combinations
from types import MappingProxyType

from cube_net.core.geometry import Rigid90, Vec

type Face = int
type VertexLabel = str
type Edge = frozenset[VertexLabel]


FACES: tuple[Face, ...] = (1, 2, 3, 4, 5, 6)
VERTICES: tuple[VertexLabel, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")

LOCAL_CORNERS: tuple[Vec, Vec, Vec, Vec] = (Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(0, 1))

# Corners of a face's local square, counter-clockwise, starting at the origin.
FACE_CORNERS: Mapping[Face, tuple[VertexLabel, VertexLabel, VertexLabel, VertexLabel]] = MappingProxyType(
    {
        # Labels at local (0,0), (1,0), (1,1), (0,1), read off the default net in docs/idea.txt.
        1: ("C", "D", "B", "A"),
        2: ("H", "G", "D", "C"),
        3: ("G", "F", "B", "D"),
        4: ("E", "H", "C", "A"),
        5: ("A", "B", "F", "E"),
        6: ("E", "F", "G", "H"),
    }
)

DEFAULT_FACE_ORIGINS: Mapping[Face, Vec] = MappingProxyType(
    {
        # Sheet position of local (0, 0) of each face in the default net (H_1 = (11, 12), see docs/idea.txt).
        1: Vec(11, 13),
        2: Vec(11, 12),
        3: Vec(12, 12),
        4: Vec(10, 12),
        5: Vec(11, 10),
        6: Vec(11, 11),
    }
)


class CubeTableError(ValueError):
    """The hand-written cube tables (`FACE_CORNERS`, `DEFAULT_FACE_ORIGINS`) are inconsistent."""


class CubeTopology:
    """Combinatorics of the cube plus the rigid maps between neighbouring face frames. Immutable after creation.

    All consistency checks of the input tables run once, here in `__init__`, and raise `CubeTableError` with a
    readable message. The query methods afterwards rely on those checks and do no validation of the tables
    themselves. Use the module-level instance `CUBE`.
    """

    def __init__(
        self,
        face_corners: Mapping[Face, tuple[VertexLabel, VertexLabel, VertexLabel, VertexLabel]] = FACE_CORNERS,
        face_origins: Mapping[Face, Vec] = DEFAULT_FACE_ORIGINS,
    ) -> None:
        self._corners = dict(face_corners)
        _check_face_table(self._corners)

        self._corner_local: dict[tuple[Face, VertexLabel], Vec] = {
            (face, label): LOCAL_CORNERS[i] for face, labels in self._corners.items() for i, label in enumerate(labels)
        }
        self._vertex_faces: dict[VertexLabel, frozenset[Face]] = {
            label: frozenset(f for f, labels in self._corners.items() if label in labels) for label in VERTICES
        }
        edge_faces: dict[Edge, list[Face]] = {}
        for face, labels in self._corners.items():
            for i in range(4):
                edge_faces.setdefault(frozenset((labels[i], labels[(i + 1) % 4])), []).append(face)
        self._edge_faces: dict[Edge, frozenset[Face]] = {e: frozenset(fs) for e, fs in edge_faces.items()}
        self._face_edge: dict[frozenset[Face], Edge] = {fs: e for e, fs in self._edge_faces.items()}
        self._check_vertices_and_edges(edge_faces)

        self._opposite: dict[Face, Face] = self._compute_opposites()
        self._transitions: dict[tuple[Face, Face], Rigid90] = {
            (f, g): self._compute_transition(f, g) for f in FACES for g in FACES if self.are_adjacent(f, g)
        }
        self._check_orientation()

        self._origins = dict(face_origins)
        self._check_default_net()

    # --- faces ----------------------------------------------------------------------------------------------------

    def face_corners(self, face: Face) -> tuple[VertexLabel, VertexLabel, VertexLabel, VertexLabel]:
        """Vertex labels at local (0,0), (1,0), (1,1), (0,1) of `face`."""
        try:
            return self._corners[face]
        except KeyError:
            raise ValueError(f"no such face: {face!r}") from None

    def corner_local(self, face: Face, vertex: VertexLabel) -> Vec:
        """Local coordinates of a cube vertex in the frame of one of its faces."""
        try:
            return self._corner_local[(face, vertex)]
        except KeyError:
            raise ValueError(f"vertex {vertex} is not a corner of face {face}") from None

    def are_adjacent(self, f: Face, g: Face) -> bool:
        """True if faces `f` and `g` share an edge (a face is not adjacent to itself)."""
        return frozenset((f, g)) in self._face_edge

    def opposite(self, face: Face) -> Face:
        """The face that shares no vertex with `face`."""
        try:
            return self._opposite[face]
        except KeyError:
            raise ValueError(f"no such face: {face!r}") from None

    # --- vertices and edges ---------------------------------------------------------------------------------------

    def vertex_faces(self, vertex: VertexLabel) -> frozenset[Face]:
        """The 3 faces meeting at a cube vertex."""
        try:
            return self._vertex_faces[vertex]
        except KeyError:
            raise ValueError(f"no such vertex: {vertex!r}") from None

    @property
    def edges(self) -> frozenset[Edge]:
        """All 12 edges, each as the set of its two vertex labels."""
        return frozenset(self._edge_faces)

    def edge_faces(self, edge: Edge) -> frozenset[Face]:
        """The 2 faces sharing an edge."""
        try:
            return self._edge_faces[edge]
        except KeyError:
            raise ValueError(f"no such edge: {_edge_name(edge)}") from None

    def shared_edge(self, f: Face, g: Face) -> Edge:
        """The edge between two adjacent faces."""
        try:
            return self._face_edge[frozenset((f, g))]
        except KeyError:
            raise ValueError(f"faces {f} and {g} are not adjacent") from None

    # --- frames ---------------------------------------------------------------------------------------------------

    def transition(self, f: Face, g: Face) -> Rigid90:
        """Map from `f`-local to `g`-local coordinates that "unfolds" face `f` across their shared edge.

        Points of the shared edge map to the same cube points in `g`'s frame; the rest of `f`'s square lands right
        outside `g`'s square, next to that edge (as if the two faces were laid flat on the sheet side by side).
        """
        try:
            return self._transitions[(f, g)]
        except KeyError:
            raise ValueError(f"faces {f} and {g} are not adjacent") from None

    def default_placement(self, face: Face) -> Rigid90:
        """Placement (local -> sheet) of `face` in the default net: a pure translation."""
        try:
            return Rigid90.translation(self._origins[face])
        except KeyError:
            raise ValueError(f"no such face: {face!r}") from None

    # --- construction helpers (run once, in __init__) -------------------------------------------------------------

    def _compute_transition(self, f: Face, g: Face) -> Rigid90:
        x, y = sorted(self.shared_edge(f, g))
        return Rigid90.from_segments(
            self.corner_local(f, x), self.corner_local(f, y), self.corner_local(g, x), self.corner_local(g, y)
        )

    def _compute_opposites(self) -> dict[Face, Face]:
        # Exactly one candidate per face: `_check_vertices_and_edges` guarantees 4 distinct neighbours out of 5.
        return {face: next(g for g in FACES if g != face and not self.are_adjacent(face, g)) for face in FACES}

    def _check_vertices_and_edges(self, edge_faces: Mapping[Edge, list[Face]]) -> None:
        for vertex, faces in self._vertex_faces.items():
            if len(faces) != 3:
                raise CubeTableError(f"vertex {vertex} belongs to {len(faces)} faces {sorted(faces)}, expected 3")
        for edge, faces_list in edge_faces.items():
            if len(faces_list) != 2:  # never the same face twice: a face's 4 labels are distinct
                raise CubeTableError(f"edge {_edge_name(edge)} belongs to faces {faces_list}, expected 2")
        if len(edge_faces) != 12:
            raise CubeTableError(f"cube must have 12 edges, got {len(edge_faces)}")
        # Not implied by the checks above for an arbitrary table (two faces could share two opposite sides).
        # The 3 faces at a vertex being pairwise adjacent, which SurfacePoint relies on, follows from the vertex and
        # edge checks: 3 edges at a vertex, each in 2 of its 3 faces.
        for face in FACES:
            neighbours = [g for g in FACES if g != face and self.are_adjacent(face, g)]
            if len(neighbours) != 4:
                raise CubeTableError(f"face {face} must have 4 distinct neighbours, got {neighbours}")

    def _check_orientation(self) -> None:
        """Unfolding f across the shared edge must put it next to g, not on top of it: every face's corners must be
        listed counter-clockwise as seen from outside the cube (consistently for all faces)."""
        center = Vec(1, 1) / 2
        for (f, g), t in self._transitions.items():
            if (t.apply(center) - center).length_squared() != 1:
                raise CubeTableError(
                    f"faces {f} and {g} have inconsistent orientation: "
                    f"corners of every face must be listed counter-clockwise as seen from outside the cube"
                )

    def _check_default_net(self) -> None:
        if sorted(self._origins) != list(FACES):
            raise CubeTableError(f"default net must place faces {FACES}, got {sorted(self._origins)}")
        for f, g in combinations(FACES, 2):
            d = self._origins[f] - self._origins[g]
            if abs(d.x) < 1 and abs(d.y) < 1:
                raise CubeTableError(f"faces {f} and {g} overlap in the default net")

        # Every side shared by two squares on the sheet must be a fold: same labels at the same sheet points.
        sides: dict[frozenset[Vec], list[tuple[Face, dict[Vec, VertexLabel]]]] = {}
        for face in FACES:
            placement = self.default_placement(face)
            labels = self._corners[face]
            for i in range(4):
                ends = {placement.apply(LOCAL_CORNERS[j]): labels[j] for j in (i, (i + 1) % 4)}
                sides.setdefault(frozenset(ends), []).append((face, ends))
        parent = {face: face for face in FACES}  # union-find over faces glued by folds

        def root(face: Face) -> Face:
            while parent[face] != face:
                face = parent[face]
            return face

        folds = 0
        for entries in sides.values():
            if len(entries) < 2:
                continue
            (f, f_labels), (g, g_labels) = entries
            if f_labels != g_labels:
                raise CubeTableError(
                    f"faces {f} and {g} touch along a whole side in the default net, but their corner labels there "
                    f"differ: {sorted(f_labels.values())} vs {sorted(g_labels.values())}"
                )
            folds += 1
            parent[root(f)] = root(g)
        if len({root(face) for face in FACES}) != 1 or folds != 5:
            raise CubeTableError(f"default net must be 6 faces connected by exactly 5 folds, got {folds} folds")


def _check_face_table(corners: Mapping[Face, tuple[VertexLabel, ...]]) -> None:
    if sorted(corners) != list(FACES):
        raise CubeTableError(f"expected faces {FACES}, got {sorted(corners)}")
    for face, labels in corners.items():
        if len(labels) != 4:
            raise CubeTableError(f"face {face} must have 4 corners, got {len(labels)}: {labels}")
        if len(set(labels)) != 4:
            raise CubeTableError(f"face {face} has repeated corner labels: {labels}")
        unknown = [label for label in labels if label not in VERTICES]
        if unknown:
            raise CubeTableError(f"face {face} has unknown vertex labels {unknown}, expected some of {VERTICES}")


def _edge_name(edge: Edge) -> str:
    return "".join(sorted(edge))


# The one and only cube.
CUBE = CubeTopology()
