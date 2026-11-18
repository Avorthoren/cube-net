# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`body_from_template`: the body a valid template describes (docs/template_plan.md, §4.4 and §8.2).

Its faces are the template's colours, numbered in the order of their first pieces in the template: the pieces of a
colour glued into one face, in the frame of its basis piece (`glue_faces`), with holes if it's a ring; a face of one
piece is that piece, in the template sheet's own frame. Their sides are glued by name: a fold joins the two faces it
divides (in place), a pair of counterparts on the loop joins its two faces after a rotation by a multiple of 90
degrees (a pair between pieces of one face is inside that face: no edge). The starting net is the template's own net:
every piece where it is. Its vertices are numbered so that each name's images are in the order of the template's
indices, so A_2 in the template is A_2 in a project of it (a vertex with only pieces of one face around it is a point
inside that face: it has no name in the body).
"""

from cube_net.core.body import Body, StartPiece
from cube_net.core.geometry import Vec
from cube_net.core.template.glued_faces import glue_faces
from cube_net.core.template.template import Template
from cube_net.core.template.validation import validate


def body_from_template(template: Template) -> Body:
    """The body of a valid template (`validate` says so). `Body` checks everything again."""
    failure = validate(template)
    if failure is not None:
        raise ValueError(f"the template isn't valid: {failure.problem.value}")

    def name(vertex: int) -> str:
        label = template.vertex(vertex).label
        assert label is not None  # it's valid
        return label.name

    faces, holes, start = {}, {}, []
    for number, face in enumerate(glue_faces(template).faces, start=1):
        outer, *inner = ([c.position for c in loop] for loop in face.loops)
        outer_names, *inner_names = ([name(c.vertex) for c in loop] for loop in face.loops)
        faces[number] = (outer, outer_names)
        if inner:
            holes[number] = list(zip(inner, inner_names, strict=True))
        for piece, frame in zip(face.pieces, face.frames, strict=True):
            if len(face.pieces) == 1 and not inner:
                start.append(StartPiece(number, frame.inverse()))  # the whole face
                continue
            corners = tuple(frame.apply(template.position(c)) for c in template.faces[piece].corners)
            start.append(StartPiece(number, frame.inverse(), corners))
    colors = [face.color for face in glue_faces(template).faces]
    body = Body(faces, start, colors, None, holes)
    order = sorted(template.vertices, key=lambda v: (v.label.name, v.label.index) if v.label else ("", 0))
    keys: list[tuple[Vec, str]] = []
    for v in order:
        key = (v.position, name(v.id))
        if key not in keys:  # two images of a vertex at one point: one vertex of the net (it touches itself there)
            keys.append(key)
    names = set(body.vertex_names)
    vertex_order = [(p, n) for p, n in keys if n in names]  # the others are points inside a face
    return Body(faces, start, colors, vertex_order, holes)
