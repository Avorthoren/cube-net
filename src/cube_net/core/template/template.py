# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Template`: a body described by one of its nets (docs/template_idea.txt; docs/template_plan.md, §4.1).

A closed loop of vertices, fold lines and the faces they divide the loop into, each with a colour. A fold line goes
from a vertex to a vertex (of the loop, or of another fold line) through points inside the loop, its *fold vertices*;
it's kept as its segments (`folds`). Vertices get labels: the name of the body's vertex they are an image of, and an
index (docs/template_plan.md, §8.4).

Immutable: every change gives a new `Template`, so the editor's history can keep them as its states. The changes here
only keep the structure consistent; whether a change is allowed geometrically is for `rules.py` to say.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import pairwise

from cube_net.core.geometry import Rigid90, Vec, on_segment, polygon_contains, signed_area

# A label's name: 1 or 2 capital Latin letters.
NAME_PATTERN = re.compile(r"[A-Z]{1,2}")

# A label's index: 1 to 99.
MIN_INDEX = 1

MAX_INDEX = 99

# A hatch tied to the template's grid.
UNTURNED = Rigid90.identity()


@dataclass(frozen=True, slots=True, order=True)
class Label:
    """Which vertex of the body a loop vertex is an image of (`name`), and which image (`index`), like A_2."""

    name: str
    index: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not NAME_PATTERN.fullmatch(self.name):
            raise ValueError(f"a name is 1 or 2 capital Latin letters, got {self.name!r}")
        if not isinstance(self.index, int) or not MIN_INDEX <= self.index <= MAX_INDEX:
            raise ValueError(f"an index is from {MIN_INDEX} to {MAX_INDEX}, got {self.index!r}")

    def __str__(self) -> str:
        return f"{self.name}{self.index}"


@dataclass(frozen=True, slots=True)
class LoopVertex:
    id: int
    position: Vec
    label: Label | None = None


@dataclass(frozen=True, slots=True)
class Fold:
    """A fold line from the vertex with id `start` to the one with id `end` (the way it was drawn)."""

    start: int
    end: int

    def joins(self, a: int, b: int) -> bool:
        return {self.start, self.end} == {a, b}


@dataclass(frozen=True, slots=True)
class TemplateFace:
    # The ids of its corners, counter-clockwise.
    corners: tuple[int, ...]

    # As "#RRGGBB"; None until it's given one (it can't be taken away then: white is a colour too).
    color: str | None = None

    # The template's colour counter when the face was last given a colour (None: not since the counter was kept).
    # Of the pieces of one colour, the one with the smallest number is the basis (docs/template_plan.md, §8.2).
    number: int | None = None

    # How its hatch lies: the template sheet -> the frame where the hatch is tied to the grid. The identity (tied to
    # the template's grid) until a Validate makes it continue the basis piece's hatch.
    hatch: Rigid90 = UNTURNED

    # The holes inside it that touch nothing else (a face that is a ring): each a cycle of corners, clockwise.
    holes: tuple[tuple[int, ...], ...] = ()

    @property
    def cycles(self) -> tuple[tuple[int, ...], ...]:
        """Its outer cycle, then its holes'."""
        return (self.corners, *self.holes)

    def has_side(self, a: int, b: int) -> bool:
        """Does the face go straight from corner `a` to corner `b` (along its outer cycle or a hole's)?"""
        for cycle in self.cycles:
            n = len(cycle)
            if any(cycle[i] == a and cycle[(i + 1) % n] == b for i in range(n)):
                return True
        return False


@dataclass(frozen=True, slots=True)
class Hole:
    """An inner loop (docs/template_plan.md, §8.5): clockwise once it's closed, so that the net is on its left."""

    vertices: tuple[LoopVertex, ...] = ()
    closed: bool = False

    def sides(self) -> list[tuple[int, int]]:
        ids = [v.id for v in self.vertices]
        sides = list(pairwise(ids))
        if self.closed:
            sides.append((ids[-1], ids[0]))
        return sides


