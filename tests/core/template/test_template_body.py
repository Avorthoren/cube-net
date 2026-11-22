# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from fractions import Fraction as F

import pytest

from cube_net.core.body import CUBE, SurfacePoint
from cube_net.core.geometry import Vec
from cube_net.core.labels import PointLabels, vertex_labels
from cube_net.core.net import Net, default_net, starting_net, validate_net
from cube_net.core.project import TemplateDocument
from cube_net.core.template import (
    Template,
    TemplateEditor,
    TemplateProblem,
    body_from_template,
    template_area,
    validate,
)


def labels_by_position(net: Net) -> dict[Vec, str]:
    return {v.position: str(label) for v, label in vertex_labels(net, PointLabels(net.body)).items()}


def test_the_cross_gives_the_cubes_default_net(cross_template: Template) -> None:
    body = body_from_template(cross_template)
    assert body.area == template_area(cross_template) == 6
    assert len(body.edges) == 12 and body.vertex_names == CUBE.vertex_names
    assert {body.vertex_angle(v) for v in body.vertex_names} == {270}
    net = starting_net(body)
    validate_net(net)
    assert labels_by_position(net) == labels_by_position(default_net())  # A_1 where A_1 is, and so on
    assert len(net.fold_edges()) == 5 and len(net.boundary_edges()) == 14


def test_faces_and_colours_in_the_templates_order(cross_template: Template) -> None:
    body = body_from_template(cross_template)
    assert body.face_numbers == tuple(range(1, len(cross_template.faces) + 1))
    assert body.colors == tuple(face.color for face in cross_template.faces)
    assert sorted(body.colors) == sorted(CUBE.colors)


def test_a_point_glued_across_a_cut(cross_template: Template) -> None:
    """The middle of A_3-B_3 is the middle of A_1-B_1: the same point of the body."""

    body = body_from_template(cross_template)
    bottom = next(n for n in body.face_numbers if Vec(11, 10) in body.face(n).corners)
    top = next(n for n in body.face_numbers if Vec(11, 14) in body.face(n).corners)

    assert SurfacePoint(body, bottom, Vec(F(23, 2), 10)) == SurfacePoint(body, top, Vec(F(23, 2), 14))


def test_the_pinwheel_box(pinwheel_template: Template) -> None:
    body = body_from_template(pinwheel_template)
    assert body.area == 16
    assert body.vertex_angle("M") == 360 and len(body.vertex_faces("M")) == 4
    net = starting_net(body)
    validate_net(net)
    assert labels_by_position(net)[pinwheel_template.vertices[3].position] == "M_1"


def test_only_a_valid_template(cross_template: Template) -> None:
    owner = cross_template.vertices[0].id
    with pytest.raises(ValueError, match="isn't valid"):
        body_from_template(cross_template.with_label(owner, None))


# The cross with a slit along C-H instead of the fold: the loop goes down from C_1 to H_1 and back up to C_2, and passes
# H again (H_2) between E_2 and E_1. Face 4 then hangs on by the points C and H only: two pieces of paper.
SLIT_CROSS = [
    (11, 10), (12, 10), (12, 11), (12, 12), (13, 12), (13, 13), (12, 13), (12, 14), (11, 14), (11, 13), (11, 12),
    (11, 13), (10, 13), (10, 12), (11, 12), (11, 11),
]  # fmt: skip


def test_a_face_hanging_on_by_points_is_refused() -> None:
    editor = TemplateEditor()
    for x, y in SLIT_CROSS:
        assert editor.add_point(Vec(x, y)) is None
    rejection = editor.add_point(Vec(11, 10))  # closing it
    assert rejection is not None and rejection.problem is TemplateProblem.APART
    assert not editor.template.closed


# The 1 x 1 x 2 box (`long_box`'s net, 10 units right and up), cut between its front and its right side from the top
# down to the middle M of their edge B-F: the loop goes down that slit and back up. B-M stays a fold. The slit's two
# sides are images of one edge of the body lying on each other: in the net that's a fold (as gluing would make it).
SLIT_BOX = [
    (10, 9, "D", 1), (11, 9, "C", 1), (11, 10, "B", 1), (12, 10, "C", 2), (13, 10, "D", 2), (14, 10, "A", 1),
    (14, 12, "E", 1), (13, 12, "H", 1), (12, 12, "G", 1), (11, 12, "F", 1), (11, 11, "M", 1), (11, 12, "F", 2),
    (11, 13, "G", 2), (10, 13, "H", 2), (10, 12, "E", 2), (10, 10, "A", 2),
]  # fmt: skip
SLIT_BOX_FOLDS = [("A2", "B1"), ("B1", "M1"), ("C2", "G1"), ("D2", "H1"), ("E2", "F2")]


def test_a_slit_whose_sides_are_one_edge_is_a_fold(draw: Callable[..., TemplateEditor]) -> None:
    template = draw(SLIT_BOX, SLIT_BOX_FOLDS).template
    assert validate(template) is None
    body = body_from_template(template)
    # M, the slit's tip, lies in the middle of the straight edge B-F (360 degrees around it): no vertex of the body.
    assert body.area == 10 and "M" not in body.vertex_names
    assert "BF" in {"".join(sorted(e.names)) for e in body.edges}
    net = starting_net(body)
    validate_net(net)
    at_f = [v for v in net.vertices if v.position == Vec(11, 12)]
    assert len(at_f) == 1  # F_1 and F_2 are one point
    assert not [v for v in net.vertices if v.position == Vec(11, 11)]  # M's point, inside the net: gone
    folds = {frozenset((he.origin.position, he.destination.position)) for he in net.fold_edges()}
    assert frozenset((Vec(11, 10), Vec(11, 12))) in folds  # the slit glued: one fold B-F


