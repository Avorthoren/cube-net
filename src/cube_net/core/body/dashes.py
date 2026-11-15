# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""How a straight segment of the body's surface is coloured as a dashed line (docs/idea.txt, colouring rule 2).

- A segment on an edge alternates the colours of the edge's 2 faces; any other segment alternates its face's colour
  with white.
- Dashes have a constant length, and the pattern is anchored to the surface, not to the net: both images
  (counterparts) of a cut, and all pieces of one edge, show exactly the same pattern.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cube_net.core.body.body import Body, Face
from cube_net.core.body.surface_point import SurfacePoint
from cube_net.core.geometry import Vec


@dataclass(frozen=True, slots=True)
class DashLayout:
    """Dash pattern of a segment.

    The dash at distance `s` from `start` (along the segment, towards the other end) has colour
    `faces[floor((offset + s) / dash) % 2]`, where the second entry may be None for white.
    """

    # Colour of even dashes, colour of odd dashes (None = white).
    faces: tuple[Face, Face | None]

    # The endpoint the pattern is measured from.
    start: SurfacePoint

    # Pattern position at `start`: its distance along the edge from the edge's first vertex (0 inside a face).
    offset: float


def dash_layout(body: Body, face: Face, a: Vec, b: Vec) -> DashLayout:
    """The dash pattern of the straight segment a-b (a != b), given by its ends' positions in the frame of `face`,
    the face it lies in (or one of the two, if it lies on an edge)."""
    if a == b:
        raise ValueError(f"degenerate segment at {a} in face {face}")
    p, q = SurfacePoint(body, face, a), SurfacePoint(body, face, b)
    side = body.side_through(face, a, b)
    if side is None:  # inside the face: measure from the canonically smaller endpoint
        start = min(p, q, key=lambda s: (s.face, s.local.x, s.local.y))
        return DashLayout((face, None), start, 0.0)

    edge = body.side_edge(side)
    first = edge.sides[0]
    if side != first:
        to_first = edge.transition(side)
        a, b = to_first.apply(a), to_first.apply(b)
    # Measured from the edge's alphabetically first vertex, in the frame of its first side.
    start_corner, end_corner = body.face(first.face).side_ends(first.index)
    start_name, _ = body.face(first.face).side_names(first.index)
    origin, other = (start_corner, end_corner) if start_name == min(edge.names) else (end_corner, start_corner)
    d = other - origin
    length2 = d.length_squared()
    ta, tb = (a - origin).dot(d) / length2, (b - origin).dot(d) / length2
    start, t = (p, ta) if ta < tb else (q, tb)
    f, *rest = sorted(edge.faces)
    return DashLayout((f, rest[0] if rest else f), start, float(t) * math.sqrt(length2))
