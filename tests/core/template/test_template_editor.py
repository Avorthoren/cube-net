# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.geometry import Vec
from cube_net.core.history import ActionKind
from cube_net.core.origin import Origin
from cube_net.core.template import Fold, Label, TemplateEditor, TemplateProblem, TemplateState

# A 2 x 1 rectangle with the middles of its long sides: 6 vertices, ids 0..5, counter-clockwise.
PILLOW = [Vec(10, 10), Vec(11, 10), Vec(12, 10), Vec(12, 11), Vec(11, 11), Vec(10, 11)]

# An L: a reflex corner at (11, 11) (id 3), ids 0..5.
L_SHAPE = [Vec(10, 10), Vec(12, 10), Vec(12, 11), Vec(11, 11), Vec(11, 12), Vec(10, 12)]


def drawn(points: list[Vec]) -> TemplateEditor:
    editor = TemplateEditor()
    for p in [*points, points[0]]:
        assert editor.add_point(p) is None
    return editor


class TestLooping:
    def test_states(self) -> None:
        editor = TemplateEditor()
        assert editor.state is TemplateState.INITIAL
        assert editor.add_point(Vec(10, 10)) is None
        assert editor.state is TemplateState.LOOPING
        for p in PILLOW[1:]:
            assert editor.add_point(p) is None
        assert editor.add_point(PILLOW[0]) is None
        assert editor.state is TemplateState.FINALIZATION
        assert len(editor.template.faces) == 1

    @pytest.mark.parametrize("p", [Vec(-1, 5), Vec(5, F(100001, 1000)), Vec(101, 0)])
    def test_only_on_the_sheet(self, p: Vec) -> None:
        rejection = TemplateEditor().add_point(p)
        assert rejection is not None and rejection.problem is TemplateProblem.OFF_THE_SHEET
        assert TemplateEditor().add_point(Vec(100, 0)) is None

    def test_at_least_three_segments(self) -> None:
        editor = TemplateEditor()
        editor.add_point(Vec(10, 10))
        editor.add_point(Vec(11, 10))
        rejection = editor.add_point(Vec(10, 10))
        assert rejection is not None and rejection.problem is TemplateProblem.TOO_EARLY_TO_CLOSE
        editor.add_point(Vec(11, 11))
        assert editor.add_point(Vec(10, 10)) is None
        assert editor.state is TemplateState.FINALIZATION

    def test_no_crossing(self) -> None:
        editor = TemplateEditor()
        for p in (Vec(10, 10), Vec(12, 10), Vec(12, 12)):
            editor.add_point(p)
        rejection = editor.add_point(Vec(11, 9))  # back across the first segment
        assert rejection is not None and rejection.problem is TemplateProblem.CROSSING
        assert rejection.segments == ((Vec(12, 12), Vec(11, 9)),)
        assert len(editor.template.vertices) == 3

    @pytest.mark.parametrize(
        "p",
        [
            Vec(11, 10),  # on the first segment
            Vec(12, 10),  # on a vertex that isn't the first one
            Vec(12, 11),  # back along the last segment: a slit
        ],
    )
    def test_touching_is_fine(self, p: Vec) -> None:
        editor = TemplateEditor()
        for q in (Vec(10, 10), Vec(12, 10), Vec(12, 12)):
            editor.add_point(q)
        assert editor.add_point(p) is None

    def test_the_last_vertex_again_is_no_segment(self) -> None:
        editor = TemplateEditor()
        for q in (Vec(10, 10), Vec(12, 10), Vec(12, 12)):
            editor.add_point(q)
        rejection = editor.add_point(Vec(12, 12))
        assert rejection is not None and rejection.problem is TemplateProblem.CROSSING

    def test_a_slit_into_the_loop(self) -> None:
        """Up 1 from the bottom side and down 1.5, past where it went up: the loop goes back along itself, with the net
        on both sides of the slit."""
        editor = TemplateEditor()
        for q in (Vec(10, 10), Vec(11, 10), Vec(11, 11), Vec(11, F(19, 2)), Vec(12, F(19, 2)), Vec(12, 12)):
            assert editor.add_point(q) is None
        assert editor.add_point(Vec(10, 12)) is None
        assert editor.add_point(Vec(10, 10)) is None
        assert editor.state is TemplateState.FINALIZATION

    def test_touching_with_the_net_on_the_same_side_is_refused(self) -> None:
        """Along its own first side again, the same way round: the net would be on the same side of both."""
        editor = TemplateEditor()
        for q in (Vec(10, 10), Vec(13, 10), Vec(13, 12), Vec(11, 12), Vec(11, 11), Vec(9, 11), Vec(9, 10)):
            assert editor.add_point(q) is None
        rejection = editor.add_point(Vec(12, 10))  # along the first side, the same way
        assert rejection is not None and rejection.problem is TemplateProblem.CROSSING

    def test_a_clockwise_loop_ends_up_counter_clockwise(self) -> None:
        editor = drawn(list(reversed(PILLOW)))
        assert editor.template.closed
        from cube_net.core.template import template_area

        assert template_area(editor.template) == 2

    def test_undo_takes_points_back_one_by_one(self) -> None:
        editor = drawn(PILLOW)
        assert editor.undo()
        assert editor.state is TemplateState.LOOPING and len(editor.template.vertices) == 6
        for _ in range(6):
            assert editor.undo()
        assert editor.state is TemplateState.INITIAL
        assert not editor.undo()
        assert editor.redo() and editor.template.vertices[0].position == PILLOW[0]
        assert editor.history.next_undo() is not None
        assert editor.history.next_undo().kind is ActionKind.ADD_VERTEX  # type: ignore[union-attr]


