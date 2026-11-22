# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Faces glued from pieces (docs/template_plan.md, §8.2): the template's faces of one colour are pieces of one face of
the body. `glue_faces` glues each colour's pieces together, in the frame of its basis piece, along the pairs of loop
sides that join two of them (seams: inside the face, not edges), and finds the glued face's boundary: an outer loop
and maybe holes (a ring).

It needs a template whose loop sides all have one counterpart, parallel or perpendicular, of the same length and
running the other way (validation's checks up to 7 passed). It says which colours' pieces aren't all joined, and which
glued faces aren't one flat piece of paper: pieces overlapping, a seam that doesn't fall onto its other side, or the
face touching itself (along a side or at a point) other than where it's glued.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from cube_net.core.geometry import IntersectionKind, Rigid90, Vec, classify_segments, signed_area
from cube_net.core.template.template import Template


@dataclass(frozen=True, slots=True)
class Corner:
    """A corner of a glued face: where it is in the face's frame, and the template's vertex it comes from."""

    position: Vec
    vertex: int


@dataclass(frozen=True, slots=True)
class GluedFace:
    color: str

    # The template's faces (indices) that are its pieces, the basis piece first, the others in the template's order.
    pieces: tuple[int, ...]

    # For each piece: the template sheet -> the face's frame (the basis piece's: the identity).
    frames: tuple[Rigid90, ...]

    # The boundary: the outer loop (counter-clockwise), then the holes (clockwise).
    loops: tuple[tuple[Corner, ...], ...]


@dataclass(frozen=True, slots=True)
class Gluing:
    # Every colour's face, in the order of their first pieces in the template (when nothing is wrong).
    faces: tuple[GluedFace, ...]

    # The colours whose pieces aren't all joined through seams, in the order of their first pieces.
    apart: tuple[str, ...]

    # The colours whose glued face isn't one flat piece of paper (see the module's docstring).
    broken: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Seam:
    """A pair of loop sides joining two pieces of one colour: `side` of piece `piece`, glued to `other_side` of
    `other`; `to_other` maps the template sheet near `side` onto `other_side` (as gluing puts it)."""

    piece: int
    side: tuple[int, int]
    other: int
    other_side: tuple[int, int]
    to_other: Rigid90


def basis_piece(template: Template, pieces: Sequence[int]) -> int:
    """Of a colour's pieces (template face indices), the basis: the one given its colour least recently (the smallest
    number; faces coloured before the counter was kept count as earlier, in the template's order)."""
    return min(pieces, key=lambda i: (template.faces[i].number or 0, i))


def glue_faces(template: Template) -> Gluing:
    """Each colour's face glued from its pieces, in its basis piece's frame."""
    by_color: dict[str, list[int]] = {}
    for i, face in enumerate(template.faces):
        assert face.color is not None  # validation's check 1 passed
        by_color.setdefault(face.color, []).append(i)
    seams = _seams(template)
    faces, apart, broken = [], [], []
    for color, pieces in by_color.items():
        first = basis_piece(template, pieces)
        frames = _frames(first, [s for s in seams if s.piece in pieces])
        if len(frames) != len(pieces):
            apart.append(color)
            continue
        loops = _boundary(template, pieces, frames, [s for s in seams if s.piece in pieces])
        if loops is None:
            broken.append(color)
            continue
        ordered = (first, *(p for p in pieces if p != first))
        faces.append(GluedFace(color, ordered, tuple(frames[p] for p in ordered), loops))
    return Gluing(tuple(faces), tuple(apart), tuple(broken))


def _piece_of_side(template: Template) -> dict[tuple[int, int], int]:
    """The template face each side (loop sides and both ways of the folds) belongs to."""
    owner = {}
    for i, face in enumerate(template.faces):
        for cycle in face.cycles:
            n = len(cycle)
            for k in range(n):
                owner[(cycle[k], cycle[(k + 1) % n])] = i
    return owner


def _seams(template: Template) -> list[_Seam]:
    """Both ways of every pair of loop sides joining two pieces of one colour (different pieces: a face glued to
    itself along a pair has an edge there)."""
    owner = _piece_of_side(template)
    by_names: dict[frozenset[str], list[tuple[int, int]]] = {}
    for a, b in template.all_loop_sides():
        la, lb = template.vertex(a).label, template.vertex(b).label
        assert la is not None and lb is not None  # validation's check 2 passed
        by_names.setdefault(frozenset((la.name, lb.name)), []).append((a, b))
    seams = []
    for pair in by_names.values():
        s, t = pair  # validation's check 4 passed
        p, q = owner[s], owner[t]
        if p == q or template.faces[p].color != template.faces[q].color:
            continue
        pos = template.position
        to_t = Rigid90.from_segments(pos(s[0]), pos(s[1]), pos(t[1]), pos(t[0]))  # checks 5-7 passed: it exists
        seams.append(_Seam(p, s, q, t, to_t))
        seams.append(_Seam(q, t, p, s, to_t.inverse()))
    return seams


def _frames(basis: int, seams: list[_Seam]) -> dict[int, Rigid90]:
    """Each piece reached from the basis through seams: the template sheet -> the face's frame."""
    frames = {basis: Rigid90.identity()}
    queue = [basis]
    while queue:
        piece = queue.pop(0)
        for seam in seams:
            if seam.piece == piece and seam.other not in frames:
                frames[seam.other] = frames[piece] @ seam.to_other.inverse()
                queue.append(seam.other)
    return frames


def _boundary(
    template: Template, pieces: list[int], frames: dict[int, Rigid90], seams: list[_Seam]
) -> tuple[tuple[Corner, ...], ...] | None:
    """The glued face's loops, or None if it isn't one flat piece of paper."""
    for seam in seams:  # every seam must fall onto its other side
        if frames[seam.piece] @ seam.to_other.inverse() != frames[seam.other]:
            return None
    inside = {seam.side for seam in seams}
    starts: dict[Vec, tuple[Corner, Corner]] = {}
    for piece in pieces:
        frame = frames[piece]
        for a, b in (pair for cycle in template.faces[piece].cycles for pair in pairwise((*cycle, cycle[0]))):
            if (a, b) in inside:
                continue
            start = Corner(frame.apply(template.position(a)), a)
            if start.position in starts:  # the face touches itself there (or pieces overlap)
                return None
            starts[start.position] = (start, Corner(frame.apply(template.position(b)), b))
    loops: list[tuple[Corner, ...]] = []
    left = dict(starts)
    while left:
        first = next(iter(left))
        loop: list[Corner] = []
        at = first
        while at in left:
            start, end = left.pop(at)
            loop.append(start)
            at = end.position
        if at != first:
            return None
        loops.append(tuple(loop))
    outer = [loop for loop in loops if signed_area([c.position for c in loop]) > 0]
    if len(outer) != 1 or not _simple(loops):
        return None
    return (outer[0], *(loop for loop in loops if loop is not outer[0]))


def _simple(loops: list[tuple[Corner, ...]]) -> bool:
    """Do the loops' sides meet only where neighbours along a loop meet, at their shared corner?"""
    sides: list[tuple[Vec, Vec]] = []
    for loop in loops:
        n = len(loop)
        sides.extend((loop[k].position, loop[(k + 1) % n].position) for k in range(n))
    for i, s in enumerate(sides):
        for t in sides[i + 1 :]:
            hit = classify_segments(*s, *t)
            if hit.kind is IntersectionKind.DISJOINT:
                continue
            if hit.kind is IntersectionKind.TOUCH and (
                (s[1] == t[0] and hit.point == s[1]) or (s[0] == t[1] and hit.point == s[0])
            ):
                continue  # neighbours along a loop (each point starts one side only: they're the only ones)
            return False
    return True


def aligned_hatches(template: Template) -> Template:
    """The template with every piece's hatch continuing its basis piece's: each piece hatched in its face's frame (the
    basis piece's, tied to the template's grid). It must be valid (`validate` finds no problem)."""
    hatches = [Rigid90.identity()] * len(template.faces)
    for face in glue_faces(template).faces:
        for piece, frame in zip(face.pieces, face.frames, strict=True):
            hatches[piece] = frame
    return template.with_hatches(hatches)
