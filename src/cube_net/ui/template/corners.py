# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Which vertex the mouse means where several are at one point (a loop that touches itself, docs/template_plan.md,
§8.1), and the part of the point's circle each one owns.

Around the point, the net is in some of the gaps between the loop's rays (`loop_geometry.inside_gaps`). A vertex owns
the part of a gap next to its own ray: all of it if the gap is between two of its own rays (as at any other vertex), up
to the middle if the other ray is another vertex's. The direction from the point to the mouse picks the owner of that
part; the parts outside the net belong to none. Angles are in radians, counter-clockwise from the sheet's x axis, in
floats: this is for the mouse and the drawing, nothing exact depends on it.
"""

import math
from collections.abc import Sequence

from cube_net.core.geometry import Vec
from cube_net.core.template import Template
from cube_net.core.template.loop_geometry import Gap, Ray, inside_gaps

type Arc = tuple[float, float]


def shared(template: Template, vertex_id: int) -> bool:
    """Is another vertex at the same point (on a closed loop: only then do the parts matter)?"""
    q = template.position(vertex_id)
    return template.closed and any(v.position == q and v.id != vertex_id for v in template.vertices)


def owned_arcs(template: Template, vertex_id: int) -> list[Arc]:
    """The arcs of the circle round the vertex's point that are its own (start, end: counter-clockwise, end > start)."""
    arcs = []
    for gap in inside_gaps(template, template.position(vertex_id)):
        start, end = _angles(gap)
        first, last = _owner(gap.start), _owner(gap.end)
        if (first == vertex_id and last in (vertex_id, None)) or (last == vertex_id and first is None):
            arcs.append((start, end))
        elif first == vertex_id:
            arcs.append((start, (start + end) / 2))
        elif last == vertex_id:
            arcs.append(((start + end) / 2, end))
    return arcs


def vertex_toward(template: Template, candidates: Sequence[int], direction: tuple[float, float]) -> int | None:
    """Of the vertices at one point, the one owning the direction (dx, dy) from it; None outside the net."""
    angle = math.atan2(direction[1], direction[0])
    for vertex_id in candidates:
        for start, end in owned_arcs(template, vertex_id):
            if _within(angle, start, end):
                return vertex_id
    return None


def middle_angle(arcs: Sequence[Arc]) -> float | None:
    """The direction halfway along the largest arc (for a label), if there's any."""
    if not arcs:
        return None
    start, end = max(arcs, key=lambda arc: arc[1] - arc[0])
    return (start + end) / 2


def _angles(gap: Gap) -> tuple[float, float]:
    start = _angle(gap.start_direction)
    end = _angle(gap.end_direction)
    while end <= start:
        end += 2 * math.pi
    return start, end


def _angle(d: Vec) -> float:
    return math.atan2(float(d.y), float(d.x))


def _owner(rays: Sequence[Ray]) -> int | None:
    """The vertex whose ray bounds the gap there (rays of sides passing through the point belong to none)."""
    return next((ray.vertex for ray in rays if ray.vertex is not None), None)


def _within(angle: float, start: float, end: float) -> bool:
    while angle < start:
        angle += 2 * math.pi
    while angle >= start + 2 * math.pi:
        angle -= 2 * math.pi
    return start <= angle <= end
