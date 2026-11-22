# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The scripts of Help -> Help's Template tab: the built-in Cube with a hole (the torus, `cube_with_a_hole`) made from
nothing, its points clicked where the template has them.

1. `DRAW_LOOP`: the outer boundary loop, fast (2 points a second), closed on its first vertex.
2. `FOLDS_AND_HOLE`, from where `DRAW_LOOP` ends (`loop_start`), with the instrument panel (`PANEL_SHOWN`): Draw hole
   clicked, the inner loop, then every fold line (a click on a vertex, then on another), one click every ~667 ms.
3. `COLORS_AND_LABELS`, from where `FOLDS_AND_HOLE` ends (`folds_start`): both pieces of the dark green face get its
   colour (in the colour window, its code clicked, selected with Ctrl+A and pasted over), then the images of the body's
   vertex S get their labels: S1, S2, S3.
4. `VALIDATING`, from the template with everything but the label of H1 (`validate_start`), with the instrument panel:
   Validate says some vertices have no label; H1 gets its label; Validate again finds nothing wrong.
"""

from dataclasses import replace
from fractions import Fraction as F
from functools import cache

from PyQt6.QtCore import QSize, Qt

from cube_net.core.geometry import Box, Vec
from cube_net.core.history import History
from cube_net.core.project import TemplateDocument
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.template import LoopVertex, Template, TemplateFace, TemplateSnapshot, ValidationStatus
from cube_net.ui.help.demo.steps import (
    COLOR_CODE,
    DRAW_HOLE,
    VALIDATE,
    DoubleClick,
    Keys,
    Move,
    Paste,
    Point,
    RightClick,
    Step,
    ToItem,
    ToWidget,
    Type,
    Wait,
    click,
)
from cube_net.ui.sheet.sheet_context_menu import ASSIGN_VERTEX

# The animations' size, and what they show: the whole template with room around it (and the colour window over it).
SIZE = QSize(640, 760)
SHOWN = Box(Vec(37, F(911, 20)), Vec(56, F(1349, 20)))

# What the animations with the instrument panel show right of it: the template, close to the panel.
PANEL_SHOWN = Box(Vec(39, 46), Vec(F(109, 2), 67))

# Where the mouse is before the first animation: left of the template, below its arm.
START: Point = (39.0, 52.0)

# The dark green face's colour, and a point inside each of its two pieces.
GREEN = "#008A4B"
GREEN_PIECES: tuple[Point, ...] = ((48.5, 60.0), (48.5, 52.0))


def _template() -> Template:
    return cube_with_a_hole().state.template


def _at(label: str) -> Point:
    """Where the built-in template has the vertex `label` ("S1")."""
    vertex = next(v for v in _template().all_vertices if str(v.label) == label)
    return float(vertex.position.x), float(vertex.position.y)


def _point(p: Vec) -> Point:
    return float(p.x), float(p.y)


def empty_start() -> TemplateDocument:
    """Nothing drawn yet, in the built-in template's style."""
    return TemplateDocument(TemplateSnapshot(Template()), History(), cube_with_a_hole().style)


@cache
def loop_start() -> TemplateDocument:
    """Where `FOLDS_AND_HOLE` starts: the outer loop drawn, as `DRAW_LOOP` draws it (one face, nothing named): made
    from the built-in template, not by replaying the clicks (the rules' checks would take seconds)."""
    template = _bare(_template())
    loop = replace(template, folds=(), holes=(), faces=(TemplateFace(tuple(v.id for v in template.vertices)),))
    return TemplateDocument(TemplateSnapshot(loop), History(), cube_with_a_hole().style)


@cache
def folds_start() -> TemplateDocument:
    """Where `COLORS_AND_LABELS` starts: the loop, the hole and the fold lines drawn (nothing coloured or named)."""
    return TemplateDocument(TemplateSnapshot(_bare(_template())), History(), cube_with_a_hole().style)


