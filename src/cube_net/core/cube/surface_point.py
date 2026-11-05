"""`SurfacePoint`: a point on the surface of the cube in canonical form (docs/plan.md, section 3.2).

A point on an edge belongs to 2 faces and a cube vertex to 3, so the same point can be written in several face frames.
`SurfacePoint` always stores it in the frame of the **lowest-numbered** face that contains it. As a result, two
`SurfacePoint`s are equal exactly when they are the same point of the cube, no matter which face they were created
from. That is what makes "counterpart" and "matching" (docs/idea.txt) well-defined.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from cube_net.core.cube.topology import CUBE, FACES, LOCAL_CORNERS, Edge, Face, VertexLabel
from cube_net.core.geometry import Vec


class SurfacePointKind(Enum):
    FACE = "face"
    """Strictly inside a face: 1 face."""
    EDGE = "edge"
    """Strictly inside an edge: 2 faces."""
    VERTEX = "vertex"
    """A vertex of the cube: 3 faces."""


@dataclass(frozen=True, slots=True)
class SurfacePoint:
    """A point of the cube surface. Create it from any face that contains it: `SurfacePoint(face, local)`.

    Equality and hashing use only the canonical `(face, local)` pair; the other attributes are derived from it.
    """

    face: Face
    """The lowest-numbered face containing the point (the canonical frame)."""
    local: Vec
    """Coordinates in the canonical face's frame, in [0, 1]^2."""
    faces: frozenset[Face] = field(compare=False)
    """All faces containing the point: 1, 2 or 3 of them. They define the point's colours."""
    vertex: VertexLabel | None = field(compare=False)
    """The cube vertex label, if the point is a vertex of the cube."""
    edge: Edge | None = field(compare=False)
    """The cube edge (as a set of 2 vertex labels), if the point lies strictly inside an edge."""

    def __init__(self, face: Face, local: Vec) -> None:
        if face not in FACES:
            raise ValueError(f"no such face: {face!r}")
        if not (0 <= local.x <= 1 and 0 <= local.y <= 1):
            raise ValueError(f"local point {local} is outside the unit square of face {face}")

        vertex = _corner_label(face, local)
        edge = None if vertex is not None else _edge_containing(face, local)
        if vertex is not None:
            faces = CUBE.vertex_faces(vertex)
        elif edge is not None:
            faces = CUBE.edge_faces(edge)
        else:
            faces = frozenset((face,))

        canonical = min(faces)
        if canonical != face:
            local = CUBE.transition(face, canonical).apply(local)

        object.__setattr__(self, "face", canonical)
        object.__setattr__(self, "local", local)
        object.__setattr__(self, "faces", faces)
        object.__setattr__(self, "vertex", vertex)
        object.__setattr__(self, "edge", edge)

    @classmethod
    def at_vertex(cls, vertex: VertexLabel) -> SurfacePoint:
        """The cube vertex with the given label."""
        face = min(CUBE.vertex_faces(vertex))
        return cls(face, CUBE.corner_local(face, vertex))

    @property
    def kind(self) -> SurfacePointKind:
        if self.vertex is not None:
            return SurfacePointKind.VERTEX
        if self.edge is not None:
            return SurfacePointKind.EDGE
        return SurfacePointKind.FACE

    def local_in(self, face: Face) -> Vec:
        """Coordinates of this point in the frame of `face`, which must be one of `self.faces`."""
        if face not in self.faces:
            raise ValueError(f"{self} does not lie on face {face}")
        if face == self.face:
            return self.local
        return CUBE.transition(self.face, face).apply(self.local)

    def __repr__(self) -> str:
        label = f" {self.vertex}" if self.vertex else (f" on {''.join(sorted(self.edge))}" if self.edge else "")
        return f"SurfacePoint({self.face}, {self.local!r}{label})"


def _corner_label(face: Face, local: Vec) -> VertexLabel | None:
    # FACE_CORNERS is validated once in CubeTopology.__init__ (4 labels per face), so no length check here.
    for i, corner in enumerate(LOCAL_CORNERS):
        if local == corner:
            return CUBE.face_corners(face)[i]
    return None


def _edge_containing(face: Face, local: Vec) -> Edge | None:
    """The edge of `face` that `local` lies on (not at a corner: corners are handled before), if any."""
    corners = CUBE.face_corners(face)
    # Side i of the local square goes from LOCAL_CORNERS[i] to LOCAL_CORNERS[i + 1].
    for side, on_side in enumerate((local.y == 0, local.x == 1, local.y == 1, local.x == 0)):
        if on_side:
            return frozenset((corners[side], corners[(side + 1) % 4]))
    return None
