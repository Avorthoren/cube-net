# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import math

from cube_net.core.geometry import Vec
from cube_net.core.template import Template, TemplateEditor
from cube_net.ui.template.corners import middle_angle, owned_arcs, shared, vertex_toward

# A square with a triangular hole whose top corner touches the top side at T = (2, 4): T_1 (id 3) and T_2 (id 6).
TOUCHING_HOLE = [Vec(0, 0), Vec(4, 0), Vec(4, 4), Vec(2, 4), Vec(3, 2), Vec(1, 2), Vec(2, 4), Vec(0, 4)]
T1, T2 = 3, 6


def touching_hole() -> Template:
    editor = TemplateEditor()
    for p in [*TOUCHING_HOLE, TOUCHING_HOLE[0]]:
        assert editor.add_point(p) is None
    return editor.template


def toward(template: Template, degrees: float) -> int | None:
    angle = math.radians(degrees)
    return vertex_toward(template, [T1, T2], (math.cos(angle), math.sin(angle)))


def test_each_owns_its_part_of_the_point() -> None:
    template = touching_hole()
    assert shared(template, T1) and shared(template, T2)
    assert toward(template, 340) == T1  # right of the hole, below the top side
    assert toward(template, 200) == T2  # left of it
    assert toward(template, 270) is None  # in the hole
    assert toward(template, 90) is None  # above the top side


def test_arcs_and_where_labels_go() -> None:
    template = touching_hole()
    total = sum(end - start for start, end in owned_arcs(template, T1) + owned_arcs(template, T2))
    assert math.isclose(total, 2 * math.atan2(2, 1))  # both wedges between the top side and the hole's sides
    label = middle_angle(owned_arcs(template, T1))
    assert label is not None and math.isclose(math.degrees(label) % 360, 360 - math.degrees(math.atan2(2, 1)) / 2)
    assert not shared(template, 0)
