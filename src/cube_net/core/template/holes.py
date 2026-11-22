# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Holes in a template: inner loops (docs/template_plan.md, §8.5).

A hole is drawn as the outer loop is, a point at a time, and closed at its first vertex. Closed, it runs clockwise
(the net on its left), and cuts the folds it crosses: each crossing becomes a vertex of the hole and the end of what's
left of the fold; the folds' parts inside it go, with their fold vertices.

Once a template has holes, its faces are worked out again from its segments after every change of its folds or holes
(`faces_from_graph`), instead of dividing and merging them as `Template` does without holes: a fold may join a hole to
the outer loop (a ring stops being one), a hole may lie inside a face (a ring). A face keeps the colour, number and
hatch of the face it was part of (a point inside it says which); where faces merge, the one on the left of the deleted
fold, as without holes.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace
from fractions import Fraction
from itertools import pairwise

from cube_net.core.geometry import IntersectionKind, Vec, classify_segments, on_segment, polygon_contains, signed_area
from cube_net.core.template.template import Fold, Hole, LoopVertex, Template, TemplateFace


def with_hole_point(template: Template, p: Vec) -> Template:
    """A new point of the hole being drawn (or the first point of a new hole)."""
    new = LoopVertex(template.next_id, p)
    if template.drawing_hole:
        last = template.holes[-1]
        holes = (*template.holes[:-1], replace(last, vertices=(*last.vertices, new)))
    else:
        holes = (*template.holes, Hole((new,)))
    return replace(template, holes=holes, next_id=template.next_id + 1)


def closed_hole(template: Template) -> Template:
    """The hole being drawn closed: clockwise, the folds it crosses cut there (their parts inside it gone), the faces
    worked out again."""
    hole = template.holes[-1]
    vertices = hole.vertices
    if signed_area([v.position for v in vertices]) > 0:
        vertices = (vertices[0], *reversed(vertices[1:]))
    hole = Hole(vertices, closed=True)
    after = replace(template, holes=(*template.holes[:-1], hole))
    after = _cut_folds(after, len(after.holes) - 1)
    return _refaced(after, template)


def recut(after: Template, before: Template, index: int) -> Template:
    """`after` (`before` with a vertex of the closed hole `index` moved): the folds its sides now cross cut there, as
    when it was closed (their parts and fold vertices now inside it gone), the faces worked out again."""
    return _refaced(_cut_folds(after, index), before)


def without_hole_vertex(template: Template, vertex_id: int) -> Template:
    """A hole without a vertex (its two sides become one), or without the whole hole if it had 3; the folds that end
    at the vertices that go, go too (and what's left hanging)."""
    index = template.hole_of(vertex_id)
    assert index is not None
    hole = template.holes[index]
    gone = {vertex_id} if len(hole.vertices) > 3 else {v.id for v in hole.vertices}
    if len(hole.vertices) > 3:
        holes = list(template.holes)
        holes[index] = replace(hole, vertices=tuple(v for v in hole.vertices if v.id != vertex_id))
    else:
        holes = [h for i, h in enumerate(template.holes) if i != index]
    folds = tuple(f for f in template.folds if f.start not in gone and f.end not in gone)
    after = _without_hanging(replace(template, holes=tuple(holes), folds=folds))
    return _refaced(after, template)


def with_fold_line_refaced(template: Template, start: int, points: Sequence[Vec], end: int) -> Template:
    """`Template.with_fold_line` where there are holes, or where the face it divides touches itself: the faces worked
    out again (both sides keep the face's colour)."""
    ids = list(range(template.next_id, template.next_id + len(points)))
    chain = [start, *ids, end]
    after = replace(
        template,
        folds=(*template.folds, *(Fold(a, b) for a, b in pairwise(chain))),
        fold_vertices=(*template.fold_vertices, *(LoopVertex(i, p) for i, p in zip(ids, points, strict=True))),
        next_id=template.next_id + len(points),
    )
    return _refaced(after, template)


def without_fold_refaced(template: Template, fold: Fold) -> Template:
    """`Template.without_fold` where there are holes, or where the fold has one face on both sides (what's beyond it
    then floats, and goes): the faces worked out again, the merged face in the colour of the one on the fold's left."""
    left = next((f for f in template.faces if f.has_side(fold.start, fold.end)), None)
    after = _without_hanging(replace(template, folds=tuple(f for f in template.folds if f != fold)))
    return _refaced(after, template, prefer=left)


