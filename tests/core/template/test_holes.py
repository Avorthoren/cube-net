# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Holes in templates (docs/template_plan.md, §8.5), in a 10 x 10 square with a fold down its middle (x = 5): vertices
0..5 from (0, 0) counter-clockwise, the fold from 1 (5, 0) to 4 (5, 10)."""

from fractions import Fraction as F

import pytest

from cube_net.core.geometry import Vec
from cube_net.core.project import TemplateDocument
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


def test_a_hole_in_a_template_with_a_slit(slit_torus: TemplateDocument) -> None:
    """The torus template as it was built in (`SLIT_TORUS`) has a slit: its loop goes up from S2 to M2 and back down
    from M2 to K2, two sides leaving M2 the same way. A hole drawn in its purple face used to lose the three faces by
    the slit when the faces were worked out again (2026-11-19: the file was saved so, and couldn't be opened)."""
    template = slit_torus.state.template
    assert {frozenset(c) for c, _ in faces_from_graph(template)} == {frozenset(f.corners) for f in template.faces}
    editor = TemplateEditor(template)
    hole = [(F(173, 4), F(119, 2)), (F(175, 4), F(119, 2)), (F(175, 4), F(121, 2))]  # in the upper purple piece
    for x, y in [*hole, hole[0]]:
        assert editor.add_hole_point(Vec(x, y)) is None
    after = editor.template
    assert len(after.faces) == len(template.faces) and sum(bool(f.holes) for f in after.faces) == 1
    assert {f.color for f in after.faces} == {f.color for f in template.faces}


def test_faces_that_dont_add_up_are_never_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    """A safety net: if working the faces out ever went wrong again, the change is refused, not kept (and saved)."""
    import cube_net.core.template.holes as holes

    editor = TestEditor().editor()
    for p in [(1, 1), (2, 1), (2, 2)]:
        assert editor.add_hole_point(Vec(*p)) is None
    real = holes.faces_from_graph
    monkeypatch.setattr(holes, "faces_from_graph", lambda t: real(t)[1:])  # a face lost
    before = editor.template
    assert editor.add_hole_point(Vec(1, 1)) is not None
    assert editor.template is before and editor.template.drawing_hole


def test_a_face_is_never_its_own_hole() -> None:
    """A triangle of folds touching nothing else (none should be left so: see `TestFloatingFolds`) is a face of its own,
    and the hole of the face around it (2026-11-20: it was its own hole, and clicks inside reached the face around)."""
    from dataclasses import replace

    from cube_net.core.template import LoopVertex
    from cube_net.core.template.holes import _refaced

    template = holed(square(), [(6, 6), (7, 6), (7, 7), (6, 7)])
    n = template.next_id
    corners = [Vec(1, 1), Vec(3, 1), Vec(2, 3)]
    floating = replace(
        template,
        fold_vertices=tuple(LoopVertex(n + i, p) for i, p in enumerate(corners)),
        folds=(*template.folds, Fold(n, n + 1), Fold(n + 1, n + 2), Fold(n + 2, n)),
        next_id=n + 3,
    )
    faced = _refaced(floating, template)
    triangle = faced.face_at(Vec(2, 2))
    around = faced.face_at(Vec(4, 8))
    assert triangle is not None and around is not None and triangle != around
    assert faced.faces[triangle].holes == () and set(faced.faces[around].holes[0]) == {n, n + 1, n + 2}


def test_a_loop_of_folds_left_floating_by_its_hole_goes() -> None:
    """A triangle held by two segments from a hole's vertices: the hole deleted, it floats, and goes."""
    template = holed(square(), [(6, 6), (8, 6), (7, 8)])
    at = {v.position: v.id for v in template.holes[0].vertices}
    template = template.with_fold_line(at[Vec(6, 6)], [Vec(6, 2), Vec(8, 2), Vec(7, 4)], at[Vec(8, 6)])
    corner = {v.position: v.id for v in template.fold_vertices}
    template = template.with_fold_line(corner[Vec(7, 4)], [], corner[Vec(6, 2)])
    assert len(template.faces) == 4
    after = without_hole_vertex(template, at[Vec(6, 6)])
    assert after.holes == () and after.folds == (Fold(1, 4),) and after.fold_vertices == ()
    assert sorted(f.color for f in after.faces) == ["#00AA00", "#AA0000"]


def test_a_loop_of_folds_hanging_from_a_hole_by_one_segment_goes() -> None:
    template = holed(square(), [(6, 6), (8, 6), (7, 8)])
    at = {v.position: v.id for v in template.holes[0].vertices}
    template = template.with_fold_line(at[Vec(6, 6)], [Vec(6, 2), Vec(8, 2), Vec(7, 4)], at[Vec(8, 6)])
    corner = {v.position: v.id for v in template.fold_vertices}
    template = template.with_fold_line(corner[Vec(7, 4)], [], corner[Vec(6, 2)])
    after = template.without_fold(Fold(at[Vec(6, 6)], corner[Vec(6, 2)]))
    assert after.folds == (Fold(1, 4),) and after.fold_vertices == () and len(after.faces) == 2
