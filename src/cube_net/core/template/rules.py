# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a template's loop and folds may and may not do (docs/template_idea.txt; docs/template_plan.md, §4.2).

- The loop never crosses itself, the net it draws never overlaps itself, and it's one piece of paper. It may touch
  itself, as a rearranged net in a project may (docs/template_plan.md, §8.1): at a point, or along a segment with the
  net on opposite sides of it (a slit); several vertices may be at one point, each with its own part of the net there.
  But parts of the net meeting only at a point are two pieces: not allowed.
- A fold line goes from a vertex (of the loop, or a fold vertex of another line) to another, straight or through fold
  vertices strictly inside the net (docs/template_plan.md, §8.4); a line of one segment not to a neighbour, a vertex at
  the same point, or one already joined by a fold. A segment leaves a loop vertex into that vertex's sector of the
  net, and meets the loop and the other segments nowhere but at its ends.
- Everything stays on the template sheet.

Each check takes the template as it would be after a change and the segments the change made or moved, and says what
breaks the rules: a `TemplateRejection` with the segments to flash, or None.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from cube_net.core.geometry import (
    IntersectionKind,
    Vec,
    classify_segments,
    on_segment,
    polygon_contains,
    signed_area,
)
from cube_net.core.sheet import TEMPLATE_SHEET_HEIGHT, TEMPLATE_SHEET_WIDTH
from cube_net.core.template.loop_geometry import gaps_at, pieces, vertex_gaps, winding_number
from cube_net.core.template.template import Template

# The fewest vertices a closed loop keeps.
MIN_VERTICES = 6

# The fewest vertices a loop closes with (it then has as many segments).
MIN_VERTICES_TO_CLOSE = 3

type Segment = tuple[Vec, Vec]


class TemplateProblem(Enum):
    # Segments touch or cross where they mustn't.
    CROSSING = "crossing"

    # A point off the template sheet.
    OFF_THE_SHEET = "off the sheet"

    # The loop can't be closed yet: it would have fewer than 3 segments.
    TOO_EARLY_TO_CLOSE = "too early to close"

    # A vertex can't be deleted: the loop would have fewer than 6.
    TOO_FEW_VERTICES = "too few vertices"

    # The net would come apart: parts meeting only at points (it must be one piece of paper).
    APART = "apart"

    # A fold can't join these two vertices: the same one, neighbours, or two joined by a fold already.
    NOT_A_FOLD = "not a fold"

    # A fold outside the loop.
    OUTSIDE_THE_LOOP = "outside the loop"

    # The change would turn the loop inside out.
    TURNED_OVER = "turned over"

    # Another vertex has this label already.
    LABEL_TAKEN = "label taken"


@dataclass(frozen=True, slots=True)
class TemplateRejection:
    problem: TemplateProblem

    # The segments that break the rules (to be shown in black for a moment).
    segments: tuple[Segment, ...] = ()


def on_the_sheet(p: Vec) -> bool:
    return 0 <= p.x <= TEMPLATE_SHEET_WIDTH and 0 <= p.y <= TEMPLATE_SHEET_HEIGHT


def check(template: Template, changed: Iterable[tuple[int, int]]) -> TemplateRejection | None:
    """Does `template` keep to the rules, now that the `changed` segments (vertex id pairs: loop sides or folds) were
    made or moved? The segments to flash are those of the changed ones that break a rule (or all that do, if none of
    the changed ones does)."""
    changed_pairs = {_ordered(pair) for pair in changed}
    broken = _loop_problems(template)
    if not broken and template.closed:
        if signed_area(template.polygon()) <= 0:
            return TemplateRejection(TemplateProblem.TURNED_OVER, _shown(template, changed_pairs, changed_pairs))
        if pieces(template) != 1:
            return TemplateRejection(TemplateProblem.APART, _shown(template, changed_pairs, changed_pairs))
        holes = _hole_problems(template)
        if holes:
            return TemplateRejection(TemplateProblem.CROSSING, _shown(template, holes, changed_pairs))
        outside, crossing = _fold_problems(template)
        if crossing or outside:
            # Both sides of every conflict: what changed, and the folds it runs into (all was fine before the change).
            problem = TemplateProblem.CROSSING if crossing else TemplateProblem.OUTSIDE_THE_LOOP
            involved = crossing | outside
            return TemplateRejection(problem, _shown(template, involved, involved))
        return None
    if broken:
        return TemplateRejection(TemplateProblem.CROSSING, _shown(template, broken, changed_pairs))
    return None