def _without_hanging(template: Template) -> Template:
    """Only the folds that `attached` keeps, and the fold vertices they reach (faces aside)."""
    folds = attached(template)
    used = {v for f in folds for v in (f.start, f.end)}
    kept = tuple(v for v in template.fold_vertices if v.id in used)
    return replace(template, folds=tuple(folds), fold_vertices=kept)


def attached(template: Template) -> list[Fold]:
    """The folds that stay after a deletion (docs/template_plan.md §8.4): without the parts that reach neither the loop
    nor a hole. Such a part either floats inside a face, touching nothing but itself, or hangs on by one segment (a
    segment hanging from a vertex, or a loop of folds and the segment it hangs on by): the face on both sides of that
    segment is the same, so it can't fold. A deletion leaves them so (drawing always starts at a vertex that's there),
    and they go, one after another, with whatever hangs on them."""
    anchors = {v.id for v in template.vertices} | {v.id for h in template.holes for v in h.vertices}
    folds = list(template.folds)
    while True:
        part = _cut_off(folds, anchors)
        if not part:
            return folds
        folds = [f for f in folds if f not in part]


def _cut_off(folds: list[Fold], anchors: set[int]) -> set[Fold]:
    """A part of `folds` that doesn't reach `anchors`: a floating one, or one and the segment it hangs on by (empty if
    there's none)."""
    for fold in folds:
        reach = _reached(folds, fold.start)
        if not reach & anchors:
            return {f for f in folds if f.start in reach}
        rest = [f for f in folds if f != fold]
        for end in (fold.start, fold.end):
            reach = _reached(rest, end)
            if not reach & anchors:
                return {fold} | {f for f in rest if f.start in reach}
    return set()


def _reached(folds: list[Fold], start: int) -> set[int]:
    """The vertices `start` reaches through `folds` (itself included)."""
    reached = {start}
    grown = True
    while grown:
        grown = False
        for f in folds:
            if (f.start in reached) != (f.end in reached):
                reached.update((f.start, f.end))
                grown = True
    return reached


def _cut_folds(template: Template, index: int) -> Template:
    """The closed hole `index` cuts the folds it crosses: new vertices of the hole at the crossings, the folds divided
    there, their parts inside the hole gone, fold vertices inside it gone."""
    hole = template.holes[index]
    vertices = list(hole.vertices)
    folds = list(template.folds)
    next_id = template.next_id
    k = 0
    while k < len(vertices):
        a, b = vertices[k], vertices[(k + 1) % len(vertices)]
        hits: list[tuple[Fraction, Vec, Fold]] = []
        for fold in folds:
            hit = classify_segments(a.position, b.position, template.position(fold.start), template.position(fold.end))
            if hit.kind is IntersectionKind.CROSSING:
                d = b.position - a.position
                hits.append(((hit.point - a.position).dot(d) / d.length_squared(), hit.point, fold))
        if not hits:
            k += 1
            continue
        _, point, fold = min(hits, key=lambda h: h[0])
        new = LoopVertex(next_id, point)
        next_id += 1
        vertices.insert(k + 1, new)
        i = folds.index(fold)
        folds[i : i + 1] = [Fold(fold.start, new.id), Fold(new.id, fold.end)]
        template = replace(template, holes=_with_hole(template, index, vertices), next_id=next_id)
        k += 1  # the next side starts at the new vertex
    template = replace(template, holes=_with_hole(template, index, vertices), folds=tuple(folds), next_id=next_id)
    inside = [v.position for v in vertices]

    def in_hole(p: Vec) -> bool:
        return polygon_contains(inside, p) and not _on_polygon(inside, p)

    # Divided at the crossings, a fold's parts are inside the hole or outside it: their middles say which.
    kept_folds = tuple(
        f for f in template.folds if not in_hole((template.position(f.start) + template.position(f.end)) / 2)
    )
    kept_vertices = tuple(v for v in template.fold_vertices if not in_hole(v.position))
    return _without_hanging(replace(template, folds=kept_folds, fold_vertices=kept_vertices))


def _with_hole(template: Template, index: int, vertices: list[LoopVertex]) -> tuple[Hole, ...]:
    holes = list(template.holes)
    holes[index] = replace(holes[index], vertices=tuple(vertices))
    return tuple(holes)


