# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fixtures for all core tests: bodies other than the cube (docs/template_plan.md, §2.1)."""

from fractions import Fraction as F

import pytest

from cube_net.core.body import Body
from cube_net.core.geometry import Rigid90, Vec
from cube_net.core.template import Label, Template, TemplateEditor

IDENTITY = Rigid90.identity()


@pytest.fixture
def pillow() -> Body:
    """Two unit squares glued along all 4 sides: faces 1 and 2 share the edges PQ, QR, RS and SP. Its template:
    P_1 (0,0), Q_1 (1,0), P_2 (2,0), S_2 (2,1), R_1 (1,1), S_1 (0,1), with the fold Q_1-R_1."""
    return Body(
        {
            1: ((Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(0, 1)), ("P", "Q", "R", "S")),
            2: ((Vec(1, 0), Vec(2, 0), Vec(2, 1), Vec(1, 1)), ("Q", "P", "S", "R")),
        },
        [(1, IDENTITY), (2, IDENTITY)],
    )


@pytest.fixture
def flat_pillow() -> Body:
    """The pillow's template without its fold: one face glued to itself along 3 pairs of its sides."""
    corners = (Vec(0, 0), Vec(1, 0), Vec(2, 0), Vec(2, 1), Vec(1, 1), Vec(0, 1))
    return Body({1: (corners, ("P", "Q", "P", "S", "R", "S"))}, [(1, IDENTITY)])


def flat_body(faces: dict[int, list[tuple[int, int, str]]]) -> Body:
    """A body given by its starting net: every face's corners on the sheet as (x, y, name), counter-clockwise, all
    placed by the identity (so each face's frame is the sheet's)."""
    return Body(
        {
            n: (tuple(Vec(x, y) for x, y, _ in corners), tuple(name for *_, name in corners))
            for n, corners in faces.items()
        },
        [(n, IDENTITY) for n in faces],
    )


@pytest.fixture
def cube_with_a_hole() -> Body:
    """The built-in Cube with a hole (a torus): one of its faces is a ring, with a seam."""
    from cube_net.core.project.builtin_templates import cube_with_a_hole as template
    from cube_net.core.project.from_template import project_from_template

    return project_from_template(template()).state.net.body


@pytest.fixture
def long_box() -> Body:
    """A 1x1x2 box: the 4 long sides in a row, the bottom below the front, the top above it."""
    return flat_body(
        {
            1: [(0, 0, "A"), (1, 0, "B"), (1, 2, "F"), (0, 2, "E")],
            2: [(1, 0, "B"), (2, 0, "C"), (2, 2, "G"), (1, 2, "F")],
            3: [(2, 0, "C"), (3, 0, "D"), (3, 2, "H"), (2, 2, "G")],
            4: [(3, 0, "D"), (4, 0, "A"), (4, 2, "E"), (3, 2, "H")],
            5: [(0, -1, "D"), (1, -1, "C"), (1, 0, "B"), (0, 0, "A")],
            6: [(0, 2, "E"), (1, 2, "F"), (1, 3, "G"), (0, 3, "H")],
        }
    )


@pytest.fixture
def l_prism() -> Body:
    """3 unit cubes in an L, 1 high: L-shaped bottom (face 1, with a reflex corner) and top (face 2), 6 sides; the
    two sides at the inner corner (5 and 6) hang off side 4."""
    return flat_body(
        {
            1: [(0, 0, "P0"), (2, 0, "P1"), (2, 1, "P2"), (1, 1, "P3"), (1, 2, "P4"), (0, 2, "P5")],
            2: [(0, -3, "T5"), (1, -3, "T4"), (1, -2, "T3"), (2, -2, "T2"), (2, -1, "T1"), (0, -1, "T0")],
            3: [(0, -1, "T0"), (2, -1, "T1"), (2, 0, "P1"), (0, 0, "P0")],
            4: [(2, 0, "P1"), (3, 0, "T1"), (3, 1, "T2"), (2, 1, "P2")],
            5: [(2, 1, "P2"), (3, 1, "T2"), (3, 2, "T3"), (2, 2, "P3")],
            6: [(2, 2, "P3"), (3, 2, "T3"), (3, 3, "T4"), (2, 3, "P4")],
            7: [(0, 2, "P5"), (1, 2, "P4"), (1, 3, "T4"), (0, 3, "T5")],
            8: [(-1, 0, "T0"), (0, 0, "P0"), (0, 2, "P5"), (-1, 2, "T5")],
        }
    )