def fold_problem(template: Template, start: int, end: int) -> TemplateRejection | None:
    """Can a fold join these two vertices at all (before looking at where it goes)?"""
    if (
        start == end
        or template.position(start) == template.position(end)
        or template.are_neighbours(start, end)
        or template.find_fold(start, end) is not None
    ):
        segment = (template.position(start), template.position(end))
        return TemplateRejection(TemplateProblem.NOT_A_FOLD, () if start == end else (segment,))
    return None


def _loop_problems(template: Template) -> set[tuple[int, int]]:
    """The loop's sides that break its rules: no side of zero length, no two crossing, none going along another the
    same way; and once it's closed, where sides meet (at a vertex, at a point, along a part they share), the net on
    every side of the point is there once at most (`loop_geometry`). While it's open, which side the net will be on
    isn't known: closing it checks that."""
    sides = template.loop_sides()
    bad: set[tuple[int, int]] = set()
    for side in sides:
        a, b = _positions(template, side)
        if a == b:
            bad.add(_ordered(side))
    if bad:
        return bad
    contacts: set[Vec] = set()
    for i, s in enumerate(sides):
        a, b = _positions(template, s)
        for t in sides[i + 1 :]:
            c, d = _positions(template, t)
            hit = classify_segments(a, b, c, d)
            if hit.kind is IntersectionKind.CROSSING:
                bad.update((_ordered(s), _ordered(t)))
            elif hit.kind is IntersectionKind.TOUCH:
                contacts.add(hit.point)
            elif hit.kind is IntersectionKind.OVERLAP:
                if (b - a).dot(d - c) > 0:  # the same way: the net would be on the same side of both
                    bad.update((_ordered(s), _ordered(t)))
                contacts.update((hit.points[0], hit.points[1]))
    if bad or not template.closed:
        return bad
    for q in contacts:
        for gap in gaps_at(template, q):
            if gap.winding not in (0, 1):
                bad.update(_ordered(ray.side) for ray in (*gap.start, *gap.end))
    return bad


def _fold_problems(template: Template) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    """Folds outside the loop, and folds that meet a side or another fold where they mustn't. A fold leaves each of its
    ends into the net, by a gap next to that vertex (`vertex_gaps`: other vertices may be at the same point), and meets
    the loop and the other folds nowhere else (another fold may start at the same point)."""
    outside: set[tuple[int, int]] = set()
    crossing: set[tuple[int, int]] = set()
    loop_sides = template.all_loop_sides()
    segments = [_ordered(side) for side in loop_sides] + [_ordered((f.start, f.end)) for f in template.folds]
    loop_positions = {v.position for v in template.vertices} | {
        v.position for h in template.holes if h.closed for v in h.vertices
    }
    strictly_inside = {
        v.id: v.position not in loop_positions
        and not any(on_segment(v.position, *_positions(template, side)) for side in loop_sides)
        and on_the_net(template, v.position)
        for v in template.fold_vertices
    }
    shared = {v.position for v in template.fold_vertices}
    for fold in template.folds:
        pair = _ordered((fold.start, fold.end))
        a, b = template.position(fold.start), template.position(fold.end)
        if a == b:
            crossing.add(pair)
            continue
        for vertex, direction in ((fold.start, b - a), (fold.end, a - b)):
            if vertex in strictly_inside:
                if not strictly_inside[vertex]:
                    outside.add(pair)
            elif template.hole_of(vertex) is not None:
                if _in_a_hole(template, (a + b) / 2):  # from a hole's vertex into the hole
                    outside.add(pair)
            elif not any(gap.contains(direction) for gap in vertex_gaps(template, vertex)):
                outside.add(pair)
        for other in segments:
            if other == pair:
                continue
            c, d = _positions(template, other)
            hit = classify_segments(a, b, c, d)
            if hit.kind is IntersectionKind.DISJOINT:
                continue
            if hit.kind is not IntersectionKind.TOUCH or hit.point not in (a, b):
                crossing.update((pair, other))
            elif hit.point in shared and not set(pair) & set(other):
                crossing.update((pair, other))  # at a fold vertex's point, but not at that vertex: not allowed
    if len(shared) != len(template.fold_vertices) or shared & loop_positions:
        crossing.update(
            _ordered((f.start, f.end)) for f in template.folds for v in (f.start, f.end) if template.is_fold_vertex(v)
        )  # two vertices at one point, one of them a fold vertex
    return outside, crossing - outside