def _on_polygon(polygon: list[Vec], p: Vec) -> bool:
    n = len(polygon)
    return any(on_segment(p, polygon[i], polygon[(i + 1) % n]) for i in range(n))


def faces_from_graph(template: Template) -> list[tuple[tuple[int, ...], list[tuple[int, ...]]]]:
    """The faces the loops and the folds divide the net into: each its outer cycle (counter-clockwise) and the cycles
    of the holes inside it that touch nothing else (clockwise)."""
    loop_sides = set(template.all_loop_sides())
    edges: dict[int, set[int]] = {}
    for a, b in [*loop_sides, *((f.start, f.end) for f in template.folds)]:
        edges.setdefault(a, set()).add(b)
        edges.setdefault(b, set()).add(a)

    def order(a: int, b: int) -> tuple[float, int]:
        """Where the segment from `a` to `b` lies round `a`, counter-clockwise. Two loop sides may leave `a` the same
        way (a slit: the loop comes back along itself): of them, the one with the net on its right comes first, the
        slit (outside the net) between them."""
        d = template.position(b) - template.position(a)
        net_on_the_right = (b, a) in loop_sides
        return round(math.atan2(float(d.y), float(d.x)), 12), 0 if net_on_the_right else 1

    around = {v: sorted(ns, key=lambda n: order(v, n)) for v, ns in edges.items()}
    seen: set[tuple[int, int]] = set()
    outer: list[tuple[int, ...]] = []
    inner: list[tuple[int, ...]] = []
    for start in sorted((a, b) for a, ns in edges.items() for b in ns):
        if start in seen:
            continue
        cycle: list[int] = []
        u, v = start
        net_side = True
        while (u, v) not in seen:
            seen.add((u, v))
            cycle.append(u)
            if (v, u) in loop_sides:  # against a loop's direction: outside the net, or inside a hole
                net_side = False
            ns = around[v]
            w = ns[(ns.index(u) - 1) % len(ns)]  # the next one clockwise from the way back: the face on the left
            u, v = v, w
        if not net_side:
            continue
        area = signed_area([template.position(c) for c in cycle])
        (outer if area > 0 else inner).append(tuple(cycle))
    result: list[tuple[tuple[int, ...], list[tuple[int, ...]]]] = [(c, []) for c in outer]
    for island in inner:
        # A point just to the left of its first side: outside it, in the face around it (a point of the island itself
        # is in the faces inside it too: the smallest of them would take it as its own hole).
        side_start, side_end = template.position(island[0]), template.position(island[1])
        along = side_end - side_start
        p = (side_start + side_end) / 2 + Vec(-along.y, along.x) * Fraction(1, 1_000_000)
        containing = [
            (signed_area(poly), i)
            for i, (c, _) in enumerate(result)
            if polygon_contains(poly := [template.position(x) for x in c], p)
        ]
        _, i = min(containing)
        result[i][1].append(island)
    return result


def _refaced(after: Template, before: Template, prefer: TemplateFace | None = None) -> Template:
    """`after` with its faces worked out again, each with the colour (number, hatch) of the face of `before` a point
    inside it lies in (`prefer`, if a point of it lies in it: a merged face takes the left one's)."""
    faces = []
    for corners, holes in faces_from_graph(after):
        samples = _inner_points(after, corners)
        old = None
        if prefer is not None and any(_contains(before, prefer, p) for p in samples):
            old = prefer
        for p in samples:
            if old is not None:
                break
            i = before.face_at(p)
            old = before.faces[i] if i is not None else None
        face = TemplateFace(corners, holes=tuple(holes))
        if old is not None:
            face = replace(face, color=old.color, number=old.number, hatch=old.hatch)
        faces.append(face)
    return replace(after, faces=tuple(faces))


def _contains(template: Template, face: TemplateFace, p: Vec) -> bool:
    i = template.face_at(p)
    return i is not None and template.faces[i] == face


def _inner_points(template: Template, corners: tuple[int, ...]) -> list[Vec]:
    """Points just inside the face: to the left of the middle of each of its outer sides."""
    points = []
    n = len(corners)
    for i in range(n):
        a, b = template.position(corners[i]), template.position(corners[(i + 1) % n])
        d = b - a
        points.append((a + b) / 2 + Vec(-d.y, d.x) * Fraction(1, 1_000_000))
    return points
