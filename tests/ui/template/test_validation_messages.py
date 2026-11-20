# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from cube_net.core.template import ValidationFailure, ValidationProblem
from cube_net.ui import palette
from cube_net.ui.template.validation_messages import (
    color_square,
    failure_text,
    groups_listed,
    listed,
    shown_name,
    subscripted,
)

P = ValidationProblem


def test_lists() -> None:
    assert listed(["A-CT"]) == "A-CT"
    assert listed(["A-CT", "AS-QC", "Z-R"]) == "A-CT, AS-QC and Z-R"
    assert groups_listed([("A1-B1", "A1-B3"), ("S2-Q3", "S1-Q1", "S3-Q5")]) == "A1-B1 and A1-B3; S2-Q3 and S1-Q1, S3-Q5"


def test_indices_are_subscripts() -> None:
    assert subscripted("A1-GF12") == "A<sub>1</sub>-GF<sub>12</sub>"
    assert subscripted("S2") == "S<sub>2</sub>"
    assert subscripted("A-CT") == "A-CT"


def test_a_segment_is_never_broken_at_its_hyphen() -> None:
    assert shown_name("GG1-C1") == "GG<sub>1</sub>\u2011C<sub>1</sub>"
    assert shown_name("A-CT") == "A\u2011CT"
    assert shown_name("S2") == "S<sub>2</sub>"


def test_a_message_with_indices_is_rich_text() -> None:
    from PyQt6.QtCore import Qt

    assert Qt.mightBeRichText(failure_text(ValidationFailure(P.FACE_TOUCHES_ITSELF, ("S2",))))


@pytest.mark.parametrize(
    ("failure", "text"),
    [
        (ValidationFailure(P.UNLABELLED), "Some vertices don't have assigned labels. Name each vertex."),
        (
            ValidationFailure(P.SELF_EDGE, ("A1-A3", "BV2-BV1")),
            "You have edges that connect a vertex to itself, which is impossible: A<sub>1</sub>\u2011A<sub>3</sub> and "
            "BV<sub>2</sub>\u2011BV<sub>1</sub>.",
        ),
        (
            ValidationFailure(P.NO_COUNTERPART, ("A-CT",)),
            "Segment A\u2011CT doesn't have a counterpart. Each segment should appear exactly twice, because that's "
            "what gluing implies.",
        ),
        (
            ValidationFailure(P.CUT_AND_FOLD, groups=(("A1-B1", "A1-B3"),)),
            "You have a cut that also exists as a fold, which is impossible: A<sub>1</sub>\u2011B<sub>1</sub> and "
            "A<sub>1</sub>\u2011B<sub>3</sub>.",
        ),
        (
            ValidationFailure(P.SAME_FOLDS, groups=(("A1-B1", "A2-B2"), ("S1-Q1", "S2-Q3", "S3-Q2"))),
            "You have folds that connect the same vertices, which is impossible: A<sub>1</sub>\u2011B<sub>1</sub> and "
            "A<sub>2</sub>\u2011B<sub>2</sub>; S<sub>1</sub>\u2011Q<sub>1</sub>, S<sub>2</sub>\u2011Q<sub>3</sub> and "
            "S<sub>3</sub>\u2011Q<sub>2</sub>.",
        ),
        (ValidationFailure(P.NOT_GLUED, ("A",)), "Vertex A is not glued to itself, which is impossible."),
        (
            ValidationFailure(P.NOT_GLUED, ("A", "Q", "GG")),
            "Some of your vertices are not glued to themselves, which is impossible: A, Q and GG.",
        ),
        (ValidationFailure(P.TOO_FEW_FACES), "Net should have at least 4 faces."),
        (
            ValidationFailure(P.INDEX_GAPS, ("A", "HV")),
            "Indices for vertices A and HV have gaps. Reindex automatically?",
        ),
    ],
)
def test_texts(failure: ValidationFailure, text: str) -> None:
    assert failure_text(failure) == text


def test_every_problem_has_a_text() -> None:
    for problem in ValidationProblem:
        assert failure_text(ValidationFailure(problem, ("A", "B"), (("A1-B1", "A1-B2"),), colors=("#FFFFFF",)))


@pytest.mark.parametrize(
    ("problem", "one", "many"),
    [
        (
            ValidationProblem.PIECES_APART,
            "Pieces of this face aren't glued together: {}.",
            "Pieces of some faces aren't glued together: {}.",
        ),
        (
            ValidationProblem.SELF_INTERSECTING,
            "This face self-intersects after gluing: {}.",
            "Some faces self-intersect after gluing: {}.",
        ),
    ],
)
def test_faces_shown_as_squares_of_their_colours(problem: ValidationProblem, one: str, many: str, qapp: object) -> None:
    a, b, c = (color_square(color) for color in ("#8B45B5", "#FFFFFF", "#008A4B"))
    assert failure_text(ValidationFailure(problem, colors=("#8B45B5",))) == one.format(a)
    text = failure_text(ValidationFailure(problem, colors=("#8B45B5", "#FFFFFF", "#008A4B")))
    assert text == many.format(f"{a}, {b} and {c}")


def test_a_square_is_an_image_of_its_colour(qapp: object) -> None:
    import base64

    from PyQt6.QtGui import QImage

    square = color_square("#8B45B5")
    assert square.startswith('<img src="data:image/png;base64,') and square.endswith('">')
    image = QImage.fromData(base64.b64decode(square.split(",", 1)[1][:-2]))
    middle = image.pixelColor(image.width() // 2, image.height() // 2)
    assert middle.name().upper() == "#8B45B5"
    assert image.pixelColor(0, 0).name() == palette.COLOR_SQUARE_OUTLINE.name()


def test_folds_of_one_colour() -> None:
    failure = ValidationFailure(ValidationProblem.SAME_COLOR_FOLD, ("A1-B1",))
    assert failure_text(failure) == (
        "You have a fold between faces of the same color: A<sub>1</sub>\u2011B<sub>1</sub>. A fold separates two "
        "faces: give them different colors."
    )
