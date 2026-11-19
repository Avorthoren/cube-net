# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Validating a template (docs/template_idea.txt, Validation): the checks, in order. The first that fails stops the
rest; it says what to list, and the UI words it.

The checks don't prove that a template is the net of a body, only reject what certainly isn't: every loop segment
must be glued to exactly one other (its counterpart), and the gluing must keep coordinates rational. Faces of one
colour are pieces of one face (docs/template_plan.md, §8.2): no fold between them, all glued together, and glued, one
flat piece of paper.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum

from cube_net.core.geometry import IntersectionKind, Vec, classify_segments
from cube_net.core.template.glued_faces import glue_faces
from cube_net.core.template.template import Fold, Label, LoopVertex, Template

# The fewest faces a valid template has.
MIN_FACES = 4


class ValidationProblem(Enum):
    # 1. Some faces have no colour.
    NO_COLOR = "no color"

    # 2. Some vertices have no label.
    UNLABELLED = "unlabelled"

    # 3. Segments or folds joining a name to itself (`segments`: like "A1-A3").
    SELF_EDGE = "self edge"

    # 4. Loop segments without exactly one counterpart (`names`: like "A-CT").
    NO_COUNTERPART = "no counterpart"

    # 5. Counterparts neither parallel nor perpendicular (`names`).
    NOT_PARALLEL = "not parallel"

    # 6. Counterparts of different lengths (`names`).
    DIFFERENT_LENGTHS = "different lengths"

    # 7. Counterparts running the same way along the loop (`names`).
    SAME_DIRECTION = "same direction"

    # 8. Folds named like a glued pair (`groups`: a cut of the pair, then the folds, like ("A1-B1", "A1-B3")).
    CUT_AND_FOLD = "cut and fold"

    # 9. Folds named the same (`groups`: the folds of each name pair).
    SAME_FOLDS = "same folds"

    # 10. Names whose instances aren't all glued together (`names`: like "A").
    NOT_GLUED = "not glued"

    # 11. Folds with one colour on both sides (`names`: the folds, like "A1-B1"): a fold separates two faces.
    SAME_COLOR_FOLD = "same color fold"

    # 12. Colours whose pieces aren't all glued together (`colors`).
    PIECES_APART = "pieces apart"

    # 13. Fewer than 4 faces (colours: the pieces of one colour are one face).
    TOO_FEW_FACES = "too few faces"

    # 14. Faces that touch themselves: a slit (or a point) inside a face (`names`: the vertices where, like "S2").
    FACE_TOUCHES_ITSELF = "face touches itself"

    # 15. Faces glued from their pieces that aren't one flat piece of paper (`colors`): see `glued_faces`.
    SELF_INTERSECTING = "self intersecting"

    # 16. Names whose indices don't go 1, 2, 3, ... (`names`); the UI offers to reindex them.
    INDEX_GAPS = "index gaps"


@dataclass(frozen=True, slots=True)
class ValidationFailure:
    problem: ValidationProblem

    # The names, name pairs or segments to list, in order along the loop.
    names: tuple[str, ...] = ()

    # Groups of segments to list (checks 8 and 9).
    groups: tuple[tuple[str, ...], ...] = ()

    # How many there are, where nothing is listed (check 1: the faces without a colour).
    count: int = 0

    # The faces to show, by their colours (checks 12 and 15), in the template's order.
    colors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Side:
    """A segment of the loop or a fold: its ends, labelled."""

    start: LoopVertex
    end: LoopVertex

    @property
    def labels(self) -> tuple[Label, Label]:
        assert self.start.label is not None and self.end.label is not None  # check 2 passed
        return self.start.label, self.end.label

    @property
    def names(self) -> frozenset[str]:
        a, b = self.labels
        return frozenset((a.name, b.name))

    @property
    def text(self) -> str:
        a, b = self.labels
        return f"{a}-{b}"

    @property
    def name_text(self) -> str:
        a, b = self.labels
        return f"{a.name}-{b.name}"