@dataclass(frozen=True, slots=True)
class Template:
    # The loop's vertices, in order; counter-clockwise once it's closed.
    vertices: tuple[LoopVertex, ...] = ()

    closed: bool = False

    folds: tuple[Fold, ...] = ()

    # The parts the folds divide the closed loop into (none until it's closed).
    faces: tuple[TemplateFace, ...] = ()

    # The id the next new vertex gets (ids are never reused).
    next_id: int = 0

    # The colour counter: the number the next face given a colour gets.
    next_number: int = 1

    # The vertices of fold lines inside the loop (not on it), in the order they were made.
    fold_vertices: tuple[LoopVertex, ...] = ()

    # The inner loops, in the order they were drawn; the last may be still open (being drawn).
    holes: tuple[Hole, ...] = ()

    # --- queries ------------------------------------------------------------------------------------------------------

    def vertex(self, vertex_id: int) -> LoopVertex:
        """A vertex of the loop, of a hole, or a fold vertex."""
        for v in self.all_vertices:
            if v.id == vertex_id:
                return v
        raise ValueError(f"no vertex with id {vertex_id}")

    @property
    def all_vertices(self) -> tuple[LoopVertex, ...]:
        """The loop's vertices, then the holes', then the fold vertices."""
        return (*self.vertices, *(v for hole in self.holes for v in hole.vertices), *self.fold_vertices)

    @property
    def drawing_hole(self) -> bool:
        """Is a hole being drawn (the last one still open)?"""
        return bool(self.holes) and not self.holes[-1].closed

    @property
    def complete(self) -> bool:
        """The loop closed and no hole being drawn: what validation needs."""
        return self.closed and not self.drawing_hole

    def hole_of(self, vertex_id: int) -> int | None:
        """The index of the hole the vertex belongs to, if it's a hole's."""
        return next((i for i, h in enumerate(self.holes) if any(v.id == vertex_id for v in h.vertices)), None)

    def hole_sides(self) -> list[tuple[int, int]]:
        """The sides of the closed holes, hole after hole."""
        return [side for hole in self.holes if hole.closed for side in hole.sides()]

    def all_loop_sides(self) -> list[tuple[int, int]]:
        """The outer loop's sides, then the closed holes'."""
        return [*self.loop_sides(), *self.hole_sides()]

    def is_fold_vertex(self, vertex_id: int) -> bool:
        return any(v.id == vertex_id for v in self.fold_vertices)

    def index_of(self, vertex_id: int) -> int:
        """Where the vertex is along the loop."""
        for i, v in enumerate(self.vertices):
            if v.id == vertex_id:
                return i
        raise ValueError(f"no vertex with id {vertex_id}")

    def position(self, vertex_id: int) -> Vec:
        return self.vertex(vertex_id).position

    def loop_sides(self) -> list[tuple[int, int]]:
        """The loop's segments as (from, to) vertex ids, in order (the closing one too, once it's closed)."""
        ids = [v.id for v in self.vertices]
        sides = list(pairwise(ids))
        if self.closed:
            sides.append((ids[-1], ids[0]))
        return sides

    def are_neighbours(self, a: int, b: int) -> bool:
        """Are the two vertices next to each other along the loop (or a hole)?"""
        return any({a, b} == set(side) for side in self.all_loop_sides())

    def polygon(self) -> list[Vec]:
        return [v.position for v in self.vertices]

    def face_polygon(self, face: TemplateFace) -> list[Vec]:
        return [self.position(i) for i in face.corners]

    def folds_at(self, vertex_id: int) -> list[Fold]:
        return [f for f in self.folds if vertex_id in (f.start, f.end)]

    def find_fold(self, a: int, b: int) -> Fold | None:
        return next((f for f in self.folds if f.joins(a, b)), None)

    def label_owner(self, label: Label) -> LoopVertex | None:
        """The vertex with this label, if any."""
        return next((v for v in self.all_vertices if v.label == label), None)

    def first_free_index(self, name: str) -> int:
        """The smallest index no vertex named `name` has."""
        taken = {v.label.index for v in self.all_vertices if v.label is not None and v.label.name == name}
        return next(i for i in range(MIN_INDEX, MAX_INDEX + 2) if i not in taken)

    # --- changes ------------------------------------------------------------------------------------------------------

    def with_vertex_appended(self, position: Vec) -> Template:
        """One more vertex at the open end of the loop."""
        if self.closed:
            raise ValueError("the loop is closed")
        new = LoopVertex(self.next_id, position)
        return replace(self, vertices=(*self.vertices, new), next_id=self.next_id + 1)

    def without_last_vertex(self) -> Template:
        if self.closed or not self.vertices:
            raise ValueError("no open end to take a vertex from")
        return replace(self, vertices=self.vertices[:-1])

    def closed_loop(self) -> Template:
        """The loop closed (its last vertex joined to its first), counter-clockwise, as one white face."""
        if self.closed or len(self.vertices) < 3:
            raise ValueError("an open loop of at least 3 vertices is needed")
        vertices = self.vertices
        if signed_area([v.position for v in vertices]) < 0:
            vertices = (vertices[0], *reversed(vertices[1:]))
        face = TemplateFace(tuple(v.id for v in vertices))
        return replace(self, vertices=vertices, closed=True, faces=(face,))

    def with_vertex_inserted(self, a: int, b: int, position: Vec) -> Template:
        """A new vertex at `position` on the side from `a` to `b` of the loop or a hole (in its direction)."""
        if (a, b) not in self.all_loop_sides():
            raise ValueError(f"no loop side from {a} to {b}")
        new = LoopVertex(self.next_id, position)
        faces = tuple(_insert_corner(face, a, b, new.id) for face in self.faces)
        hole = self.hole_of(a)
        if hole is not None:
            vertices = self.holes[hole].vertices
            i = next(k for k, v in enumerate(vertices) if v.id == a) + 1
            changed = replace(self.holes[hole], vertices=(*vertices[:i], new, *vertices[i:]))
            holes = (*self.holes[:hole], changed, *self.holes[hole + 1 :])
            return replace(self, holes=holes, faces=faces, next_id=self.next_id + 1)
        i = self.index_of(a) + 1
        vertices = (*self.vertices[:i], new, *self.vertices[i:])
        return replace(self, vertices=vertices, faces=faces, next_id=self.next_id + 1)

    def with_vertex_moved(self, vertex_id: int, position: Vec) -> Template:
        return self._with_vertex(replace(self.vertex(vertex_id), position=position))

    def with_label(self, vertex_id: int, label: Label | None) -> Template:
        return self._with_vertex(replace(self.vertex(vertex_id), label=label))

    def without_vertex(self, vertex_id: int) -> Template:
        """The loop without a vertex (its two sides become one), and without the folds that end at it (and those left
        hanging then), and without a face it leaves with nothing (two corners: its fold goes too). A fold vertex
        between two segments: they become one, as the loop's sides do (`with_fold_vertex_joined`), unless that one would
        lie on a fold or a side of the loop (the face between them would close up to nothing); otherwise, and where
        more segments meet: without the folds at it, and those left hanging."""
        if self.hole_of(vertex_id) is not None:
            from cube_net.core.template.holes import without_hole_vertex

            return without_hole_vertex(self, vertex_id)
        if self.is_fold_vertex(vertex_id) and len(self.folds_at(vertex_id)) == 2:
            a, b = (f.start if f.end == vertex_id else f.end for f in self.folds_at(vertex_id))
            if self.find_fold(a, b) is None and not self.are_neighbours(a, b):
                return self.with_fold_vertex_joined(vertex_id)
            # Joined, they'd lie on a fold or a side of the loop: the face between closes up to nothing. So the
            # segments go (as deleting one of them would have it: the rest is left hanging).
        template = self
        for fold in self.folds_at(vertex_id):
            if fold in template.folds:
                template = template.without_fold(fold)
        if self.is_fold_vertex(vertex_id):
            return template._without_hanging()
        faces = tuple(
            replace(face, corners=tuple(c for c in face.corners if c != vertex_id)) for face in template.faces
        )
        vertices = tuple(v for v in template.vertices if v.id != vertex_id)
        return replace(template, vertices=vertices, faces=faces)._without_empty_faces()

    def with_fold_vertex_joined(self, vertex_id: int) -> Template:
        """Without a fold vertex between two segments: they become one, from the first's other end to the second's (in
        the line's direction, where the two go one way); the faces just lose that corner."""
        first, second = self.folds_at(vertex_id)
        a = first.start if first.end == vertex_id else first.end
        b = second.end if second.start == vertex_id else second.start
        if first.start == vertex_id and second.end == vertex_id:  # drawn the other way: keep that way
            a, b = b, a
        joined = Fold(a, b)
        folds = tuple(joined if f == first else f for f in self.folds if f != second)
        faces = tuple(
            replace(
                face,
                corners=tuple(c for c in face.corners if c != vertex_id),
                holes=tuple(tuple(c for c in cycle if c != vertex_id) for cycle in face.holes),
            )
            for face in self.faces
        )
        fold_vertices = tuple(v for v in self.fold_vertices if v.id != vertex_id)
        return replace(self, folds=folds, faces=faces, fold_vertices=fold_vertices)

    def _without_empty_faces(self) -> Template:
        """Without the faces a deleted vertex reduced to nothing: two corners left, joined by the loop's new side and
        by a fold, which goes too (the side is the loop's now); then without what that leaves hanging."""
        empty = [f for f in self.faces if len(f.corners) < 3]
        if not empty:
            return self
        gone = {frozenset(f.corners) for f in empty}
        folds = tuple(f for f in self.folds if frozenset((f.start, f.end)) not in gone)
        faces = tuple(f for f in self.faces if len(f.corners) >= 3)
        return replace(self, folds=folds, faces=faces)._without_hanging()

    def with_fold(self, start: int, end: int) -> Template:
        """A fold of one segment from `start` to `end` (see `with_fold_line`)."""
        return self.with_fold_line(start, (), end)

    def with_fold_line(self, start: int, points: Sequence[Vec], end: int) -> Template:
        """A fold line from vertex `start` through new fold vertices at `points` to vertex `end`: it divides the face it
        goes through into two, each in that face's colour (and with its number and hatch)."""
        if self.holes:
            from cube_net.core.template.holes import with_fold_line_among_holes

            return with_fold_line_among_holes(self, start, points, end)
        ids = list(range(self.next_id, self.next_id + len(points)))
        chain = [start, *ids, end]
        positions = [self.position(start), *points, self.position(end)]
        inside = self.face_at((positions[0] + positions[1]) / 2)
        candidates = [f for f in self.faces if start in f.corners and end in f.corners]
        face = self.faces[inside] if inside is not None and self.faces[inside] in candidates else None
        if face is None:
            face = next(iter(candidates), None)
        if face is None:
            raise ValueError(f"no face has both {start} and {end}")
        corners = list(face.corners)
        k = corners.index(start)
        corners = corners[k:] + corners[:k]  # from `start`
        m = corners.index(end)
        right = replace(face, corners=(*corners[: m + 1], *reversed(ids)))  # start ... end, then back along the line
        left = replace(face, corners=(*corners[m:], corners[0], *ids))  # end ... start, then along the line
        i = self.faces.index(face)
        faces = (*self.faces[:i], right, left, *self.faces[i + 1 :])
        folds = (*self.folds, *(Fold(a, b) for a, b in pairwise(chain)))
        new = tuple(LoopVertex(i, p) for i, p in zip(ids, points, strict=True))
        return replace(
            self,
            folds=folds,
            faces=faces,
            fold_vertices=(*self.fold_vertices, *new),
            next_id=self.next_id + len(points),
        )

    def with_fold_vertex_inserted(self, fold: Fold, position: Vec) -> Template:
        """A new fold vertex at `position` on `fold`: its two parts keep its direction (in faces' holes too)."""
        new = LoopVertex(self.next_id, position)
        folds = tuple(
            part for f in self.folds for part in ((Fold(f.start, new.id), Fold(new.id, f.end)) if f == fold else (f,))
        )
        faces = tuple(
            _insert_corner(_insert_corner(face, fold.start, fold.end, new.id), fold.end, fold.start, new.id)
            for face in self.faces
        )
        return replace(
            self, folds=folds, faces=faces, fold_vertices=(*self.fold_vertices, new), next_id=self.next_id + 1
        )

    def without_fold(self, fold: Fold) -> Template:
        """The two faces on its sides become one, in the colour of the one on its left (seen from where it starts)."""
        if self.holes:
            from cube_net.core.template.holes import without_fold_among_holes

            return without_fold_among_holes(self, fold)
        left = next(f for f in self.faces if f.has_side(fold.start, fold.end))
        right = next(f for f in self.faces if f.has_side(fold.end, fold.start))
        merged = replace(left, corners=_merge(left.corners, right.corners, fold))
        i = min(self.faces.index(left), self.faces.index(right))
        faces = [f for f in self.faces if f is not left and f is not right]
        faces.insert(i, merged)
        return replace(self, folds=tuple(f for f in self.folds if f != fold), faces=tuple(faces))._without_hanging()

    def _without_hanging(self) -> Template:
        """Without the fold segments left hanging (an end at a fold vertex no other segment reaches), one after another,
        and without fold vertices that no segment reaches."""
        template = self
        while True:
            degree = {v.id: len(template.folds_at(v.id)) for v in template.fold_vertices}
            hanging = next((v for v, n in degree.items() if n == 1), None)
            if hanging is None:
                break
            (fold,) = template.folds_at(hanging)
            faces = tuple(_without_spike(face, hanging) for face in template.faces)
            template = replace(template, folds=tuple(f for f in template.folds if f != fold), faces=faces)
        kept = tuple(v for v in template.fold_vertices if template.folds_at(v.id))
        return replace(template, fold_vertices=kept) if kept != template.fold_vertices else template

    def with_face_color(self, face_index: int, color: str) -> Template:
        """The face in `color` (even the one it has), numbered by the counter (which goes on), its hatch tied to the
        grid again."""
        faces = list(self.faces)
        faces[face_index] = replace(faces[face_index], color=color, number=self.next_number, hatch=Rigid90.identity())
        return replace(self, faces=tuple(faces), next_number=self.next_number + 1)

    def with_hatches(self, hatches: Sequence[Rigid90]) -> Template:
        """Every face's hatch as given (in the faces' order)."""
        faces = tuple(replace(f, hatch=h) for f, h in zip(self.faces, hatches, strict=True))
        return replace(self, faces=faces)

    def face_at(self, p: Vec) -> int | None:
        """The index of the face `p` lies strictly inside (not on a fold or the loop), if any."""
        for i, face in enumerate(self.faces):
            cycles = [[self.position(c) for c in cycle] for cycle in face.cycles]
            on_border = any(
                on_segment(p, cycle[j], cycle[(j + 1) % len(cycle)]) for cycle in cycles for j in range(len(cycle))
            )
            if not on_border and polygon_contains(cycles[0], p) and not any(polygon_contains(h, p) for h in cycles[1:]):
                return i
        return None

    def _with_vertex(self, new: LoopVertex) -> Template:
        if self.is_fold_vertex(new.id):
            return replace(self, fold_vertices=tuple(new if v.id == new.id else v for v in self.fold_vertices))
        hole = self.hole_of(new.id)
        if hole is not None:
            vertices = tuple(new if v.id == new.id else v for v in self.holes[hole].vertices)
            holes = (*self.holes[:hole], replace(self.holes[hole], vertices=vertices), *self.holes[hole + 1 :])
            return replace(self, holes=holes)
        return replace(self, vertices=tuple(new if v.id == new.id else v for v in self.vertices))


