# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from dataclasses import replace

import pytest

from cube_net.core.geometry import Vec
from cube_net.core.template import Fold, Label, Template, TemplateEditor, ValidationProblem, reindexed, validate
from cube_net.core.template.glued_faces import glue_faces

type Draw = Callable[[list[tuple[int, int, str, int]], list[tuple[str, str]]], TemplateEditor]

# The fold-less pillow, its middles both named Q: every segment has its counterpart, but Q_1 and Q_2 are never glued.
TWO_QS = [(10, 10, "P", 1), (11, 10, "Q", 1), (12, 10, "P", 2), (12, 11, "S", 2), (11, 11, "Q", 2), (10, 11, "S", 1)]


def relabelled(template: Template, **labels: str) -> Template:
    """`template` with some labels changed, e.g. relabelled(t, A1="Q1"); "" takes a label away."""
    for old, new in labels.items():
        owner = next(v for v in template.vertices if str(v.label) == old)
        template = template.with_label(owner.id, Label(new[:-1], int(new[-1])) if new else None)
    return template


def moved(template: Template, label: str, to: Vec) -> Template:
    owner = next(v for v in template.vertices if str(v.label) == label)
    return template.with_vertex_moved(owner.id, to)


def vertex_id(template: Template, label: str) -> int:
    return next(v.id for v in template.vertices if str(v.label) == label)


def test_the_cross_is_valid(cross_template: Template) -> None:
    assert validate(cross_template) is None


def test_only_a_closed_loop() -> None:
    with pytest.raises(ValueError, match="closed"):
        validate(Template().with_vertex_appended(Vec(1, 1)))


def test_1_every_face_has_a_colour(cross_template: Template) -> None:
    faces = tuple(replace(face, color=None) if i in (1, 3) else face for i, face in enumerate(cross_template.faces))
    failure = validate(replace(relabelled(cross_template, G1=""), faces=faces))  # before the labels
    assert failure is not None and failure.problem is ValidationProblem.NO_COLOR and failure.count == 2


def test_white_is_a_colour(cross_template: Template) -> None:
    faces = tuple(replace(face, color="#FFFFFF") if i == 0 else face for i, face in enumerate(cross_template.faces))
    assert validate(replace(cross_template, faces=faces)) is None


# Where the cube's faces are in the cross (`cross_template`), doubled: 1 at the top, 2 in the middle, 3 and 4 right and
# left of it, 6 below it, 5 at the bottom.
CROSS_CENTRES = {1: Vec(23, 27), 2: Vec(23, 25), 3: Vec(25, 25), 4: Vec(21, 25), 5: Vec(23, 21), 6: Vec(23, 23)}


def coloured_alike(template: Template, *cube_faces: int) -> Template:
    """The cross with these cube faces in one colour (the first one's)."""
    pieces = [_face_at(template, CROSS_CENTRES[k]) for k in cube_faces]
    color = template.faces[pieces[0]].color
    faces = tuple(replace(face, color=color) if i in pieces else face for i, face in enumerate(template.faces))
    return replace(template, faces=faces)


def _face_at(template: Template, centre: Vec) -> int:
    index = template.face_at(centre / 2)  # the centres are doubled, as in the fixture
    assert index is not None
    return index


def test_two_faces_of_one_colour_glued_by_a_pair_are_one(cross_template: Template) -> None:
    """The left face and the top one share a cube edge, a pair of loop segments: in one colour, they're one face."""
    template = coloured_alike(cross_template, 4, 1)
    assert validate(template) is None
    gluing = glue_faces(template)
    assert len(gluing.faces) == 5 and not gluing.apart and not gluing.broken


def test_2_every_vertex_has_a_label(cross_template: Template) -> None:
    failure = validate(relabelled(cross_template, G1=""))
    assert failure is not None and failure.problem is ValidationProblem.UNLABELLED


def test_3_no_segment_joins_a_name_to_itself(cross_template: Template) -> None:
    failure = validate(relabelled(cross_template, B3="F3"))  # the loop goes on from it to F_1
    assert failure is not None and failure.problem is ValidationProblem.SELF_EDGE
    assert failure.names == ("F3-F1",)


def test_4_every_segment_has_exactly_one_counterpart(cross_template: Template) -> None:
    failure = validate(relabelled(cross_template, A3="Q1"))  # Q-B and E-Q once each, and so A-B and A-E
    assert failure is not None and failure.problem is ValidationProblem.NO_COUNTERPART
    assert failure.names == ("Q-B", "B-A", "A-E", "E-Q")


def test_5_counterparts_parallel_or_perpendicular(cross_template: Template) -> None:
    failure = validate(moved(cross_template, "A3", Vec(11, 9)))  # A_3-B_3 askew; E_1-A_3 is longer, but upright
    assert failure is not None and failure.problem is ValidationProblem.NOT_PARALLEL
    assert failure.names == ("A-B",)


