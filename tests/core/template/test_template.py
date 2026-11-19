# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

import pytest

from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.template import Fold, Label, Template, TemplateFace, template_area

# The pillow's template (docs/template_plan.md, §2.1), counter-clockwise: ids 0..5.
PILLOW = [Vec(0, 0), Vec(1, 0), Vec(2, 0), Vec(2, 1), Vec(1, 1), Vec(0, 1)]


def loop(points: list[Vec]) -> Template:
    template = Template()
    for p in points:
        template = template.with_vertex_appended(p)
    return template.closed_loop()


class TestLabel:
    def test_valid(self) -> None:
        assert str(Label("CT", 12)) == "CT12"
        assert Label("A", 2) < Label("A", 10) < Label("B", 1)

    @pytest.mark.parametrize(
        ("name", "index"), [("", 1), ("ABC", 1), ("a", 1), ("Ж", 1), ("A1", 1), ("A", 0), ("A", 100)]
    )
    def test_invalid(self, name: str, index: int) -> None:
        with pytest.raises(ValueError, match=r"name|index"):
            Label(name, index)


class TestLoop:
    def test_closing_makes_one_white_face(self) -> None:
        template = loop(PILLOW)
        assert template.closed
        assert template.faces == (TemplateFace((0, 1, 2, 3, 4, 5)),)
        assert template.loop_sides()[-1] == (5, 0)
        assert template_area(template) == 2

    def test_a_clockwise_loop_is_turned_round(self) -> None:
        template = loop(list(reversed(PILLOW)))
        assert [v.id for v in template.vertices] == [0, 5, 4, 3, 2, 1]
        assert template.vertices[0].position == PILLOW[-1]
        assert template_area(template) == 2

    def test_no_area_while_open(self) -> None:
        assert template_area(Template().with_vertex_appended(Vec(1, 1))) is None

    def test_inserting_and_removing_a_vertex(self) -> None:
        template = loop(PILLOW).with_vertex_inserted(3, 4, Vec(F(3, 2), 1))
        assert [v.id for v in template.vertices] == [0, 1, 2, 3, 6, 4, 5]
        assert template.faces[0].corners == (0, 1, 2, 3, 6, 4, 5)
        assert template.without_vertex(6).faces == loop(PILLOW).faces
        with pytest.raises(ValueError, match="no loop side"):
            template.with_vertex_inserted(4, 3, Vec(0, 0))

    def test_ids_are_never_reused(self) -> None:
        template = loop(PILLOW).without_vertex(5).with_vertex_inserted(4, 0, Vec(0, F(1, 2)))
        assert template.vertices[-1].id == 6


class TestFolds:
    def test_a_fold_divides_its_face_and_both_keep_its_colour(self) -> None:
        template = loop(PILLOW).with_face_color(0, "#123456").with_fold(1, 4)
        assert template.folds == (Fold(1, 4),)
        assert [f.corners for f in template.faces] == [(1, 2, 3, 4), (4, 5, 0, 1)]
        assert {f.color for f in template.faces} == {"#123456"}

    def test_deleting_a_fold_gives_the_colour_of_the_face_on_its_left(self) -> None:
        template = loop(PILLOW).with_fold(1, 4).with_face_color(0, "#AA0000").with_face_color(1, "#00AA00")
        # Going from 1 to 4, the left is face 1 (4, 5, 0, 1).
        merged = template.without_fold(Fold(1, 4))
        assert merged.faces == (TemplateFace((4, 5, 0, 1, 2, 3), "#00AA00", 2),)  # its number too
        upwards = loop(PILLOW).with_fold(4, 1).with_face_color(0, "#AA0000").with_face_color(1, "#00AA00")
        # Going down from 4 to 1, the left is the other half: face 1 again, (1, 2, 3, 4), now that one.
        assert upwards.faces[1].corners == (1, 2, 3, 4)
        assert upwards.without_fold(Fold(4, 1)).faces[0].color == "#00AA00"

    def test_deleting_a_vertex_deletes_its_folds(self) -> None:
        template = loop(PILLOW).with_fold(1, 4).with_fold(1, 3)
        after = template.without_vertex(1)
        assert after.folds == ()
        assert [f.corners for f in after.faces] == [(3, 4, 5, 0, 2)]  # the same cycle as 0, 2, 3, 4, 5

    def test_faces_with_three_folds_from_one_vertex(self) -> None:
        template = loop(PILLOW).with_fold(0, 2).with_fold(0, 3).with_fold(0, 4)
        assert sorted(sorted(f.corners) for f in template.faces) == [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]]

    def test_the_face_at_a_point(self) -> None:
        template = loop(PILLOW).with_fold(1, 4)
        assert template.face_at(Vec(F(1, 2), F(1, 2))) == 1
        assert template.face_at(Vec(F(3, 2), F(1, 2))) == 0
        assert template.face_at(Vec(1, F(1, 2))) is None  # on the fold
        assert template.face_at(Vec(3, 3)) is None


