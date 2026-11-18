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

from cube_net.core.body import Body, StartPiece, SurfacePoint
from cube_net.core.geometry import Vec
from cube_net.core.template.glued_faces import glue_faces
from cube_net.core.template.template import Template
from cube_net.core.template.validation import validate

# A loop of a face: its corners and their names.
type _Loop = list[tuple[Vec, str]]


def body_from_template(template: Template) -> Body:
    """The body of a valid template (`validate` says so). `Body` checks everything again."""
    return body_and_point_names(template)[0]


def body_and_point_names(template: Template) -> tuple[Body, dict[SurfacePoint, str]]:
    """The body of a valid template, and the names the template gives points of it that aren't its vertices (a
    labelled vertex in the middle of a straight edge: see `_drop_straight_vertices`), for a project to call them by."""
    failure = validate(template)
    if failure is not None:
        raise ValueError(f"the template isn't valid: {failure.problem.value}")

    def name(vertex: int) -> str:
        label = template.vertex(vertex).label
        assert label is not None  # it's valid
        return label.name

    glued = glue_faces(template).faces
    loops = {
        n: [[(c.position, name(c.vertex)) for c in loop] for loop in face.loops] for n, face in enumerate(glued, 1)
    }
    _drop_straight_vertices(loops)
    faces = {n: ([p for p, _ in face[0]], [m for _, m in face[0]]) for n, face in loops.items()}
    holes = {
        n: [([p for p, _ in loop], [m for _, m in loop]) for loop in face[1:]]
        for n, face in loops.items()
        if len(face) > 1
    }
    start = []
    for number, face in enumerate(glued, start=1):
        outer = [p for p, _ in loops[number][0]]
        for piece, frame in zip(face.pieces, face.frames, strict=True):
            corners = tuple(frame.apply(template.position(c)) for c in template.faces[piece].corners)
            whole = len(face.pieces) == 1 and number not in holes and list(corners) == outer
            start.append(StartPiece(number, frame.inverse(), None if whole else corners))
    colors = [face.color for face in glued]
    body = Body(faces, start, colors, None, holes)
    order = sorted(template.vertices, key=lambda v: (v.label.name, v.label.index) if v.label else ("", 0))
    keys: list[tuple[Vec, str]] = []
    for v in order:
        key = (v.position, name(v.id))
        if key not in keys:  # two images of a vertex at one point: one vertex of the net (it touches itself there)
            keys.append(key)
    names = set(body.vertex_names)
    vertex_order = [(p, n) for p, n in keys if n in names]  # the others aren't vertices of the body
    body = Body(faces, start, colors, vertex_order, holes)
    points: dict[SurfacePoint, str] = {}
    for number, face in enumerate(glued, start=1):
        for piece, frame in zip(face.pieces, face.frames, strict=True):
            for c in template.faces[piece].corners:
                if name(c) not in names:
                    points[SurfacePoint(body, number, frame.apply(template.position(c)))] = name(c)
    return body, points


def _drop_straight_vertices(loops: dict[int, list[_Loop]]) -> None:
    """A labelled vertex of the template that, the faces glued from their pieces, lies in the middle of a straight
    edge (two corners, both going straight on, between the same two vertices) isn't a vertex of the body: the two sides
    through it become one in each face (docs/template_plan.md §8.2: the line there is smooth). Not if that would make a
    side join a vertex to itself, a loop too short, or two edges of one name."""
    while True:
        corners: dict[str, list[tuple[int, int, int]]] = {}
        sides: dict[frozenset[str], int] = {}
        for number, face in loops.items():
            for li, loop in enumerate(face):
                for k, (_, m) in enumerate(loop):
                    corners.setdefault(m, []).append((number, li, k))
                    pair = frozenset((m, loop[(k + 1) % len(loop)][1]))
                    sides[pair] = sides.get(pair, 0) + 1
        dropped = next((m for m, at in corners.items() if _straight_through(loops, at, sides)), None)
        if dropped is None:
            return
        for number, li, k in sorted(corners[dropped], key=lambda c: -c[2]):
            del loops[number][li][k]


def _straight_through(
    loops: dict[int, list[_Loop]], at: list[tuple[int, int, int]], sides: dict[frozenset[str], int]
) -> bool:
    if len(at) != 2:
        return False
    ends: set[frozenset[str]] = set()
    for number, li, k in at:
        loop = loops[number][li]
        if len(loop) <= 3:
            return False
        (p, a), (c, _), (q, b) = loop[k - 1], loop[k], loop[(k + 1) % len(loop)]
        if (c - p).cross(q - c) != 0 or (c - p).dot(q - c) <= 0 or a == b:
            return False
        ends.add(frozenset((a, b)))
    return len(ends) == 1 and sides.get(next(iter(ends)), 0) == 0