def _bare(template: Template) -> Template:
    """The template as drawn, before any colour or name: no labels, no colours, hatches tied to the grid."""

    def unnamed(vertices: tuple[LoopVertex, ...]) -> tuple[LoopVertex, ...]:
        return tuple(replace(v, label=None) for v in vertices)

    faces = tuple(TemplateFace(f.corners, holes=f.holes) for f in template.faces)
    holes = tuple(replace(h, vertices=unnamed(h.vertices)) for h in template.holes)
    vertices, fold_vertices = unnamed(template.vertices), unnamed(template.fold_vertices)
    return replace(template, vertices=vertices, holes=holes, fold_vertices=fold_vertices, faces=faces, next_number=1)


def validate_start() -> TemplateDocument:
    """The built-in template with every face coloured and every vertex named, but H1."""
    document = cube_with_a_hole()
    template = document.state.template
    vertices = tuple(replace(v, label=None) if str(v.label) == "H1" else v for v in template.vertices)
    state = replace(document.state, template=replace(template, vertices=vertices))
    return TemplateDocument(state, History(), document.style, ValidationStatus.UNDEFINED)


def _clicks(points: list[Point], move_ms: int, rest_ms: int) -> list[Step]:
    steps: list[Step] = []
    for p in points:
        steps += [Move(p, move_ms), *click(), Wait(rest_ms)]
    return steps


def _draw_loop() -> list[Step]:
    loop = [_point(v.position) for v in _template().vertices]
    return [Move(START, 0), Wait(400), *_clicks([*loop, loop[0]], 330, 60), Wait(1000)]


def _folds_and_hole() -> list[Step]:
    template = _template()
    hole = [_point(v.position) for v in template.holes[0].vertices]
    folds: list[Point] = []
    for fold in template.folds:
        folds += [_point(template.position(fold.start)), _point(template.position(fold.end))]
    first = _point(template.vertices[0].position)  # where `DRAW_LOOP` leaves the mouse
    steps = [Move(first, 0), Wait(500), ToWidget(DRAW_HOLE, 1000), Wait(300), *click(), Wait(400)]
    steps += _clicks([*hole, hole[0]], 450, 107)
    return [*steps, *_clicks(folds, 450, 107), Wait(1000)]


def _colors_and_labels() -> list[Step]:
    template = _template()
    last = _point(template.position(template.folds[-1].end))  # where `FOLDS_AND_HOLE` leaves the mouse
    steps: list[Step] = [Move(last, 0), Wait(500)]
    for inside in GREEN_PIECES:
        steps += [
            Move(inside, 900),
            Wait(300),
            DoubleClick(),
            Wait(900),
            ToWidget(COLOR_CODE, 700),
            Wait(300),
            *click(),
            Wait(400),
            Keys(Qt.KeyboardModifier.ControlModifier),
            Type("a", 0),  # its text selected
            Wait(700),
            Paste(GREEN),  # (Ctrl+V)
            Wait(300),
            Keys(Qt.KeyboardModifier.NoModifier),
            Wait(900),
            Type("\n"),
            Wait(700),
        ]
    for index, label in enumerate(("S1", "S2", "S3"), start=1):
        steps += [
            Move(_at(label), 900),
            Wait(300),
            RightClick(),
            Wait(600),
            ToItem(ASSIGN_VERTEX, 500),
            Wait(250),
            *click(),
            Wait(700),
            Type("S", 250),
            Wait(500),
            Type(f"\t{index}", 300),  # (its index: the window keeps 1 until it's changed)
            Wait(800),
            Type("\n"),
            Wait(700),
        ]
    return [*steps, Wait(800)]


def _validate() -> list[Step]:
    return [
        Move(START, 0),
        Wait(500),
        ToWidget(VALIDATE, 1000),
        Wait(300),
        *click(),
        Wait(3600),  # what's wrong: some vertices have no labels
        Type("\n"),
        Wait(600),
        Move(_at("H1"), 1000),
        Wait(300),
        RightClick(),
        Wait(600),
        ToItem(ASSIGN_VERTEX, 500),
        Wait(250),
        *click(),
        Wait(700),
        Type("H", 250),
        Wait(800),
        Type("\n"),
        Wait(800),
        ToWidget(VALIDATE, 1000),
        Wait(300),
        *click(),
        Wait(2200),  # nothing wrong
        Type("\n"),
        Wait(800),
    ]


DRAW_LOOP = _draw_loop()
FOLDS_AND_HOLE = _folds_and_hole()
COLORS_AND_LABELS = _colors_and_labels()
VALIDATING = _validate()
