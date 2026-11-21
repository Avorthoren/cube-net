# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Repairing a template whose numbers are too long (a file edited by hand, or made before the limit)."""

from dataclasses import replace
from fractions import Fraction as F

import pytest

import cube_net.core.geometry.long_numbers as long_numbers
from cube_net.core.geometry import Vec
from cube_net.core.history import History
from cube_net.core.project import TemplateDocument
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.project.repair import RepairError
from cube_net.core.project.template_repair import (
    needs_template_repair,
    repair_template,
    template_long_vertices,
    template_vertex_names,
)
from cube_net.core.template import LoopVertex, Template, TemplateEditor, validate

# A third, written with 2200 digits: too long, but nowhere near any other point.
THIRD = F(10**2200 // 3, 10**2200)

# A hair: moved by it, a point gets a number too long, but nothing visible changes.
HAIR = F(1, 10**2200)


def moved(template: Template, by: dict[int, Vec]) -> Template:
    """The template with vertices moved by hand (as a file can be edited)."""

    def placed(vertices: tuple[LoopVertex, ...]) -> tuple[LoopVertex, ...]:
        return tuple(replace(v, position=v.position + by.get(v.id, Vec(0, 0))) for v in vertices)

    holes = tuple(replace(h, vertices=placed(h.vertices)) for h in template.holes)
    return replace(
        template, vertices=placed(template.vertices), holes=holes, fold_vertices=placed(template.fold_vertices)
    )


def edited(by: dict[int, Vec]) -> TemplateDocument:
    """The built-in Cube with a hole (a valid template), edited by hand."""
    document = cube_with_a_hole()
    state = replace(document.state, template=moved(document.state.template, by))
    return replace(document, state=state, history=History())


def test_a_vertex_nudged_by_hand_goes_back() -> None:
    template = cube_with_a_hole().state.template
    corner = template.vertices[0]
    document = edited({corner.id: Vec(HAIR, 0)})
    assert needs_template_repair(document)
    assert [v.id for v in template_long_vertices(document)] == [corner.id]
    assert template_vertex_names(template_long_vertices(document)) == [str(corner.label)]
    repaired = repair_template(document)
    assert repaired.state.template == template  # back on the grid: exactly where it was
    assert repaired.history.done_count == 0 and validate(repaired.state.template) is None


def test_the_whole_template_moved_by_hand_by_a_long_shift() -> None:
    template = cube_with_a_hole().state.template
    document = edited({v.id: Vec(THIRD, THIRD / 7) for v in template.all_vertices})
    assert len(template_long_vertices(document)) == len(template.all_vertices)
    repaired = repair_template(document)
    assert not needs_template_repair(repaired) and validate(repaired.state.template) is None
    before = [v.position for v in document.state.template.all_vertices]
    after = [v.position for v in repaired.state.template.all_vertices]
    shifts = {b - a for a, b in zip(before, after, strict=True)}
    assert len(shifts) == 1  # one shift of everything: its shape is just as it was
    (shift,) = shifts
    assert abs(float(shift.x)) < 1e-300 and abs(float(shift.y)) < 1e-300


def test_where_a_holes_side_crosses_a_fold_stays_on_the_side() -> None:
    """Made with the limit lifted: the hole's corner and its crossing with the fold have numbers too long. The corner
    goes to the grid; the crossing stays on the hole's side (the fold bends there instead)."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(long_numbers, "MAX_NUMBER_DIGITS", 10**9)
        editor = TemplateEditor()
        pillow = [Vec(10, 10), Vec(11, 10), Vec(12, 10), Vec(12, 11), Vec(11, 11), Vec(10, 11)]
        for p in [*pillow, pillow[0]]:
            assert editor.add_point(p) is None
        assert editor.add_fold(1, 4) is None  # x = 11
        for p in [Vec(F(21, 2), F(21, 2)), Vec(F(23, 2), 10 + THIRD), Vec(F(23, 2), F(41, 4)), Vec(F(21, 2), F(21, 2))]:
            assert editor.add_hole_point(p) is None
    document = TemplateDocument(editor.snapshot(), editor.history)
    assert needs_template_repair(document)
    repaired = repair_template(document)
    assert not needs_template_repair(repaired)
    hole = repaired.state.template.holes[0]
    positions = [v.position for v in hole.vertices]
    crossings = [i for i, p in enumerate(positions) if p.x == 11]
    assert len(crossings) == 2
    for i in crossings:
        a, b, c = positions[i - 1], positions[i], positions[(i + 1) % len(positions)]
        assert (b - a).cross(c - b) == 0  # still straight on the hole's side


def test_two_points_a_hair_apart_cant_be_repaired() -> None:
    """On the grid they'd fall onto each other."""
    template = cube_with_a_hole().state.template
    first, second = template.vertices[0], template.vertices[1]
    near = second.position - first.position
    document = edited({second.id: Vec(HAIR, 0) - near * (1 - HAIR)})  # a hair from the first one
    with pytest.raises(RepairError):
        repair_template(document)


def test_the_built_in_template_needs_nothing() -> None:
    document = cube_with_a_hole()
    assert not needs_template_repair(document) and not template_long_vertices(document)