def validate(template: Template) -> ValidationFailure | None:
    """The first check that fails, or None if the template is valid. The loop must be closed."""
    if not template.closed:
        raise ValueError("only a closed loop can be validated")
    uncoloured = sum(face.color is None for face in template.faces)
    if uncoloured:
        return ValidationFailure(ValidationProblem.NO_COLOR, count=uncoloured)
    if any(v.label is None for v in template.all_vertices):
        return ValidationFailure(ValidationProblem.UNLABELLED)
    sides = [_Side(template.vertex(a), template.vertex(b)) for a, b in template.loop_sides()]
    folds = [_Side(template.vertex(f.start), template.vertex(f.end)) for f in template.folds]

    selfish = tuple(s.text for s in (*sides, *folds) if len(s.names) == 1)
    if selfish:
        return ValidationFailure(ValidationProblem.SELF_EDGE, selfish)

    pairs: dict[frozenset[str], list[_Side]] = {}
    for side in sides:
        pairs.setdefault(side.names, []).append(side)
    lonely = _first_texts(group for group in pairs.values() if len(group) != 2)
    if lonely:
        return ValidationFailure(ValidationProblem.NO_COUNTERPART, lonely)
    glued = list(pairs.values())

    def failing(test: Callable[[_Side, _Side], bool]) -> tuple[str, ...]:
        return _first_texts(group for group in glued if not test(*group))

    tests: tuple[tuple[ValidationProblem, Callable[[_Side, _Side], bool]], ...] = (
        (ValidationProblem.NOT_PARALLEL, _parallel_or_perpendicular),
        (ValidationProblem.DIFFERENT_LENGTHS, _same_length),
        (ValidationProblem.SAME_DIRECTION, _opposite),
    )
    for problem, test in tests:
        names = failing(test)
        if names:
            return ValidationFailure(problem, names)

    named_like_cuts = tuple(
        (pairs[names][0].text, *(f.text for f in folds if f.names == names))
        for names in _in_order(f.names for f in folds)
        if names in pairs
    )
    if named_like_cuts:
        return ValidationFailure(ValidationProblem.CUT_AND_FOLD, groups=named_like_cuts)

    same_folds = tuple(
        tuple(f.text for f in folds if f.names == names)
        for names in _in_order(f.names for f in folds)
        if sum(f.names == names for f in folds) > 1
    )
    if same_folds:
        return ValidationFailure(ValidationProblem.SAME_FOLDS, groups=same_folds)

    apart = _not_glued(template)
    if apart:
        return ValidationFailure(ValidationProblem.NOT_GLUED, apart)

    colors = {i: face.color for i, face in enumerate(template.faces)}
    one_color = tuple(fold.text for f, fold in zip(template.folds, folds, strict=True) if _same_color(template, f))
    if one_color:
        return ValidationFailure(ValidationProblem.SAME_COLOR_FOLD, one_color)

    gluing = glue_faces(template)
    if gluing.apart:
        return ValidationFailure(ValidationProblem.PIECES_APART, colors=gluing.apart)

    if len(set(colors.values())) < MIN_FACES:
        return ValidationFailure(ValidationProblem.TOO_FEW_FACES)

    touching = _faces_touching_themselves(template)
    if touching:
        return ValidationFailure(ValidationProblem.FACE_TOUCHES_ITSELF, touching)

    if gluing.broken:
        return ValidationFailure(ValidationProblem.SELF_INTERSECTING, colors=gluing.broken)

    gaps = _index_gaps(template)
    if gaps:
        return ValidationFailure(ValidationProblem.INDEX_GAPS, gaps)
    return None


def reindexed(template: Template) -> Template:
    """Every name's indices made 1, 2, 3, ... in the order they were in (A2, A4, A5, A10 -> A1, A2, A3, A4)."""
    by_name: dict[str, list[LoopVertex]] = {}
    for v in template.all_vertices:
        if v.label is not None:
            by_name.setdefault(v.label.name, []).append(v)
    result = template
    for name, vertices in by_name.items():
        for i, v in enumerate(sorted(vertices, key=_index), start=1):
            result = result.with_label(v.id, Label(name, i))
    return result