def template_area(template: Template) -> Fraction | None:
    """The area of the net the template draws (None while the loop is open): its holes' don't count."""
    if not template.closed:
        return None
    holes = sum(
        (signed_area([v.position for v in h.vertices]) for h in template.holes if h.closed), Fraction(0)
    )  # holes run clockwise: negative
    return signed_area(template.polygon()) + holes


def _insert_corner(face: TemplateFace, a: int, b: int, new: int) -> TemplateFace:
    """The face with `new` between its corners `a` and `b`, if it goes from one straight to the other (along its outer
    cycle or a hole's)."""
    cycles = list(face.cycles)
    for k, cycle in enumerate(cycles):
        n = len(cycle)
        for i in range(n):
            if cycle[i] == a and cycle[(i + 1) % n] == b:
                cycles[k] = (*cycle[: i + 1], new, *cycle[i + 1 :])
                return replace(face, corners=cycles[0], holes=tuple(cycles[1:]))
    return face


def _without_spike(face: TemplateFace, tip: int) -> TemplateFace:
    """The face without the hanging segment that ends at `tip` (its corners go ..., p, tip, p, ...: one p stays)."""
    corners = face.corners
    n = len(corners)
    for i in range(n):
        if corners[i] == tip and corners[i - 1] == corners[(i + 1) % n]:
            gone = {i, (i + 1) % n}
            return replace(face, corners=tuple(c for j, c in enumerate(corners) if j not in gone))
    return face


def _merge(left: tuple[int, ...], right: tuple[int, ...], fold: Fold) -> tuple[int, ...]:
    """One face from the two on the sides of `fold`: around `left` from the fold's end to its start, then around
    `right` from its start back to (just before) its end."""
    k = left.index(fold.end)
    around_left = left[k:] + left[:k]  # end ... start
    m = right.index(fold.start)
    around_right = right[m:] + right[:m]  # start ... end
    return (*around_left, *around_right[1:-1])
