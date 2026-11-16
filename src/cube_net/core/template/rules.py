# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a template's loop and folds may and may not do (docs/template_idea.txt; docs/template_plan.md, §4.2).

- The loop never crosses or touches itself: two of its segments meet only at the vertex they share.
- A fold is one straight segment from a loop vertex to another (not a neighbour, not one already joined by a fold),
  strictly inside the loop, meeting other folds only at shared ends.
- Everything stays on the template sheet.

Each check takes the template as it would be after a change and the segments the change made or moved, and says what
breaks the rules: a `TemplateRejection` with the segments to flash, or None.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from cube_net.core.geometry import IntersectionKind, Vec, classify_segments, on_segment, polygon_contains, signed_area
from cube_net.core.sheet import TEMPLATE_SHEET_HEIGHT, TEMPLATE_SHEET_WIDTH
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
    """Do the `changed` segments (vertex id pairs: loop sides or folds) of `template` keep to the rules? The loop must
    still go counter-clockwise, and every fold must still be inside it."""
    changed = [_ordered(pair) for pair in changed]
    segments = [_ordered(pair) for pair in (*template.loop_sides(), *((f.start, f.end) for f in template.folds))]
    broken: list[Segment] = []
    for pair in changed:
        if any(_conflict(template, pair, other) for other in segments if other != pair):
            broken.append(_positions(template, pair))
    if broken:
        return TemplateRejection(TemplateProblem.CROSSING, tuple(broken))
    if template.closed:
        if signed_area(template.polygon()) <= 0:
            return TemplateRejection(TemplateProblem.TURNED_OVER, tuple(_positions(template, p) for p in changed))
        outside = [(f.start, f.end) for f in template.folds if not _inside(template, f.start, f.end)]
        if outside:
            return TemplateRejection(TemplateProblem.OUTSIDE_THE_LOOP, tuple(_positions(template, p) for p in outside))
    return None


def fold_problem(template: Template, start: int, end: int) -> TemplateRejection | None:
    """Can a fold join these two vertices at all (before looking at where it goes)?"""
    if start == end or template.are_neighbours(start, end) or template.find_fold(start, end) is not None:
        segment = (template.position(start), template.position(end))
        return TemplateRejection(TemplateProblem.NOT_A_FOLD, () if start == end else (segment,))
    return None


def _conflict(template: Template, s: tuple[int, int], t: tuple[int, int]) -> bool:
    """Do the two segments meet anywhere but at the one vertex they share?"""
    a, b = _positions(template, s)
    c, d = _positions(template, t)
    if a == b or c == d:
        return True
    result = classify_segments(a, b, c, d)
    if result.kind is IntersectionKind.DISJOINT:
        return False
    shared = set(s) & set(t)
    if len(shared) != 1 or result.kind is not IntersectionKind.TOUCH:
        return True
    (vertex,) = shared
    return result.point != template.position(vertex)


def _inside(template: Template, start: int, end: int) -> bool:
    """Is the middle of the segment strictly inside the loop? (If the segment touches the loop nowhere but at its ends,
    then the whole of it is.)"""
    middle = (template.position(start) + template.position(end)) / 2
    polygon = template.polygon()
    n = len(polygon)
    if any(on_segment(middle, polygon[i], polygon[(i + 1) % n]) for i in range(n)):
        return False
    return polygon_contains(polygon, middle)


def _ordered(pair: tuple[int, int]) -> tuple[int, int]:
    a, b = pair
    return (a, b) if a < b else (b, a)


def _positions(template: Template, pair: tuple[int, int]) -> Segment:
    return template.position(pair[0]), template.position(pair[1])
