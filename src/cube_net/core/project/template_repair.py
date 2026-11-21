# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Repairing a template whose numbers are longer than the application supports (`MAX_NUMBER_DIGITS`): a file made by
hand, or before the limit. `template_long_vertices` finds them; `repair_template` moves them to the nearest points with
short numbers, by at most a step of 10^-1000 or so.

A template is the body's net: sides with the same pair of names are copies of each other, turned by a multiple of 90
degrees and shifted. Moved vertices must stay copies of each other, and the body must stay the same body:
- A vertex goes to the nearest point of a fine grid (`grid_step`): one fine enough that every short shift between copies
  is on it, so a vertex and its copies land on copies of each other again (rounding to the grid commutes with turning by
  90 degrees and with such shifts).
- A vertex that is no corner of the body anywhere (every vertex of its name, every copy, lies where its loop goes
  straight on: in the middle of a body edge, like where a hole's side crosses a fold) stays on its straight run: it
  keeps its place along the run, rounded, between the run's ends (moved first). On the grid it could leave the line,
  and the body would get a corner there. A fold through it bends a little: a fold line may.
- A fold vertex inside a face has no copies: it just goes to the grid. So do the origin and a hatch's shift, if long.
- But first: if the whole template was moved by a long shift (by hand), moving it all back by one tiny shift makes
  every number short, and nothing else changes.

What can't be kept goes: the history (its states have the same long numbers). The result is checked as a whole: the
drawing rules, every pair of segments meeting as before, the faces adding up, the validation (if the template was
valid, it must stay valid), every number short. Anything wrong is a `RepairError`, and nothing is repaired.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace
from fractions import Fraction
from itertools import combinations
from math import lcm

from cube_net.core.geometry import MAX_NUMBER_DIGITS, Rigid90, Vec, classify_segments, long_number
from cube_net.core.history import History
from cube_net.core.origin import Origin
from cube_net.core.project.longest_number import longest_number
from cube_net.core.project.repair import RepairError
from cube_net.core.project.template_codec import TemplateDocument
from cube_net.core.template import LoopVertex, Template, TemplateSnapshot, ValidationStatus, validate
from cube_net.core.template.rules import check, faces_consistent

# How much finer than the short numbers' denominators the grid is.
FINE = 10**1000


def needs_template_repair(document: TemplateDocument) -> bool:
    return longest_number(document) > MAX_NUMBER_DIGITS


def template_long_vertices(document: TemplateDocument) -> list[LoopVertex]:
    return [v for v in document.state.template.all_vertices if long_number(v.position) is not None]


def template_vertex_names(vertices: Sequence[LoopVertex]) -> list[str]:
    """The vertices' labels ("A1"), in their order (a vertex without one: where it is, "(1.500, 3.667)")."""
    names = [str(v.label) if v.label is not None else _place(v.position) for v in vertices]
    return sorted(set(names))


def repair_template(document: TemplateDocument) -> TemplateDocument:
    """The template with every vertex that has a number too long moved to the nearest short point that keeps it what
    it is (see the module's docstring). Raises `RepairError` if the result isn't a good template."""
    try:
        repaired = _repaired(document)
    except RepairError:
        raise
    except Exception as e:  # anything the template's own checks find
        raise RepairError(str(e)) from e
    if needs_template_repair(repaired):
        raise RepairError("numbers too long remain")
    return repaired


def _repaired(document: TemplateDocument) -> TemplateDocument:
    template = document.state.template
    step = grid_step(template)
    shift = _shift(template, step)
    if shift is not None:  # the hatches and the origin go with it: they look as they did
        moved = {v.id: v.position + shift for v in template.all_vertices}
        hatches = [Rigid90(f.hatch.k, f.hatch.t - f.hatch.apply_vector(shift)) for f in template.faces]
        origin = document.state.origin
        origin = Origin(origin.position + shift, None if origin.point is None else origin.point + shift, origin.name)
    else:
        moved = _moved(template, step)
        hatches = [f.hatch for f in template.faces]
        origin = document.state.origin
    after = _with_positions(template, moved)
    faces = tuple(replace(f, hatch=_short_hatch(h, step)) for f, h in zip(after.faces, hatches, strict=True))
    after = replace(after, faces=faces)
    _check(template, after)
    valid = template.complete and validate(template) is None
    if valid and validate(after) is not None:
        raise RepairError("the template isn't valid any more")
    status = document.validation if valid else ValidationStatus.UNDEFINED  # (one a hand edit made invalid: unchecked)
    origin = _short_origin(origin, step)
    return TemplateDocument(TemplateSnapshot(after, origin), History(), document.style, status)


def _shift(template: Template, step: Fraction) -> Vec | None:
    """One tiny shift of every vertex that makes them all short, if there is one (the whole template was moved by a
    long shift, by hand): nothing changes but where it is."""
    first = next((v.position for v in template.all_vertices if long_number(v.position) is not None), None)
    if first is None:
        return None
    shift = _on_grid(first, step) - first
    return shift if all(long_number(v.position + shift) is None for v in template.all_vertices) else None


def _moved(template: Template, step: Fraction) -> dict[int, Vec]:
    """Every vertex with a number too long, and each one of a straight run whose end moved, where it goes."""
    straight_runs = _straight_only(template)
    moved: dict[int, Vec] = {}
    for vertex in template.all_vertices:
        if vertex.id not in straight_runs and long_number(vertex.position) is not None:
            moved[vertex.id] = _on_grid(vertex.position, step)
    for vertex_id, (start, end) in straight_runs.items():
        position = template.position(vertex_id)
        a, b = template.position(start), template.position(end)
        if long_number(position) is None and start not in moved and end not in moved:
            continue
        d = b - a
        t = (position - a).dot(d) / d.length_squared()
        k = min(max(round(t * FINE), 1), FINE - 1)
        new_a, new_b = moved.get(start, a), moved.get(end, b)
        moved[vertex_id] = new_a + (new_b - new_a) * Fraction(k, FINE)
    return moved


def grid_step(template: Template) -> Fraction:
    """The grid the moved vertices go to: 10^-1000 of the step of the template's short numbers (every short number,
    so every shift between copies, is on it); 10^-1000 alone if their denominators are too many to bring together."""
    short = [v.position for v in template.all_vertices if long_number(v.position) is None]
    denominators = [c.denominator for p in short for c in (p.x, p.y)]
    common = lcm(*denominators) if denominators else 1
    return Fraction(1, FINE * (common if common < FINE else 1))


def _straight_only(template: Template) -> dict[int, tuple[int, int]]:
    """The loop's (and the holes') vertices that are no corner of the body anywhere: where every vertex of their name
    lies where its loop goes straight on (an unnamed one: where it does itself). Each with its straight run's ends."""
    cycles = [[v.id for v in template.vertices]] if template.closed else []
    cycles += [[v.id for v in hole.vertices] for hole in template.holes if hole.closed]
    straight: dict[int, tuple[int, int]] = {}
    for ids in cycles:
        n = len(ids)
        flat = [_goes_straight(template, ids[i - 1], ids[i], ids[(i + 1) % n]) for i in range(n)]
        for i in range(n):
            if not flat[i]:
                continue
            before = next(ids[(i - j) % n] for j in range(1, n) if not flat[(i - j) % n])
            after = next(ids[(i + j) % n] for j in range(1, n) if not flat[(i + j) % n])
            straight[ids[i]] = (before, after)
    corners_named = {v.label.name for v in template.all_vertices if v.label is not None and v.id not in straight}
    return {
        vertex_id: run
        for vertex_id, run in straight.items()
        if (label := template.vertex(vertex_id).label) is None or label.name not in corners_named
    }


def _goes_straight(template: Template, previous: int, vertex: int, following: int) -> bool:
    a, b, c = template.position(previous), template.position(vertex), template.position(following)
    return (b - a).cross(c - b) == 0 and (b - a).dot(c - b) > 0


def _with_positions(template: Template, moved: dict[int, Vec]) -> Template:
    def placed(vertices: Iterable[LoopVertex]) -> tuple[LoopVertex, ...]:
        return tuple(replace(v, position=moved.get(v.id, v.position)) for v in vertices)

    holes = tuple(replace(hole, vertices=placed(hole.vertices)) for hole in template.holes)
    return replace(
        template, vertices=placed(template.vertices), holes=holes, fold_vertices=placed(template.fold_vertices)
    )


def _check(before: Template, after: Template) -> None:
    """The drawing rules, the faces adding up, and every pair of segments meeting as it did."""
    segments = [*before.all_loop_sides(), *((f.start, f.end) for f in before.folds)]
    if after.closed and check(after, segments) is not None:
        raise RepairError("the template would break the drawing rules")
    if after.closed and not faces_consistent(after):
        raise RepairError("the template's faces wouldn't add up")
    for (a, b), (c, d) in combinations(segments, 2):
        was = classify_segments(before.position(a), before.position(b), before.position(c), before.position(d))
        now = classify_segments(after.position(a), after.position(b), after.position(c), after.position(d))
        if now.kind is not was.kind:
            raise RepairError(f"segments {a}-{b} and {c}-{d} would meet otherwise")


def _on_grid(p: Vec, step: Fraction) -> Vec:
    return Vec(round(p.x / step) * step, round(p.y / step) * step)


def _short_hatch(hatch: Rigid90, step: Fraction) -> Rigid90:
    """A hatch's shift on the grid, if it's long (it's only how the hatch is drawn)."""
    return hatch if long_number(hatch.t) is None else Rigid90(hatch.k, _on_grid(hatch.t, step))


def _short_origin(origin: Origin, step: Fraction) -> Origin:
    if long_number(origin.position) is None and (origin.point is None or long_number(origin.point) is None):
        return origin
    point = None if origin.point is None else _on_grid(origin.point, step)
    return Origin(_on_grid(origin.position, step), point, origin.name)


def _place(p: Vec) -> str:
    return f"({float(p.x):.3f}, {float(p.y):.3f})"
