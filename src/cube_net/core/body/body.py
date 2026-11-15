# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Body`: the surface the net folds into, as polygon faces glued along their sides (docs/template_plan.md, §3).

Every face has its own local frame: its corners, counter-clockwise, in face-local coordinates. Every corner is a
named vertex of the body. Two face sides with the same two vertex names are glued together: they are one edge of the
body. The cube is one body (`cube.py`); a template describes others.

The gluing of each edge is a `Rigid90` (a rotation by k * 90 degrees plus a translation) from one side's face frame to
the other's, so coordinates stay rational in every frame.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from types import MappingProxyType

from cube_net.core.geometry import Rigid90, Vec, on_segment, signed_area

type Face = int
type VertexName = str

# How a colour is written: #RRGGBB, capital letters.
COLOR_PATTERN = re.compile(r"#[0-9A-F]{6}")

# A face's colour when nothing says otherwise.
WHITE = "#FFFFFF"


class BodyError(ValueError):
    """The description of a body is inconsistent."""


@dataclass(frozen=True, slots=True)
class Side:
    """Side `index` of face `face`: from its corner `index` to the next one (counter-clockwise)."""

    face: Face
    index: int


@dataclass(frozen=True, slots=True)
class BodyFace:
    number: Face

    # The corners in the face's local frame, counter-clockwise.
    corners: tuple[Vec, ...]

    # The vertex name of each corner.
    names: tuple[VertexName, ...]

    def side_ends(self, index: int) -> tuple[Vec, Vec]:
        """Where side `index` starts and ends, in the face's frame."""
        return self.corners[index], self.corners[(index + 1) % len(self.corners)]

    def side_names(self, index: int) -> tuple[VertexName, VertexName]:
        return self.names[index], self.names[(index + 1) % len(self.names)]


@dataclass(frozen=True, slots=True, eq=False)
class BodyEdge:
    """An edge of the body: two face sides glued together (two sides of one face, if the face meets itself)."""

    id: int

    # The names of the edge's two vertices.
    names: frozenset[VertexName]

    # The two glued sides; the first one's face frame is the edge's own (its dash pattern is measured there).
    sides: tuple[Side, Side]

    # The faces on its two sides (1 of them if a face is glued to itself).
    faces: frozenset[Face]

    # For each side, the map from its face's frame to the other side's face's frame.
    _maps: Mapping[Side, Rigid90] = field(repr=False)

    def other(self, side: Side) -> Side:
        first, second = self.sides
        return second if side == first else first

    def transition(self, side: Side) -> Rigid90:
        """The map from `side`'s face frame to the other side's face frame. It "unfolds" the face across the edge:
        the edge maps onto the other side, and the rest of the face lands outside the other face, next to it."""
        return self._maps[side]

    def __repr__(self) -> str:
        return f"BodyEdge#{self.id}({'-'.join(sorted(self.names))})"