@pytest.fixture
def pinwheel_box() -> Body:
    """A 2x2x1 box whose top is cut into 4 quarters around its centre M, each attached to a different side: M is a
    vertex of 4 faces, with 4 images in the starting net."""
    return flat_body(
        {
            1: [(0, 0, "P"), (2, 0, "Q"), (2, 2, "R"), (0, 2, "T")],
            2: [(0, -1, "A"), (1, -1, "S"), (2, -1, "B"), (2, 0, "Q"), (0, 0, "P")],
            3: [(2, 0, "Q"), (3, 0, "B"), (3, 1, "E"), (3, 2, "C"), (2, 2, "R")],
            4: [(0, 2, "T"), (2, 2, "R"), (2, 3, "C"), (1, 3, "N"), (0, 3, "D")],
            5: [(-1, 0, "A"), (0, 0, "P"), (0, 2, "T"), (-1, 2, "D"), (-1, 1, "W")],
            6: [(1, -2, "M"), (2, -2, "E"), (2, -1, "B"), (1, -1, "S")],
            7: [(3, 1, "E"), (4, 1, "M"), (4, 2, "N"), (3, 2, "C")],
            8: [(0, 3, "D"), (1, 3, "N"), (1, 4, "M"), (0, 4, "W")],
            9: [(-2, 0, "S"), (-1, 0, "A"), (-1, 1, "W"), (-2, 1, "M")],
        }
    )


# The cube's cross (docs/idea.txt) as a template: its perimeter counter-clockwise from A_3, labelled as there.
CROSS_LOOP = [
    (11, 10, "A", 3),
    (12, 10, "B", 3),
    (12, 11, "F", 1),
    (12, 12, "G", 1),
    (13, 12, "F", 2),
    (13, 13, "B", 2),
    (12, 13, "D", 1),
    (12, 14, "B", 1),
    (11, 14, "A", 1),
    (11, 13, "C", 1),
    (10, 13, "A", 2),
    (10, 12, "E", 2),
    (11, 12, "H", 1),
    (11, 11, "E", 1),
]

# Its 5 folds, by their ends' labels.
CROSS_FOLDS = [("C1", "D1"), ("H1", "G1"), ("E1", "F1"), ("C1", "H1"), ("D1", "G1")]

# Its faces' colours: the cube's.
CROSS_COLORS = ("#0057B8", "#F28E00", "#008A4B", "#8B45B5", "#E50055", "#00A6D6")


def drawn_template(loop: list[tuple[int, int, str, int]], folds: list[tuple[str, str]]) -> TemplateEditor:
    """A template drawn in the editor: the loop, closed, its labels, then its folds, then a colour for each face."""
    editor = TemplateEditor()
    for x, y, *_ in [*loop, loop[0]]:
        assert editor.add_point(Vec(x, y)) is None
    for vertex_id, (_, _, name, index) in enumerate(loop):  # ids go in the order the points were drawn
        assert editor.set_label(vertex_id, Label(name, index)) is None
    by_label = {str(v.label): v.id for v in editor.template.vertices}
    for start, end in folds:
        assert editor.add_fold(by_label[start], by_label[end]) is None
    for index in range(len(editor.template.faces)):  # a face needs a colour to be valid: a different one each
        editor.set_face_color(index, f"#{40 * index % 256:02X}80{255 - 40 * index % 256:02X}")
    return editor


