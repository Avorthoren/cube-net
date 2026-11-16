# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from cube_net.core.template import ValidationFailure, ValidationProblem
from cube_net.ui.template.validation_messages import failure_text, groups_listed, listed

P = ValidationProblem


def test_lists() -> None:
    assert listed(["A-CT"]) == "A-CT"
    assert listed(["A-CT", "AS-QC", "Z-R"]) == "A-CT, AS-QC and Z-R"
    assert groups_listed([("A1-B1", "A1-B3"), ("S2-Q3", "S1-Q1", "S3-Q5")]) == "A1-B1 and A1-B3; S2-Q3 and S1-Q1, S3-Q5"


@pytest.mark.parametrize(
    ("failure", "text"),
    [
        (ValidationFailure(P.UNLABELLED), "Some vertices don't have assigned labels. Name each vertex."),
        (
            ValidationFailure(P.SELF_EDGE, ("A1-A3", "BV2-BV1")),
            "You have edges that connect a vertex to itself, which is impossible: A1-A3 and BV2-BV1.",
        ),
        (
            ValidationFailure(P.NO_COUNTERPART, ("A-CT",)),
            "Segment A-CT doesn't have a counterpart. Each segment should appear exactly twice, because that's what "
            "gluing implies.",
        ),
        (
            ValidationFailure(P.CUT_AND_FOLD, groups=(("A1-B1", "A1-B3"),)),
            "You have a cut that also exists as a fold, which is impossible: A1-B1 and A1-B3.",
        ),
        (
            ValidationFailure(P.SAME_FOLDS, groups=(("A1-B1", "A2-B2"), ("S1-Q1", "S2-Q3", "S3-Q2"))),
            "You have folds that connect the same vertices, which is impossible: A1-B1 and A2-B2; S1-Q1, S2-Q3 and "
            "S3-Q2.",
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
        assert failure_text(ValidationFailure(problem, ("A", "B"), (("A1-B1", "A1-B2"),)))