class TestFinalization:
    def test_inserting_a_vertex_in_a_sides_middle(self) -> None:
        editor = drawn(PILLOW)
        editor.insert_vertex(3, 4)
        assert editor.template.vertices[4].position == Vec(F(23, 2), 11)
        assert editor.undo() and len(editor.template.vertices) == 6

    def test_at_least_six_vertices_stay(self) -> None:
        editor = drawn(PILLOW)
        rejection = editor.delete_vertex(1)
        assert rejection is not None and rejection.problem is TemplateProblem.TOO_FEW_VERTICES
        editor.insert_vertex(3, 4)
        assert editor.delete_vertex(1) is None
        assert len(editor.template.vertices) == 6

    def test_a_deletion_that_would_cross(self) -> None:
        # A deep notch: without vertex 1, the new side from (10, 10) to (16, 14) would cut through the notch.
        notch = [Vec(10, 10), Vec(16, 10), Vec(16, 14), Vec(13, 11), Vec(10, 14), Vec(10, 13), Vec(10, 12)]
        editor = drawn(notch)
        rejection = editor.delete_vertex(1)
        assert rejection is not None and rejection.problem is TemplateProblem.CROSSING
        assert rejection.segments == ((Vec(10, 10), Vec(16, 14)),)
        assert len(editor.template.vertices) == 7
        assert editor.delete_vertex(5) is None  # (10, 13): on a straight side, nothing changes but the vertex

    def test_moving_a_vertex(self) -> None:
        editor = drawn(PILLOW)
        assert editor.move_vertex(4, Vec(11, 12)) is None
        assert editor.template.position(4) == Vec(11, 12)
        rejection = editor.move_vertex(4, Vec(11, 9))  # down through the bottom side
        assert rejection is not None and rejection.problem is TemplateProblem.CROSSING
        assert editor.template.position(4) == Vec(11, 12)
        assert editor.move_problem(4, Vec(11, 9)) is not None
        assert editor.move_problem(4, Vec(200, 9)) is not None
        revision = editor.history.revision
        assert editor.move_vertex(4, Vec(11, 12)) is None  # where it is: not an action
        assert editor.history.revision == revision

    def test_moving_a_vertex_keeps_its_folds_inside(self) -> None:
        editor = drawn(PILLOW)
        assert editor.add_fold(1, 4) is None
        rejection = editor.move_vertex(2, Vec(F(21, 2), F(21, 2)))  # across the fold
        assert rejection is not None and rejection.problem is TemplateProblem.CROSSING

    def test_folds(self) -> None:
        editor = drawn(PILLOW)
        assert editor.add_fold(1, 4) is None
        assert len(editor.template.faces) == 2
        for a, b in [(1, 4), (4, 1), (1, 2), (3, 3)]:  # again, the other way, neighbours, one vertex
            rejection = editor.add_fold(a, b)
            assert rejection is not None and rejection.problem is TemplateProblem.NOT_A_FOLD
        rejection = editor.add_fold(0, 2)  # along the bottom, through vertex 1
        assert rejection is not None and rejection.problem is TemplateProblem.CROSSING
        rejection = editor.add_fold(0, 3)  # across the fold 1-4
        assert rejection is not None and rejection.problem is TemplateProblem.CROSSING
        assert editor.add_fold(1, 3) is None  # meets the other fold at 1 only
        editor.delete_fold(Fold(1, 4))
        assert len(editor.template.faces) == 2
        assert editor.undo() and len(editor.template.faces) == 3

    def test_a_fold_outside_the_loop(self) -> None:
        editor = drawn(L_SHAPE)
        rejection = editor.add_fold(2, 4)  # round the reflex corner, outside
        assert rejection is not None and rejection.problem is TemplateProblem.OUTSIDE_THE_LOOP
        assert editor.add_fold(1, 3) is None

    def test_deleting_a_vertex_takes_its_folds_too_and_undo_brings_both(self) -> None:
        editor = drawn(PILLOW)
        editor.insert_vertex(5, 0)
        editor.add_fold(1, 4)
        assert editor.delete_vertex(4) is None
        assert editor.template.folds == () and len(editor.template.faces) == 1
        assert editor.undo()
        assert editor.template.folds == (Fold(1, 4),) and len(editor.template.faces) == 2

    def test_face_colours(self) -> None:
        editor = drawn(PILLOW)
        editor.set_face_color(0, "#ABCDEF")
        assert editor.template.faces[0].color == "#ABCDEF"
        revision = editor.history.revision
        editor.set_face_color(0, "#ABCDEF")
        assert editor.history.revision == revision
        assert editor.undo() and editor.template.faces[0].color == "#FFFFFF"