def on_the_net(template: Template, p: Vec) -> bool:
    """Is `p` (on no side) inside the outer loop and in no closed hole?"""
    return winding_number(template, p) == 1 and not _in_a_hole(template, p)


def _in_a_hole(template: Template, p: Vec) -> bool:
    return any(polygon_contains([v.position for v in h.vertices], p) for h in template.holes if h.closed)


def _hole_problems(template: Template) -> set[tuple[int, int]]:
    """The holes' sides that break their rules (docs/template_plan.md, §8.5): a hole's vertices on the net (not on a
    side, a fold or another vertex), its sides touching nothing but its own neighbours along it (no other loop), and
    crossing folds only while it's drawn (once it's closed, the crossings are its vertices); a closed hole may not go
    round another."""
    bad: set[tuple[int, int]] = set()
    outer = template.loop_sides()
    folds = [(f.start, f.end) for f in template.folds]
    others_positions = {v.position for v in template.all_vertices}
    for index, hole in enumerate(template.holes):
        sides = hole.sides()
        own = {v.id for v in hole.vertices}
        other_loops = [*outer, *(s for i, h in enumerate(template.holes) if i != index for s in h.sides())]
        for v in hole.vertices:
            at_fold_end = any(v.id in f for f in folds)
            elsewhere = [u for u in template.all_vertices if u.position == v.position and u.id != v.id]
            on_something = any(
                on_segment(v.position, *_positions(template, s)) and v.id not in s for s in [*other_loops, *folds]
            )
            if elsewhere or on_something or not (at_fold_end or on_the_net_ignoring(template, v.position, index)):
                bad.update(_ordered(s) for s in sides if v.id in s)
                if not sides:
                    bad.add((v.id, v.id))
        for i, s in enumerate(sides):
            a, b = _positions(template, s)
            if a == b:
                bad.add(_ordered(s))
                continue
            for t in sides[i + 1 :]:
                hit = classify_segments(a, b, *_positions(template, t))
                if hit.kind is IntersectionKind.DISJOINT:
                    continue
                shared = set(s) & set(t)
                if hit.kind is IntersectionKind.TOUCH and shared and hit.point == template.position(shared.pop()):
                    continue
                bad.update((_ordered(s), _ordered(t)))
            for t in other_loops:
                if classify_segments(a, b, *_positions(template, t)).kind is not IntersectionKind.DISJOINT:
                    bad.update((_ordered(s), _ordered(t)))
            for t in folds:
                hit = classify_segments(a, b, *_positions(template, t))
                if hit.kind is IntersectionKind.DISJOINT:
                    continue
                if not hole.closed and hit.kind is IntersectionKind.CROSSING and hit.point not in others_positions:
                    continue  # it will be a vertex of the hole when it's closed
                if hole.closed and hit.kind is IntersectionKind.TOUCH and set(s) & set(t) & own:
                    continue  # a fold ends at one of its vertices
                bad.update((_ordered(s), _ordered(t)))
        if hole.closed:
            polygon = [v.position for v in hole.vertices]
            for i, h in enumerate(template.holes):
                if i != index and h.vertices and polygon_contains(polygon, h.vertices[0].position):
                    bad.update(_ordered(s) for s in sides)  # it goes round another hole
    return bad


def on_the_net_ignoring(template: Template, p: Vec, hole: int) -> bool:
    """Is `p` inside the outer loop and in no closed hole but hole `hole`?"""
    if winding_number(template, p) != 1:
        return False
    return not any(
        polygon_contains([v.position for v in h.vertices], p)
        for i, h in enumerate(template.holes)
        if h.closed and i != hole
    )


def _shown(template: Template, broken: set[tuple[int, int]], changed: set[tuple[int, int]]) -> tuple[Segment, ...]:
    """The broken segments to flash: the changed ones among them, or all of them."""
    pairs = (broken & changed) or broken
    return tuple(_positions(template, pair) for pair in sorted(pairs))


def _ordered(pair: tuple[int, int]) -> tuple[int, int]:
    a, b = pair
    return (a, b) if a < b else (b, a)


def _positions(template: Template, pair: tuple[int, int]) -> Segment:
    return template.position(pair[0]), template.position(pair[1])