def test_6_counterparts_of_the_same_length(draw: Draw) -> None:
    # TWO_QS stretched: its right half is 2 long, its left half 1.
    stretched = [
        (10, 10, "P", 1),
        (11, 10, "Q", 1),
        (13, 10, "P", 2),
        (13, 11, "S", 2),
        (11, 11, "Q", 2),
        (10, 11, "S", 1),
    ]
    failure = validate(draw(stretched, []).template)
    assert failure is not None and failure.problem is ValidationProblem.DIFFERENT_LENGTHS
    assert failure.names == ("P-Q", "S-Q")


def test_7_counterparts_run_opposite_ways(draw: Draw) -> None:
    # The bottom P-Q-R glued to the top P-Q-R the same way round: it would have to be turned over.
    loop = [(10, 10, "P", 1), (11, 10, "Q", 1), (12, 10, "R", 1), (12, 11, "P", 2), (11, 11, "Q", 2), (10, 11, "R", 2)]
    failure = validate(draw(loop, []).template)
    assert failure is not None and failure.problem is ValidationProblem.SAME_DIRECTION
    assert failure.names == ("P-Q", "Q-R", "R-P")


def test_8_a_fold_named_like_a_glued_pair(draw: Draw) -> None:
    failure = validate(draw(TWO_QS, [("P1", "Q2")]).template)  # a diagonal, named like the bottom's P-Q
    assert failure is not None and failure.problem is ValidationProblem.CUT_AND_FOLD
    assert failure.groups == (("P1-Q1", "P1-Q2"),)


def test_9_two_folds_named_the_same(cross_template: Template) -> None:
    # Two more folds (where they go doesn't matter to the names), both from A to G.
    folds = (Fold(vertex_id(cross_template, "A1"), vertex_id(cross_template, "G1")),)
    folds += (Fold(vertex_id(cross_template, "A3"), vertex_id(cross_template, "G1")),)
    failure = validate(replace(cross_template, folds=(*cross_template.folds, *folds)))
    assert failure is not None and failure.problem is ValidationProblem.SAME_FOLDS
    assert failure.groups == (("A1-G1", "A3-G1"),)


def test_10_every_names_instances_glued_together(draw: Draw) -> None:
    failure = validate(draw(TWO_QS, []).template)
    assert failure is not None and failure.problem is ValidationProblem.NOT_GLUED
    assert failure.names == ("Q",)


def test_10_through_chains(pinwheel_template: Template) -> None:
    """The pinwheel box's M: 4 instances glued in a ring, opposite ones sharing no neighbour."""
    assert validate(pinwheel_template) is None


def test_13_at_least_four_faces(
    draw: Draw, cross_drawing: tuple[list[tuple[int, int, str, int]], list[tuple[str, str]]]
) -> None:
    loop, folds = cross_drawing
    failure = validate(draw(loop, folds[:2]).template)
    assert failure is not None and failure.problem is ValidationProblem.TOO_FEW_FACES


def test_11_no_fold_between_faces_of_one_colour(cross_template: Template) -> None:
    failure = validate(coloured_alike(cross_template, 1, 2))
    assert failure is not None and failure.problem is ValidationProblem.SAME_COLOR_FOLD
    assert failure.names == ("C1-D1",)


def test_12_pieces_of_one_colour_glued_together(cross_template: Template) -> None:
    template = coloured_alike(cross_template, 1, 6)  # opposite faces: nothing joins them
    failure = validate(template)
    assert failure is not None and failure.problem is ValidationProblem.PIECES_APART
    assert failure.colors == (template.faces[_face_at(template, CROSS_CENTRES[1])].color,)


def test_15_glued_faces_are_flat(cross_template: Template) -> None:
    """Three faces around a corner of the cube, glued to each other by pairs: flat, they'd go only 270 degrees round."""
    template = coloured_alike(cross_template, 1, 4, 5)
    failure = validate(template)
    assert failure is not None and failure.problem is ValidationProblem.SELF_INTERSECTING
    assert failure.colors == (template.faces[_face_at(template, CROSS_CENTRES[1])].color,)


def test_16_indices_without_gaps_and_reindexing(cross_template: Template) -> None:
    gappy = relabelled(cross_template, A3="A9", E2="E5")
    failure = validate(gappy)
    assert failure is not None and failure.problem is ValidationProblem.INDEX_GAPS
    assert failure.names == ("A", "E")
    fixed = reindexed(gappy)
    assert validate(fixed) is None
    assert {str(v.label) for v in fixed.vertices} == {str(v.label) for v in cross_template.vertices}


def test_reindexing_keeps_the_order(cross_template: Template) -> None:
    template = relabelled(cross_template, A1="A9", A2="A4", A3="A2")  # A_2, A_4, A_9 -> A_1, A_2, A_3
    fixed = reindexed(template)
    old = {v.id: v.label for v in template.vertices}
    assert [str(old[v.id]) + ">" + str(v.label) for v in fixed.vertices if v.label and v.label.name == "A"] == [
        "A2>A1",
        "A9>A3",
        "A4>A2",
    ]