def test_a_face_in_two_pieces_is_one_face(half_moved_template: Template) -> None:
    template = half_moved_template
    assert validate(template) is None
    body = body_from_template(template)
    assert len(body.face_numbers) == 6 and body.area == 24  # the cube, doubled
    # X and Y lie in the middle of the edges A-E and B-F: the line is smooth there, they're no vertices of the body.
    assert body.vertex_names == CUBE.vertex_names and {body.vertex_angle(v) for v in body.vertex_names} == {270}
    net = starting_net(body)
    validate_net(net)
    assert len(net.regions) == 7  # the pieces, where they are
    in_two = [f for f in body.face_numbers if sum(r.face == f for r in net.regions) == 2]
    assert len(in_two) == 1 and len(body.face(in_two[0]).corners) == 4  # face 5: a square again
    # The cut between the pieces is inside the face: on the perimeter twice, coloured by that face alone.
    inside = [he for he in net.boundary_edges() if len(net.segment_faces(he)) == 1]
    assert len(inside) == 2


def test_a_ring(slit_torus: TemplateDocument) -> None:
    body = body_from_template(slit_torus.state.template)
    rings = [f for f in body.face_numbers if len(body.face(f).loops) == 2]
    assert len(body.face_numbers) == 10 and len(rings) == 2
    for f in rings:
        face = body.face(f)
        middle = sum(face.loops[1], Vec(0, 0)) / len(face.loops[1])  # inside the hole
        assert not face.contains(middle) and face.contains(face.loops[1][0])
    net = starting_net(body)
    validate_net(net)
    assert len(net.regions) == 12


def test_a_bent_fold_line(cross_template: Template) -> None:
    """The cross with the fold C_1-D_1 (between faces 1 and 2) bent up through a fold vertex M: M is a vertex of the
    body with 360 degrees around it, inside the net; the faces are a pentagon and a square with a notch."""
    from dataclasses import replace

    from cube_net.core.template import Fold, Label

    c1, d1 = (next(v.id for v in cross_template.vertices if str(v.label) == name) for name in ("C1", "D1"))
    template = cross_template.without_fold(next(f for f in cross_template.folds if f.joins(c1, d1)))
    template = template.with_fold_line(c1, [Vec(F(23, 2), F(53, 4))], d1)
    m = template.fold_vertices[0].id
    template = template.with_label(m, Label("M", 1))
    sides = [i for i, f in enumerate(template.faces) if m in f.corners]
    template = template.with_face_color(sides[0], "#123456").with_face_color(sides[1], "#654321")
    assert validate(template) is None
    body = body_from_template(template)
    assert body.vertex_angle("M") == 360 and len(body.face_numbers) == 6 and body.area == 6
    assert {"".join(sorted(e.names)) for e in body.edges} >= {"CM", "DM"}
    net = starting_net(body)
    validate_net(net)
    assert [v for v in net.vertices if v.point.vertex == "M"]  # inside the net, between the two folds
    assert Fold(c1, m) in template.folds and replace(template, fold_vertices=()) != template


def test_a_fold_vertex_needs_a_label(cross_template: Template) -> None:
    from cube_net.core.template import ValidationProblem

    c1, d1 = (next(v.id for v in cross_template.vertices if str(v.label) == name) for name in ("C1", "D1"))
    template = cross_template.without_fold(next(f for f in cross_template.folds if f.joins(c1, d1)))
    template = template.with_fold_line(c1, [Vec(F(23, 2), F(53, 4))], d1)
    failure = validate(template)
    assert failure is not None and failure.problem in (ValidationProblem.NO_COLOR, ValidationProblem.UNLABELLED)


def test_a_template_with_a_hole(cross_template: Template) -> None:
    """The cross with a small square hole in face 2 (docs/template_plan.md, §8.5): its sides glued in pairs, P-Q to
    Q-P and P-R to R-P (each pair meets at Q or R), so face 2 is a ring glued to itself; the net has a hole."""
    from cube_net.core.template import Label, TemplateEditor
    from cube_net.core.template.holes import closed_hole, with_hole_point

    corners = [(F(45, 4), F(49, 4)), (F(45, 4), F(25, 2)), (F(23, 2), F(25, 2)), (F(23, 2), F(49, 4))]
    template = cross_template
    for x, y in corners:
        template = with_hole_point(template, Vec(x, y))
    template = closed_hole(template)
    names = {
        Vec(*corners[0]): ("P", 1),
        Vec(*corners[1]): ("Q", 1),
        Vec(*corners[2]): ("P", 2),
        Vec(*corners[3]): ("R", 1),
    }
    for v in template.holes[0].vertices:
        template = template.with_label(v.id, Label(*names[v.position]))
    assert validate(template) is None
    body = body_from_template(template)
    rings = [n for n in body.face_numbers if len(body.face(n).loops) == 2]
    assert len(rings) == 1 and body.area == 6 - F(1, 16)
    assert body.vertex_angle("P") == 540 and body.vertex_angle("Q") == 270
    net = starting_net(body)
    validate_net(net)
    assert len(net.perimeters()) == 2  # the outer one and the hole's
    editor = TemplateEditor(template)
    assert editor.template.holes[0].closed