@pytest.fixture
def cross_template() -> Template:
    """The cross, its faces coloured like the cube's (face k of the cube where its colour is)."""
    template = drawn_template(CROSS_LOOP, CROSS_FOLDS).template
    centres = {1: Vec(23, 27), 2: Vec(23, 25), 3: Vec(25, 25), 4: Vec(21, 25), 5: Vec(23, 21), 6: Vec(23, 23)}
    for face, centre in centres.items():
        index = template.face_at(centre / 2)
        assert index is not None
        template = template.with_face_color(index, CROSS_COLORS[face - 1])
    return template


@pytest.fixture
def draw() -> object:
    """`drawn_template`, for tests that draw their own templates."""
    return drawn_template


@pytest.fixture
def cross_drawing() -> tuple[list[tuple[int, int, str, int]], list[tuple[str, str]]]:
    """The cross's loop and folds, to draw again (with changes)."""
    return list(CROSS_LOOP), list(CROSS_FOLDS)


# The pinwheel box (`pinwheel_box`) as a template, 10 units further right and up: M has 4 instances glued in a ring.
PINWHEEL_LOOP = [
    (10, 10, "P", 1),
    (10, 9, "A", 1),
    (11, 9, "S", 1),
    (11, 8, "M", 1),
    (12, 8, "E", 1),
    (12, 9, "B", 1),
    (12, 10, "Q", 1),
    (13, 10, "B", 2),
    (13, 11, "E", 2),
    (14, 11, "M", 2),
    (14, 12, "N", 1),
    (13, 12, "C", 1),
    (12, 12, "R", 1),
    (12, 13, "C", 2),
    (11, 13, "N", 2),
    (11, 14, "M", 3),
    (10, 14, "W", 1),
    (10, 13, "D", 1),
    (10, 12, "T", 1),
    (9, 12, "D", 2),
    (9, 11, "W", 2),
    (8, 11, "M", 4),
    (8, 10, "S", 2),
    (9, 10, "A", 2),
]

PINWHEEL_FOLDS = [
    ("P1", "Q1"),
    ("Q1", "R1"),
    ("R1", "T1"),
    ("T1", "P1"),
    ("S1", "B1"),
    ("E2", "C1"),
    ("N2", "D1"),
    ("W2", "A2"),
]


@pytest.fixture
def pinwheel_template() -> Template:
    return drawn_template(PINWHEEL_LOOP, PINWHEEL_FOLDS).template


# The cross (doubled), the bottom half of face 5 moved onto the top of face 1 (its A-B side on face 1's): face 5 is in
# two pieces, glued along X-Y; X and Y are the middles of its sides (and of the sides glued to them).
HALF_MOVED = [
    (22, 21, "X", 1), (24, 21, "Y", 1), (24, 22, "F", 1), (24, 24, "G", 1), (26, 24, "F", 2), (26, 25, "Y", 3),
    (26, 26, "B", 2), (24, 26, "D", 1), (24, 28, "B", 1), (24, 29, "Y", 2), (22, 29, "X", 2), (22, 28, "A", 1),
    (22, 26, "C", 1), (20, 26, "A", 2), (20, 25, "X", 3), (20, 24, "E", 2), (22, 24, "H", 1), (22, 22, "E", 1),
]  # fmt: skip
HALF_MOVED_FOLDS = [("C1", "D1"), ("H1", "G1"), ("E1", "F1"), ("C1", "H1"), ("D1", "G1"), ("A1", "B1")]


@pytest.fixture
def half_moved_template() -> Template:
    """The cross (doubled), the bottom half of face 5 moved onto the top of face 1, both halves in one colour."""
    editor = drawn_template(HALF_MOVED, HALF_MOVED_FOLDS)
    bottom, top = editor.template.face_at(Vec(23, F(43, 2))), editor.template.face_at(Vec(23, F(57, 2)))
    assert bottom is not None and top is not None
    color = editor.template.faces[bottom].color
    assert color is not None
    editor.set_face_color(top, color)
    return editor.template
