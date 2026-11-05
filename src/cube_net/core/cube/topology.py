"""`CubeTopology`: faces, vertices, edges of the unit cube and how face frames connect (docs/plan.md, section 3.2).

Every face has its own local frame: `(u, v)` in `[0, 1]^2`, with the face seen from outside the cube and `u`, `v`
oriented counter-clockwise (like x, y on the sheet). Frames are chosen so that in the default net (docs/idea.txt)
every face is placed by a pure translation, e.g. face 2 local `(0, 0)` is sheet `(11, 12)`.

Everything else (which faces meet at an edge or a vertex, how one face's frame continues into its neighbour's) is
derived from the table of face corners below, which is just the default net from docs/idea.txt written down.
"""

from __future__ import annotations

from collections.abc import Mapping
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


class CubeTopology:
    """Combinatorics of the cube plus the rigid maps between neighbouring face frames. Immutable after creation.

    Use the module-level instance `CUBE`.
    """

    def __init__(
        self,
        face_corners: Mapping[Face, tuple[VertexLabel, VertexLabel, VertexLabel, VertexLabel]] = FACE_CORNERS,
    ) -> None:
        self._corners = dict(face_corners)
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
        self._check_combinatorics()
        self._transitions: dict[tuple[Face, Face], Rigid90] = {
            (f, g): self._compute_transition(f, g) for f in FACES for g in FACES if self.are_adjacent(f, g)
        }

    # --- faces ----------------------------------------------------------------------------------------------------

    def face_corners(self, face: Face) -> tuple[VertexLabel, VertexLabel, VertexLabel, VertexLabel]:
        """Vertex labels at local (0,0), (1,0), (1,1), (0,1) of `face`."""
        return self._corners[face]

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
        for g in FACES:
            if g != face and not self.are_adjacent(face, g):
                return g

        raise RuntimeError(f"Implementation error: face opposite to {face} wasn't found")

    # --- vertices and edges ---------------------------------------------------------------------------------------

    def vertex_faces(self, vertex: VertexLabel) -> frozenset[Face]:
        """The 3 faces meeting at a cube vertex."""
        return self._vertex_faces[vertex]

    @property
    def edges(self) -> frozenset[Edge]:
        """All 12 edges, each as the set of its two vertex labels."""
        return frozenset(self._edge_faces)

    def edge_faces(self, edge: Edge) -> frozenset[Face]:
        """The 2 faces sharing an edge."""
        return self._edge_faces[edge]

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

    @staticmethod
    def default_placement(face: Face) -> Rigid90:
        """Placement (local -> sheet) of `face` in the default net: a pure translation."""
        return Rigid90.translation(DEFAULT_FACE_ORIGINS[face])

    # --- internals ------------------------------------------------------------------------------------------------

    def _compute_transition(self, f: Face, g: Face) -> Rigid90:
        x, y = sorted(self.shared_edge(f, g))
        return Rigid90.from_segments(
            self.corner_local(f, x), self.corner_local(f, y), self.corner_local(g, x), self.corner_local(g, y)
        )

    def _check_combinatorics(self) -> None:
        if sorted(self._corners) != list(FACES):
            raise ValueError(f"expected faces {FACES}, got {sorted(self._corners)}")
        for vertex, faces in self._vertex_faces.items():
            if len(faces) != 3:
                raise ValueError(f"vertex {vertex} belongs to {len(faces)} faces, expected 3")
        if len(self._edge_faces) != 12:
            raise ValueError(f"cube must have 12 edges, got {len(self._edge_faces)}")
        for edge, faces in self._edge_faces.items():
            if len(faces) != 2:
                raise ValueError(f"edge {''.join(sorted(edge))} belongs to {len(faces)} faces, expected 2")


CUBE = CubeTopology()
"""The one and only cube."""