class Body:
    """Faces and how they're glued, plus where each face goes in the body's starting net. Immutable.

    All checks of the description run once, here, and raise `BodyError` with a readable message. The queries rely on
    them and check nothing.
    """

    def __init__(
        self,
        faces: Mapping[Face, tuple[Sequence[Vec], Sequence[VertexName]]],
        start: Sequence[tuple[Face, Rigid90]],
        colors: Sequence[str] | None = None,
    ) -> None:
        """`faces`: for each face number (1, 2, ...), its corners, counter-clockwise in its own frame, and their names.
        `start`: where each face goes in the starting net (local -> sheet), in the order its vertices get their ids.
        `colors`: each face's default colour ("#RRGGBB"; face k: colors[k - 1]), white if not given.
        """
        self._faces = {n: BodyFace(n, tuple(corners), tuple(names)) for n, (corners, names) in faces.items()}
        _check_faces(self._faces)
        self._edges, self._side_edges = _glue(self._faces)
        self._vertex_corners: dict[VertexName, list[tuple[Face, Vec]]] = {}
        for face in self._faces.values():
            for corner, name in zip(face.corners, face.names, strict=True):
                self._vertex_corners.setdefault(name, []).append((face.number, corner))
        self._angles = _vertex_angles(self._faces)
        self._area = sum((signed_area(f.corners) for f in self._faces.values()), Fraction(0))
        self._start = tuple(start)
        placed = sorted(face for face, _ in self._start)
        if placed != sorted(self._faces):
            raise BodyError(f"the starting net must place every face once, got faces {placed}")
        self._colors = tuple(colors) if colors is not None else (WHITE,) * len(self._faces)
        if len(self._colors) != len(self._faces):
            raise BodyError(f"{len(self._faces)} faces, but {len(self._colors)} colours")
        for color in self._colors:
            if not COLOR_PATTERN.fullmatch(color):
                raise BodyError(f"a colour must be #RRGGBB with capital letters, got {color!r}")

    # --- faces --------------------------------------------------------------------------------------------------------

    @property
    def face_numbers(self) -> tuple[Face, ...]:
        return tuple(sorted(self._faces))

    def face(self, number: Face) -> BodyFace:
        try:
            return self._faces[number]
        except KeyError:
            raise ValueError(f"no such face: {number!r}") from None

    @property
    def area(self) -> Fraction:
        """The area of the whole surface: the sum of its faces' areas."""
        return self._area

    @property
    def colors(self) -> tuple[str, ...]:
        """Each face's default colour, as "#RRGGBB" (face k: colors[k - 1])."""
        return self._colors

    @property
    def start(self) -> tuple[tuple[Face, Rigid90], ...]:
        """Each face's placement (local -> sheet) in the starting net, in build order."""
        return self._start

    # --- vertices -----------------------------------------------------------------------------------------------------

    @property
    def vertex_names(self) -> tuple[VertexName, ...]:
        return tuple(sorted(self._vertex_corners))

    def vertex_corners(self, name: VertexName) -> tuple[tuple[Face, Vec], ...]:
        """Every face corner that is this vertex, as (face, local position)."""
        try:
            return tuple(self._vertex_corners[name])
        except KeyError:
            raise ValueError(f"no such vertex: {name!r}") from None

    def vertex_angle(self, name: VertexName) -> int:
        """The total angle of the faces around a vertex, in degrees: 270 at a cube's corner, 360 where the surface is
        flat (such a vertex can end up inside a net), more at a saddle."""
        try:
            return self._angles[name]
        except KeyError:
            raise ValueError(f"no such vertex: {name!r}") from None

    def vertex_faces(self, name: VertexName) -> frozenset[Face]:
        """The faces meeting at a vertex."""
        return frozenset(face for face, _ in self.vertex_corners(name))

    # --- edges --------------------------------------------------------------------------------------------------------

    @property
    def edges(self) -> tuple[BodyEdge, ...]:
        return self._edges

    def side_edge(self, side: Side) -> BodyEdge:
        """The edge a face side is glued into."""
        return self._side_edges[side]

    def sides_through(self, face: Face, p: Vec) -> list[Side]:
        """The sides of `face` that local point `p` lies on (2 at a corner, 1 inside a side, none inside the face)."""
        f = self.face(face)
        return [Side(face, i) for i in range(len(f.corners)) if on_segment(p, *f.side_ends(i))]

    def side_through(self, face: Face, a: Vec, b: Vec) -> Side | None:
        """The side of `face` the segment a-b (local points of `face`, a != b) lies on, if any."""
        f = self.face(face)
        for i in range(len(f.corners)):
            start, end = f.side_ends(i)
            if on_segment(a, start, end) and on_segment(b, start, end):
                return Side(face, i)
        return None

    def edge_through(self, face: Face, a: Vec, b: Vec) -> BodyEdge | None:
        """The edge the segment a-b (local points of `face`, a != b) lies on, if it lies on one of the face's sides."""
        side = self.side_through(face, a, b)
        return None if side is None else self._side_edges[side]

    def segment_faces(self, face: Face, a: Vec, b: Vec) -> frozenset[Face]:
        """The faces the segment a-b (local points of `face`) belongs to: the 2 of an edge it lies on, or just `face`.
        They give the segment its colours."""
        edge = self.edge_through(face, a, b)
        return edge.faces if edge is not None else frozenset((face,))


