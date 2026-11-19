# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Holes in templates (docs/template_plan.md, §8.5), in a 10 x 10 square with a fold down its middle (x = 5): vertices
0..5 from (0, 0) counter-clockwise, the fold from 1 (5, 0) to 4 (5, 10)."""

from fractions import Fraction as F

from cube_net.core.geometry import Vec
from cube_net.core.template import Fold, Template, TemplateEditor, TemplateProblem, template_area
from cube_net.core.template.holes import closed_hole, faces_from_graph, with_hole_point, without_hole_vertex

SQUARE = [(0, 0), (5, 0), (10, 0), (10, 10), (5, 10), (0, 10)]


def square() -> Template:
    template = Template()
    for p in SQUARE:
        template = template.with_vertex_appended(Vec(*p))
    return template.closed_loop().with_fold(1, 4).with_face_color(0, "#AA0000").with_face_color(1, "#00AA00")


def holed(template: Template, points: list[tuple[int, int]]) -> Template:
    for p in points:
        template = with_hole_point(template, Vec(*p))
    return closed_hole(template)


def test_a_hole_across_the_fold_cuts_it() -> None:
    template = holed(square(), [(3, 4), (7, 4), (7, 6), (3, 6)])
    (hole,) = template.holes
    assert hole.closed and len(hole.vertices) == 6  # the 4 drawn, and where it crosses the fold
    crossings = {v.position for v in hole.vertices} - {Vec(3, 4), Vec(7, 4), Vec(7, 6), Vec(3, 6)}
    assert crossings == {Vec(5, 4), Vec(5, 6)}
    ends = {template.position(v) for f in template.folds for v in (f.start, f.end)}
    assert len(template.folds) == 2 and Vec(5, 4) in ends and Vec(5, 6) in ends  # the part inside is gone
    assert len(template.faces) == 2 and {f.color for f in template.faces} == {"#AA0000", "#00AA00"}
    assert template_area(template) == 100 - 8


def test_a_hole_inside_a_face_makes_it_a_ring() -> None:
    template = holed(square(), [(1, 1), (2, 1), (2, 2), (1, 2)])
    rings = [f for f in template.faces if f.holes]
    assert len(rings) == 1 and len(rings[0].holes[0]) == 4
    assert template.face_at(Vec(3, 3)) is not None and template.face_at(Vec(F(3, 2), F(3, 2))) is None  # the hole
    assert template.holes[0].closed and template_area(template) == 99


def test_the_hole_runs_clockwise_whichever_way_it_was_drawn() -> None:
    from cube_net.core.geometry import signed_area

    for points in ([(1, 1), (2, 1), (2, 2), (1, 2)], [(1, 1), (1, 2), (2, 2), (2, 1)]):
        template = holed(square(), points)
        assert signed_area([v.position for v in template.holes[0].vertices]) < 0


def test_the_faces_from_the_segments() -> None:
    template = holed(square(), [(1, 1), (2, 1), (2, 2), (1, 2)])
    faces = faces_from_graph(template)
    assert len(faces) == 2 and sum(len(holes) for _, holes in faces) == 1


def test_deleting_a_vertex_of_a_hole_and_the_hole() -> None:
    template = holed(square(), [(1, 1), (2, 1), (2, 2), (1, 2)])
    first = template.holes[0].vertices[0].id
    smaller = without_hole_vertex(template, first)
    assert len(smaller.holes[0].vertices) == 3 and template_area(smaller) == 100 - F(1, 2)
    gone = without_hole_vertex(smaller, smaller.holes[0].vertices[0].id)
    assert gone.holes == () and all(not f.holes for f in gone.faces) and template_area(gone) == 100


def test_deleting_a_hole_that_cut_a_fold_takes_its_parts_too() -> None:
    template = holed(square(), [(3, 4), (7, 4), (7, 6), (3, 6)])
    for _ in range(3):
        template = without_hole_vertex(template, next(v.id for v in template.holes[0].vertices if v.position.x != 5))
    template = without_hole_vertex(template, template.holes[0].vertices[0].id) if template.holes else template
    assert template.holes == () and template.folds == () and len(template.faces) == 1


class TestEditor:
    def editor(self) -> TemplateEditor:
        editor = TemplateEditor()
        for p in [*SQUARE, SQUARE[0]]:
            assert editor.add_point(Vec(*p)) is None
        assert editor.add_fold(1, 4) is None
        return editor

    def test_points_and_closing_are_actions(self) -> None:
        editor = self.editor()
        for p in [(3, 4), (7, 4), (7, 6), (3, 6)]:
            assert editor.add_hole_point(Vec(*p)) is None
        assert editor.template.drawing_hole and not editor.template.complete
        assert editor.add_hole_point(Vec(3, 4)) is None  # its first vertex closes it
        assert editor.template.complete and editor.template.folds != (Fold(1, 4),)
        assert editor.undo() and editor.template.drawing_hole and editor.template.folds == (Fold(1, 4),)

    def test_refused_points(self) -> None:
        editor = self.editor()
        assert editor.add_hole_point(Vec(20, 20)) is not None  # outside the net
        assert editor.add_hole_point(Vec(5, 5)) is not None  # on the fold
        assert editor.add_hole_point(Vec(1, 1)) is None
        assert editor.add_hole_point(Vec(0, 2)) is not None  # on the loop
        assert editor.add_hole_point(Vec(2, 1)) is None
        rejection = editor.add_hole_point(Vec(1, 1))  # only 2 sides: too early to close
        assert rejection is not None and rejection.problem is TemplateProblem.TOO_EARLY_TO_CLOSE

    def test_a_hole_may_not_touch_another(self) -> None:
        editor = self.editor()
        for p in [(1, 1), (2, 1), (2, 2), (1, 1)]:
            assert editor.add_hole_point(Vec(*p)) is None
        assert editor.add_hole_point(Vec(1, 3)) is None
        assert editor.add_hole_point(Vec(2, 2)) is not None  # on the first hole's vertex
        assert editor.add_hole_point(Vec(3, 3)) is None
        assert editor.add_hole_point(Vec(3, 1)) is None
        assert editor.add_hole_point(Vec(1, 3)) is not None  # closing would run into the first hole

    def test_deleting_a_vertex_of_a_hole_being_drawn_is_refused(self) -> None:
        editor = self.editor()
        assert editor.add_hole_point(Vec(1, 1)) is None
        assert editor.delete_vertex(editor.template.holes[0].vertices[0].id) is not None


def test_a_hole_vertex_dragged_over_a_fold_cuts_it() -> None:
    """A hole left of the fold, one vertex dragged across it: as if the hole had been drawn there."""
    editor = TestEditor().editor()
    for p in [(1, 4), (3, 4), (3, 6), (1, 6), (1, 4)]:
        assert editor.add_hole_point(Vec(*p)) is None
    assert editor.template.folds == (Fold(1, 4),)
    moved = next(v.id for v in editor.template.holes[0].vertices if v.position == Vec(3, 4))
    assert editor.move_problem(moved, Vec(7, 4)) is None
    assert editor.move_vertex(moved, Vec(7, 4)) is None
    positions = {v.position for v in editor.template.holes[0].vertices}
    assert {Vec(5, 4), Vec(5, 5)} <= positions  # the new crossings: vertices of the hole
    assert len(editor.template.folds) == 2 and len(editor.template.faces) == 2  # the part inside it gone
    assert editor.undo() and editor.template.folds == (Fold(1, 4),)