class TestLabels:
    def test_labels_and_free_indices(self) -> None:
        template = loop(PILLOW).with_label(0, Label("P", 1)).with_label(2, Label("P", 3))
        assert template.label_owner(Label("P", 3)) == template.vertex(2)
        assert template.label_owner(Label("P", 2)) is None
        assert template.first_free_index("P") == 2
        assert template.first_free_index("Q") == 1
        assert template.with_label(0, None).vertex(0).label is None


class TestColourNumbers:
    """Every colour given numbers the face by the counter (docs/template_plan.md, §8.2): the basis of a face in
    pieces is the piece coloured least recently."""

    TURNED = Rigid90(2, Vec(4, 2))

    def test_the_counter_numbers_faces_and_goes_on(self) -> None:
        template = loop(PILLOW).with_fold(1, 4)
        assert template.next_number == 1 and [f.number for f in template.faces] == [None, None]
        template = template.with_face_color(1, "#AA0000").with_face_color(0, "#AA0000").with_face_color(1, "#AA0000")
        assert [f.number for f in template.faces] == [2, 3] and template.next_number == 4  # the same colour counts

    def test_a_colour_ties_the_hatch_to_the_grid_again(self) -> None:
        template = loop(PILLOW).with_face_color(0, "#AA0000")
        turned = template.with_hatches([self.TURNED])
        assert turned.faces[0].hatch == self.TURNED
        assert turned.with_face_color(0, "#AA0000").faces[0].hatch.is_identity()

    def test_a_fold_keeps_the_number_and_hatch_on_both_sides(self) -> None:
        template = loop(PILLOW).with_face_color(0, "#AA0000").with_hatches([self.TURNED]).with_fold(1, 4)
        assert [(f.number, f.hatch) for f in template.faces] == [(1, self.TURNED)] * 2


class TestFoldLines:
    """Fold lines of several segments (docs/template_plan.md, §8.4), in the pillow: 2 x 1, vertices 0..5 from (0, 0)
    counter-clockwise; 1 is (1, 0), 3 is (2, 1), 4 is (1, 1)."""

    BEND = Vec(F(5, 4), F(1, 2))

    def bent(self) -> Template:
        """From 1 up through a fold vertex (id 6) to 4: the pillow's middle, bent."""
        return loop(PILLOW).with_face_color(0, "#AA0000").with_fold_line(1, [self.BEND], 4)

    def test_a_line_through_a_fold_vertex_divides_its_face(self) -> None:
        template = self.bent()
        assert [v.position for v in template.fold_vertices] == [self.BEND] and template.next_id == 7
        assert template.folds == (Fold(1, 6), Fold(6, 4))
        assert sorted(f.corners for f in template.faces) == sorted([(1, 2, 3, 4, 6), (4, 5, 0, 1, 6)])
        assert all(f.color == "#AA0000" for f in template.faces) and template.vertex(6).position == self.BEND

    def test_deleting_the_fold_vertex_deletes_its_segments(self) -> None:
        template = self.bent().without_vertex(6)
        assert template.folds == () and template.fold_vertices == ()
        (face,) = template.faces
        k = face.corners.index(0)
        assert face.corners[k:] + face.corners[:k] == (0, 1, 2, 3, 4, 5)

    def test_deleting_a_segment_deletes_what_is_left_hanging(self) -> None:
        template = self.bent().without_fold(Fold(1, 6))
        assert template.folds == () and template.fold_vertices == () and len(template.faces) == 1

    def test_deleting_a_loop_vertex_deletes_its_line(self) -> None:
        template = self.bent().without_vertex(1)
        assert template.folds == () and template.fold_vertices == () and len(template.faces) == 1

    def test_a_fold_vertex_inserted_in_a_segment(self) -> None:
        template = loop(PILLOW).with_fold(1, 4).with_fold_vertex_inserted(Fold(1, 4), Vec(1, F(1, 2)))
        assert template.folds == (Fold(1, 6), Fold(6, 4))
        assert all(6 in f.corners for f in template.faces)

    def test_a_line_ending_at_another_lines_fold_vertex(self) -> None:
        template = self.bent().with_fold_line(6, [], 3)  # from the bend to (2, 1)
        assert len(template.faces) == 3
        after = template.without_fold(Fold(1, 6))  # 6 is still between two segments: nothing more goes
        assert after.folds == (Fold(6, 4), Fold(6, 3)) and len(after.faces) == 2
        assert after.fold_vertices == template.fold_vertices

    def test_labels_of_fold_vertices(self) -> None:
        template = self.bent().with_label(6, Label("M", 1))
        assert template.label_owner(Label("M", 1)) == template.vertex(6) and template.first_free_index("M") == 2