def _check_faces(faces: Mapping[Face, BodyFace]) -> None:
    if sorted(faces) != list(range(1, len(faces) + 1)):
        raise BodyError(f"faces must be numbered 1, 2, ..., got {sorted(faces)}")
    for face in faces.values():
        n = len(face.corners)
        if n < 3:
            raise BodyError(f"face {face.number} needs at least 3 corners, got {n}")
        if len(face.names) != n:
            raise BodyError(f"face {face.number} has {n} corners but {len(face.names)} names")
        if len(set(face.corners)) != n:
            raise BodyError(f"face {face.number} has two corners at the same point: {face.corners}")
        if signed_area(face.corners) <= 0:
            raise BodyError(f"the corners of face {face.number} must be counter-clockwise: {face.corners}")
        for i in range(n):
            a, b = face.side_names(i)
            if a == b:
                raise BodyError(f"side {i} of face {face.number} joins vertex {a} to itself")


def _vertex_angles(faces: Mapping[Face, BodyFace]) -> dict[VertexName, int]:
    """The total angle around each vertex. Going around a vertex from face to face is a composition of gluings, each a
    rotation by a multiple of 90 degrees, and it must come back to where it started, so the total is a multiple of 90:
    the sum of the corners' angles, found in floats, is rounded to it, which is exact."""
    totals: dict[VertexName, float] = {}
    for face in faces.values():
        n = len(face.corners)
        for i, (corner, name) in enumerate(zip(face.corners, face.names, strict=True)):
            to_next, to_prev = face.corners[(i + 1) % n] - corner, face.corners[i - 1] - corner
            angle = math.atan2(float(to_next.cross(to_prev)), float(to_next.dot(to_prev))) % (2 * math.pi)
            totals[name] = totals.get(name, 0.0) + math.degrees(angle)
    angles = {}
    for name, total in totals.items():
        angles[name] = 90 * round(total / 90)
        if abs(total - angles[name]) > 1e-6:
            raise BodyError(f"the angles around vertex {name} add up to {total:.3f} degrees, not a multiple of 90")
    return angles


def _glue(faces: Mapping[Face, BodyFace]) -> tuple[tuple[BodyEdge, ...], Mapping[Side, BodyEdge]]:
    """Glue every face side to the other side with the same vertex names."""
    by_names: dict[frozenset[VertexName], list[Side]] = {}
    for face in faces.values():
        for i in range(len(face.corners)):
            by_names.setdefault(frozenset(face.side_names(i)), []).append(Side(face.number, i))
    edges: list[BodyEdge] = []
    side_edges: dict[Side, BodyEdge] = {}
    for names, sides in sorted(by_names.items(), key=lambda item: min((s.face, s.index) for s in item[1])):
        label = "-".join(sorted(names))
        if len(sides) != 2:
            raise BodyError(f"{len(sides)} face sides join vertices {label}, expected 2 (glued together)")
        s, t = sorted(sides, key=lambda side: (side.face, side.index))
        fs, ft = faces[s.face], faces[t.face]
        (a, b), (c, d) = fs.side_names(s.index), ft.side_names(t.index)
        if (a, b) != (d, c):
            raise BodyError(f"the two sides {label} run the same way: one face would have to be turned over")
        s_start, s_end = fs.side_ends(s.index)
        t_start, t_end = ft.side_ends(t.index)
        if (s_end - s_start).length_squared() != (t_end - t_start).length_squared():
            raise BodyError(f"the two sides {label} have different lengths")
        try:
            to_t = Rigid90.from_segments(s_start, s_end, t_end, t_start)
        except ValueError as e:
            raise BodyError(f"the two sides {label} are neither parallel nor perpendicular") from e
        edge = BodyEdge(
            len(edges), names, (s, t), frozenset((s.face, t.face)), MappingProxyType({s: to_t, t: to_t.inverse()})
        )
        edges.append(edge)
        side_edges[s] = side_edges[t] = edge
    return tuple(edges), MappingProxyType(side_edges)
