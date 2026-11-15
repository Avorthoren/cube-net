# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`SurfacePoint`: a point on the surface of a body in canonical form (docs/plan.md, section 3.2).

A point on an edge belongs to 2 faces, a vertex to several, so the same point can be written in several face frames
(a face glued to itself can even give one point two positions in its own frame). `SurfacePoint` always stores the
smallest of all those (face, local) forms. As a result, two `SurfacePoint`s are equal exactly when they are the same
point of the body, no matter which form they were created from. That is what makes "counterpart" and "matching"
(docs/idea.txt) well-defined.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from cube_net.core.body.body import Body, BodyEdge, Face, VertexName
from cube_net.core.geometry import Vec, polygon_contains


class SurfacePointKind(Enum):
    # Strictly inside a face: 1 face.
    FACE = "face"

    # Strictly inside an edge: 2 faces (or 1, if a face is glued to itself there).
    EDGE = "edge"

    # A vertex of the body.
    VERTEX = "vertex"


@dataclass(frozen=True, slots=True)
class SurfacePoint:
    """A point of a body's surface. Create it from any face that contains it: `SurfacePoint(body, face, local)`.

    Equality and hashing use only the canonical `(face, local)` pair (points of different bodies are never compared);
    the other attributes are derived from it.
    """

    body: Body = field(compare=False, repr=False)

    # The face of the smallest (face, local) form (the canonical frame).
    face: Face

    # Coordinates in the canonical face's frame.
    local: Vec

    # All faces containing the point. They define the point's colours.
    faces: frozenset[Face] = field(compare=False)

    # The vertex name, if the point is a vertex of the body.
    vertex: VertexName | None = field(compare=False)

    # The edge, if the point lies strictly inside one.
    edge: BodyEdge | None = field(compare=False)

    # Every (face, local) form of the point.
    forms: tuple[tuple[Face, Vec], ...] = field(compare=False, repr=False)

    def __init__(self, body: Body, face: Face, local: Vec) -> None:
        if not polygon_contains(body.face(face).corners, local):
            raise ValueError(f"local point {local} is outside face {face}")

        sides = body.sides_through(face, local)
        vertex = _corner_name(body, face, local)
        edge = None
        if vertex is not None:
            forms = body.vertex_corners(vertex)
        elif sides:
            (side,) = sides
            edge = body.side_edge(side)
            other = edge.other(side)
            forms = ((face, local), (other.face, edge.transition(side).apply(local)))
        else:
            forms = ((face, local),)
        canonical = min(forms, key=lambda form: (form[0], form[1].x, form[1].y))

        object.__setattr__(self, "body", body)
        object.__setattr__(self, "face", canonical[0])
        object.__setattr__(self, "local", canonical[1])
        object.__setattr__(self, "faces", frozenset(f for f, _ in forms))
        object.__setattr__(self, "vertex", vertex)
        object.__setattr__(self, "edge", edge)
        object.__setattr__(self, "forms", tuple(sorted(set(forms), key=lambda form: (form[0], form[1].x, form[1].y))))

    @classmethod
    def at_vertex(cls, body: Body, name: VertexName) -> SurfacePoint:
        """The vertex with the given name."""
        face, local = body.vertex_corners(name)[0]
        return cls(body, face, local)

    @property
    def kind(self) -> SurfacePointKind:
        if self.vertex is not None:
            return SurfacePointKind.VERTEX
        if self.edge is not None:
            return SurfacePointKind.EDGE
        return SurfacePointKind.FACE

    def locals_in(self, face: Face) -> list[Vec]:
        """Every position of this point in the frame of `face` (one, unless the face is glued to itself here)."""
        return [local for f, local in self.forms if f == face]

    def local_in(self, face: Face) -> Vec:
        """The position of this point in the frame of `face`, which must be one of `self.faces` and hold it once."""
        found = self.locals_in(face)
        if not found:
            raise ValueError(f"{self} does not lie on face {face}")
        if len(found) > 1:
            raise ValueError(f"{self} lies on face {face} {len(found)} times")
        return found[0]

    def __repr__(self) -> str:
        if self.vertex is not None:
            label = f" {self.vertex}"
        elif self.edge is not None:
            label = f" on {'-'.join(sorted(self.edge.names))}"
        else:
            label = ""
        return f"SurfacePoint({self.face}, {self.local!r}{label})"


def _corner_name(body: Body, face: Face, local: Vec) -> VertexName | None:
    f = body.face(face)
    for corner, name in zip(f.corners, f.names, strict=True):
        if corner == local:
            return name
    return None
