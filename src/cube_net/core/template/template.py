# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`Template`: a body described by one of its nets (docs/template_idea.txt; docs/template_plan.md, §4.1).

A closed loop of vertices, fold lines between them (chords of the loop) and the faces they divide the loop into,
each with a colour. Vertices get labels: the name of the body's vertex they are an image of, and an index.

Immutable: every change gives a new `Template`, so the editor's history can keep them as its states. The changes here
only keep the structure consistent; whether a change is allowed geometrically is for `rules.py` to say.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import pairwise

from cube_net.core.geometry import Vec, on_segment, polygon_contains, signed_area

# A label's name: 1 or 2 capital Latin letters.
NAME_PATTERN = re.compile(r"[A-Z]{1,2}")

# A label's index: 1 to 99.
MIN_INDEX = 1

MAX_INDEX = 99


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

    def has_side(self, a: int, b: int) -> bool:
        """Does the face go straight from corner `a` to corner `b` (counter-clockwise)?"""
        n = len(self.corners)
        return any(self.corners[i] == a and self.corners[(i + 1) % n] == b for i in range(n))


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

    # --- queries ------------------------------------------------------------------------------------------------------

    def vertex(self, vertex_id: int) -> LoopVertex:
        for v in self.vertices:
            if v.id == vertex_id:
                return v
        raise ValueError(f"no vertex with id {vertex_id}")

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
        """Are the two vertices next to each other along the loop?"""
        return any({a, b} == set(side) for side in self.loop_sides())

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
        return next((v for v in self.vertices if v.label == label), None)

    def first_free_index(self, name: str) -> int:
        """The smallest index no vertex named `name` has."""
        taken = {v.label.index for v in self.vertices if v.label is not None and v.label.name == name}
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
        """A new vertex at `position` on the loop's side from `a` to `b` (neighbours, in the loop's direction)."""
        if (a, b) not in self.loop_sides():
            raise ValueError(f"no loop side from {a} to {b}")
        new = LoopVertex(self.next_id, position)
        i = self.index_of(a) + 1
        faces = tuple(_insert_corner(face, a, b, new.id) for face in self.faces)
        vertices = (*self.vertices[:i], new, *self.vertices[i:])
        return replace(self, vertices=vertices, faces=faces, next_id=self.next_id + 1)

    def with_vertex_moved(self, vertex_id: int, position: Vec) -> Template:
        return self._with_vertex(replace(self.vertex(vertex_id), position=position))

    def with_label(self, vertex_id: int, label: Label | None) -> Template:
        return self._with_vertex(replace(self.vertex(vertex_id), label=label))

    def without_vertex(self, vertex_id: int) -> Template:
        """The loop without a vertex (its two sides become one), and without the folds that end at it."""
        template = self
        for fold in self.folds_at(vertex_id):
            template = template.without_fold(fold)
        faces = tuple(
            replace(face, corners=tuple(c for c in face.corners if c != vertex_id)) for face in template.faces
        )
        vertices = tuple(v for v in template.vertices if v.id != vertex_id)
        return replace(template, vertices=vertices, faces=faces)

    def with_fold(self, start: int, end: int) -> Template:
        """A fold from `start` to `end`: it divides the face both lie on into two, each in that face's colour."""
        face = next((f for f in self.faces if start in f.corners and end in f.corners), None)
        if face is None:
            raise ValueError(f"no face has both {start} and {end}")
        corners = list(face.corners)
        k = corners.index(start)
        corners = corners[k:] + corners[:k]  # from `start`
        m = corners.index(end)
        right = TemplateFace((*corners[: m + 1],), face.color)  # start ... end, then back along the fold
        left = TemplateFace((*corners[m:], corners[0]), face.color)  # end ... start, then along the fold
        i = self.faces.index(face)
        faces = (*self.faces[:i], right, left, *self.faces[i + 1 :])
        return replace(self, folds=(*self.folds, Fold(start, end)), faces=faces)

    def without_fold(self, fold: Fold) -> Template:
        """The two faces on its sides become one, in the colour of the one on its left (seen from where it starts)."""
        left = next(f for f in self.faces if f.has_side(fold.start, fold.end))
        right = next(f for f in self.faces if f.has_side(fold.end, fold.start))
        merged = TemplateFace(_merge(left.corners, right.corners, fold), left.color)
        i = min(self.faces.index(left), self.faces.index(right))
        faces = [f for f in self.faces if f is not left and f is not right]
        faces.insert(i, merged)
        return replace(self, folds=tuple(f for f in self.folds if f != fold), faces=tuple(faces))

    def with_face_color(self, face_index: int, color: str) -> Template:
        faces = list(self.faces)
        faces[face_index] = replace(faces[face_index], color=color)
        return replace(self, faces=tuple(faces))

    def face_at(self, p: Vec) -> int | None:
        """The index of the face `p` lies strictly inside (not on a fold or the loop), if any."""
        for i, face in enumerate(self.faces):
            polygon = self.face_polygon(face)
            n = len(polygon)
            on_border = any(on_segment(p, polygon[j], polygon[(j + 1) % n]) for j in range(n))
            if not on_border and polygon_contains(polygon, p):
                return i
        return None

    def _with_vertex(self, new: LoopVertex) -> Template:
        return replace(self, vertices=tuple(new if v.id == new.id else v for v in self.vertices))


def template_area(template: Template) -> Fraction | None:
    """The area of the net the template draws (None while the loop is open)."""
    return signed_area(template.polygon()) if template.closed else None


def _insert_corner(face: TemplateFace, a: int, b: int, new: int) -> TemplateFace:
    """The face with `new` between its corners `a` and `b`, if it goes from one straight to the other."""
    n = len(face.corners)
    for i in range(n):
        if face.corners[i] == a and face.corners[(i + 1) % n] == b:
            return replace(face, corners=(*face.corners[: i + 1], new, *face.corners[i + 1 :]))
    return face


def _merge(left: tuple[int, ...], right: tuple[int, ...], fold: Fold) -> tuple[int, ...]:
    """One face from the two on the sides of `fold`: around `left` from the fold's end to its start, then around
    `right` from its start back to (just before) its end."""
    k = left.index(fold.end)
    around_left = left[k:] + left[:k]  # end ... start
    m = right.index(fold.start)
    around_right = right[m:] + right[:m]  # start ... end
    return (*around_left, *around_right[1:-1])
