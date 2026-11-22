# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from cube_net.core.geometry import Vec
from cube_net.core.template import Template, TemplateEditor
from cube_net.core.template.loop_geometry import gaps_at, inside_gaps, pieces, rays_at, vertex_gaps, winding_number

# A square with a triangular hole whose top corner touches the top side at T = (2, 4): the loop passes T twice (T_1
# between (4, 4) and (3, 2), T_2 between (1, 2) and (0, 4)). One piece of paper, like a "C" whose tips touch.
TOUCHING_HOLE = [Vec(0, 0), Vec(4, 0), Vec(4, 4), Vec(2, 4), Vec(3, 2), Vec(1, 2), Vec(2, 4), Vec(0, 4)]
T = Vec(2, 4)


def loop(points: list[Vec]) -> Template:
    """The closed loop through `points`, as it is (no rules checked)."""
    template = Template()
    for p in points:
        template = template.with_vertex_appended(p)
    return template.closed_loop()


def drawn(points: list[Vec]) -> Template:
    """The closed loop through `points`, drawn in the editor (its rules checked)."""
    editor = TemplateEditor()
    for p in [*points, points[0]]:
        assert editor.add_point(p) is None
    return editor.template


def test_winding_numbers() -> None:
    template = loop([Vec(0, 0), Vec(2, 0), Vec(2, 2), Vec(0, 2)])
    assert winding_number(template, Vec(1, 1)) == 1
    assert winding_number(template, Vec(3, 1)) == 0


def test_an_ordinary_corner_has_one_gap_inside() -> None:
    template = loop([Vec(0, 0), Vec(2, 0), Vec(2, 2), Vec(0, 2)])
    assert sorted(gap.winding for gap in gaps_at(template, Vec(2, 2))) == [0, 1]
    (inside,) = inside_gaps(template, Vec(2, 2))
    assert inside.contains(Vec(-1, -1)) and not inside.contains(Vec(1, 1))


def test_a_point_the_loop_passes_twice() -> None:
    template = drawn(TOUCHING_HOLE)
    t1, t2 = 3, 6  # in the order drawn
    assert sorted(ray.vertex for ray in rays_at(template, T)) == [t1, t1, t2, t2]
    inside = inside_gaps(template, T)
    assert len(inside) == 2  # either side of the hole, below the top side
    assert [len(vertex_gaps(template, v)) for v in (t1, t2)] == [1, 1]
    (right,) = vertex_gaps(template, t1)
    assert right.contains(Vec(1, -1)) and not right.contains(Vec(0, -1))  # straight down: the hole


def test_pieces() -> None:
    square = [Vec(0, 0), Vec(2, 0), Vec(2, 2), Vec(0, 2)]
    assert pieces(loop(square)) == 1
    assert pieces(drawn(TOUCHING_HOLE)) == 1
    # Two squares meeting at a corner: two pieces.
    assert pieces(loop([Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(2, 1), Vec(2, 2), Vec(1, 2), Vec(1, 1), Vec(0, 1)])) == 2
    # A slit from the bottom side halfway up: one piece.
    slit = [Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(1, 0), Vec(2, 0), Vec(2, 2), Vec(0, 2)]
    assert pieces(loop(slit)) == 1
    # A slit from the bottom side all the way up to the top: two pieces.
    cut = [Vec(0, 0), Vec(1, 0), Vec(1, 2), Vec(1, 0), Vec(2, 0), Vec(2, 2), Vec(1, 2), Vec(0, 2)]
    assert pieces(loop(cut)) == 2
