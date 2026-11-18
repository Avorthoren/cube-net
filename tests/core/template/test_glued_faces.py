# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace

import pytest

from cube_net.core.geometry import Rigid90
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.template import Template, validate
from cube_net.core.template.glued_faces import aligned_hatches, basis_piece, glue_faces

# The torus's purple: two pieces, glued along N-T and L-R into a ring.
PURPLE = "#8B45B5"


@pytest.fixture
def torus() -> Template:
    """The built-in torus as if never validated or coloured since the counter is kept: no numbers, hatches tied to the
    grid."""
    template = cube_with_a_hole().state.template
    faces = tuple(replace(f, number=None, hatch=Rigid90.identity()) for f in template.faces)
    return replace(template, faces=faces, next_number=1)


def purple_pieces(template: Template) -> list[int]:
    return [i for i, face in enumerate(template.faces) if face.color == PURPLE]


def numbered(template: Template, numbers: dict[int, int]) -> Template:
    faces = tuple(replace(f, number=numbers.get(i, f.number)) for i, f in enumerate(template.faces))
    return replace(template, faces=faces, next_number=max(numbers.values()) + 1)


def test_the_torus_has_two_rings(torus: Template) -> None:
    gluing = glue_faces(torus)
    assert len(gluing.faces) == 10 and not gluing.apart and not gluing.broken
    rings = [face for face in gluing.faces if len(face.loops) == 2]
    assert {face.color for face in rings} == {PURPLE, "#008A4B"}
    assert all(len(face.pieces) == 2 and face.frames[0] == Rigid90.identity() for face in rings)


def test_the_basis_is_the_piece_coloured_least_recently(torus: Template) -> None:
    first, second = purple_pieces(torus)
    assert basis_piece(torus, [first, second]) == first  # neither numbered: the template's order
    later = numbered(torus, {first: 5, second: 3})
    assert basis_piece(later, [first, second]) == second
    purple = next(face for face in glue_faces(later).faces if face.color == PURPLE)
    assert purple.pieces == (second, first) and purple.frames[0] == Rigid90.identity()
    unnumbered = numbered(torus, {second: 3})
    assert basis_piece(unnumbered, [first, second]) == first  # coloured before the counter: earlier


def test_aligned_hatches_continue_the_basis_piece(torus: Template) -> None:
    first, second = purple_pieces(torus)
    aligned = aligned_hatches(torus)
    assert aligned.faces[first].hatch.is_identity()
    purple = next(face for face in glue_faces(torus).faces if face.color == PURPLE)
    assert aligned.faces[second].hatch == purple.frames[1] and not purple.frames[1].is_identity()
    assert sum(not f.hatch.is_identity() for f in aligned.faces) == 2  # a piece of the purple, one of the green
    assert validate(aligned) is None and aligned_hatches(aligned) == aligned