class TestLabels:
    def test_a_label_and_a_taken_one(self) -> None:
        editor = drawn(PILLOW)
        assert editor.set_label(0, Label("P", 1)) is None
        rejection = editor.set_label(2, Label("P", 1))
        assert rejection is not None and rejection.problem is TemplateProblem.LABEL_TAKEN
        assert editor.set_label(0, Label("P", 1)) is None  # its own: nothing changes
        assert editor.set_label(2, Label("P", editor.template.first_free_index("P"))) is None
        assert editor.template.vertex(2).label == Label("P", 2)
        assert editor.set_label(0, None) is None and editor.template.vertex(0).label is None
        assert editor.history.done_count == 7 + 3

    def test_labels_while_drawing(self) -> None:
        editor = TemplateEditor()
        editor.add_point(Vec(10, 10))
        assert editor.set_label(0, Label("A", 1)) is None


def test_moving_the_origin_is_an_action() -> None:
    editor = drawn(PILLOW)
    origin = Origin().moved(Vec(10, 10), Vec(0, 0), "P1")
    editor.move_origin(origin)
    assert editor.origin == origin and editor.snapshot().origin == origin
    assert editor.undo() and editor.origin == Origin()


def test_the_editor_needs_a_closed_loop_for_finalization() -> None:
    editor = TemplateEditor()
    editor.add_point(Vec(10, 10))
    with pytest.raises(ValueError, match="isn't closed"):
        editor.add_fold(0, 0)
    with pytest.raises(ValueError, match="is closed"):
        drawn(PILLOW).add_point(Vec(50, 50))


def test_a_slit_tip_on_the_far_side_would_part_the_paper() -> None:
    """A slit up from the bottom side whose tip is moved onto the top side: the net would be two pieces meeting at a
    point (docs/template_plan.md, §8.1)."""
    editor = drawn(
        [Vec(10, 10), Vec(11, 10), Vec(11, 11), Vec(11, F(19, 2)), Vec(12, F(19, 2)), Vec(12, 12), Vec(10, 12)]
    )
    tip = 2
    assert editor.move_vertex(tip, Vec(11, F(23, 2))) is None  # still inside: fine
    rejection = editor.move_vertex(tip, Vec(11, 12))  # on the top side
    assert rejection is not None and rejection.problem is TemplateProblem.APART
    assert editor.template.position(tip) == Vec(11, F(23, 2))


def test_a_refusal_shows_the_fold_it_runs_into_too() -> None:
    """A slit up from the bottom side along a fold: both the slit's sides and the fold flash."""
    editor = drawn([Vec(10, 10), Vec(11, 10), Vec(12, 10), Vec(12, 12), Vec(11, 12), Vec(10, 12)])
    assert editor.add_fold(1, 4) is None  # (11, 10) up to (11, 12)
    editor.insert_vertex(1, 2)
    middle = editor.template.vertices[2].id  # (23/2, 10)
    rejection = editor.move_vertex(middle, Vec(11, 11))
    assert rejection is not None
    assert (Vec(11, 10), Vec(11, 12)) in rejection.segments or (Vec(11, 12), Vec(11, 10)) in rejection.segments
    assert any(Vec(11, 11) in segment for segment in rejection.segments)  # the moved vertex's sides