def _same_color(template: Template, fold: Fold) -> bool:
    """Has the fold one colour on both sides?"""
    sides = [f.color for f in template.faces if f.has_side(fold.start, fold.end) or f.has_side(fold.end, fold.start)]
    return len(sides) == 2 and sides[0] == sides[1]


def _first_texts(groups: Iterable[list[_Side]]) -> tuple[str, ...]:
    """The name pair of each group of sides (as its first side is named)."""
    return tuple(group[0].name_text for group in groups)


def _in_order(items: Iterable[frozenset[str]]) -> list[frozenset[str]]:
    """Each one once, in the order they come."""
    seen: list[frozenset[str]] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _parallel_or_perpendicular(s: _Side, t: _Side) -> bool:
    a, b = s.end.position - s.start.position, t.end.position - t.start.position
    return a.cross(b) == 0 or a.dot(b) == 0


def _same_length(s: _Side, t: _Side) -> bool:
    a, b = s.end.position - s.start.position, t.end.position - t.start.position
    return a.length_squared() == b.length_squared()


def _opposite(s: _Side, t: _Side) -> bool:
    """Along the loop, one goes from A to B, the other from B to A."""
    (a, b), (c, d) = s.labels, t.labels
    return (a.name, b.name) == (d.name, c.name)


def _not_glued(template: Template) -> tuple[str, ...]:
    """The names whose instances the gluing doesn't bring together: two instances are glued directly when a name is
    next to both along the loop (their segments to it are counterparts), or when they're at the same point (the loop
    touches itself there); gluing goes on through chains of those."""
    vertices = template.vertices
    n = len(vertices)
    neighbours = {v.id: {_name(vertices[i - 1]), _name(vertices[(i + 1) % n])} for i, v in enumerate(vertices)}
    neighbours.update({v.id: set() for v in template.fold_vertices})  # one point inside the net: glued to nothing
    by_name: dict[str, list[LoopVertex]] = {}
    for v in template.all_vertices:
        by_name.setdefault(_name(v), []).append(v)
    apart = []
    for name, instances in by_name.items():
        group = {instances[0].id}
        grown = True
        while grown:
            grown = False
            for v in instances:
                if v.id not in group and any(
                    neighbours[v.id] & neighbours[g] or v.position == template.position(g) for g in group
                ):
                    group.add(v.id)
                    grown = True
        if len(group) != len(instances):
            apart.append(name)
    return tuple(apart)


def _faces_touching_themselves(template: Template) -> tuple[str, ...]:
    """The labels of the vertices where a face touches itself (the loop may touch itself, but only between faces: a
    face is a simple polygon, docs/template_plan.md §8.1). In the loop's order."""
    places: set[Vec] = set()
    for face in template.faces:
        corners = face.corners
        n = len(corners)
        sides = [(template.position(corners[i]), template.position(corners[(i + 1) % n])) for i in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                hit = classify_segments(*sides[i], *sides[j])
                if hit.kind is IntersectionKind.DISJOINT:
                    continue
                neighbours = j == i + 1 or (i == 0 and j == n - 1)
                shared = sides[i][1] if j == i + 1 else sides[i][0]
                if neighbours and hit.kind is IntersectionKind.TOUCH and hit.point == shared:
                    continue
                places.update(hit.points)
    return tuple(str(v.label) for v in template.all_vertices if v.position in places and v.label is not None)


def _index_gaps(template: Template) -> tuple[str, ...]:
    by_name: dict[str, list[int]] = {}
    for v in template.all_vertices:
        by_name.setdefault(_name(v), []).append(_index(v))
    return tuple(name for name, indices in by_name.items() if sorted(indices) != list(range(1, len(indices) + 1)))


def _name(v: LoopVertex) -> str:
    assert v.label is not None  # check 2 passed
    return v.label.name


def _index(v: LoopVertex) -> int:
    assert v.label is not None
    return v.label.index
