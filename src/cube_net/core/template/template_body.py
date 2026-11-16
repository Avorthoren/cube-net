# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`body_from_template`: the body a valid template describes (docs/template_plan.md, §4.4).

Its faces are the template's, numbered in the template's order, each in the template sheet's own frame. Their sides
are glued by name: a fold joins the two faces it divides (in place), a pair of counterparts on the loop joins its two
faces after a rotation by a multiple of 90 degrees. The starting net is the template's own net: every face where it
is. Its vertices are numbered so that each name's images are in the order of the template's indices, so A_2 in the
template is A_2 in a project of it.
"""

from cube_net.core.body import Body
from cube_net.core.geometry import Rigid90
from cube_net.core.template.template import Template
from cube_net.core.template.validation import validate


def body_from_template(template: Template) -> Body:
    """The body of a valid template (`validate` says so). `Body` checks everything again."""
    failure = validate(template)
    if failure is not None:
        raise ValueError(f"the template isn't valid: {failure.problem.value}")
    faces = {}
    for number, face in enumerate(template.faces, start=1):
        corners = [template.vertex(i) for i in face.corners]
        faces[number] = ([v.position for v in corners], [v.label.name for v in corners if v.label is not None])
    start = [(number, Rigid90.identity()) for number in faces]
    colors = [face.color for face in template.faces]
    order = sorted(template.vertices, key=lambda v: (v.label.name, v.label.index) if v.label else ("", 0))
    return Body(faces, start, colors, [v.position for v in order])
