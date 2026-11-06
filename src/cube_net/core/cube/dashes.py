"""How a straight segment of the cube surface is coloured as a dashed line (docs/idea.txt, colouring rule 2).

- A segment on a cube edge alternates the colours of the edge's 2 faces; any other segment alternates its face's
  colour with white.
- Dashes have a constant length (`DASH_LENGTH`), and the pattern is anchored to the cube surface, not to the net:
  both images (counterparts) of a cut, and all pieces of one cube edge, show exactly the same pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from cube_net.core.cube.surface_point import SurfacePoint
from cube_net.core.cube.topology import CUBE, Face
from cube_net.core.geometry import Vec

# So that a whole cube edge has 10 dashes of each of its 2 colours.
DASH_LENGTH = Fraction(1, 20)


@dataclass(frozen=True, slots=True)
class DashLayout:
    """Dash pattern of the segment p-q.

    The dash at distance `s` from `start` (along the segment, towards the other end) has colour
    `faces[floor((offset + s) / DASH_LENGTH) % 2]`, where the second entry may be None for white.
    """

    # Colour of even dashes, colour of odd dashes (None = white).
    faces: tuple[Face, Face | None]

    # The endpoint the pattern is measured from.
    start: SurfacePoint

    # Pattern position at `start`.
    offset: Fraction


def dash_layout(p: SurfacePoint, q: SurfacePoint) -> DashLayout:
    """The dash pattern of the straight cube-surface segment p-q (p != q, both on one face)."""
    if p == q:
        raise ValueError(f"degenerate segment at {p}")
    common = p.faces & q.faces
    if not common:
        raise ValueError(f"segment {p} - {q} does not lie on a single face")

    if len(common) == 2:  # along a cube edge: measure from the edge's first vertex (alphabetically)
        f, g = sorted(common)
        first_vertex = min(CUBE.shared_edge(f, g))
        origin = CUBE.corner_local(f, first_vertex)
        dp = _axis_distance(p.local_in(f), origin)
        dq = _axis_distance(q.local_in(f), origin)
        start, offset = (p, dp) if dp < dq else (q, dq)
        return DashLayout((f, g), start, offset)

    # Inside one face (distinct points share at most 2 faces): measure from the canonically smaller endpoint.
    face = min(common)

    start = min(p, q, key=lambda s: (s.face, s.local.x, s.local.y))
    return DashLayout((face, None), start, Fraction(0))


def _axis_distance(a: Vec, b: Vec) -> Fraction:
    """Distance between two points on one axis-parallel line (a cube edge in a face frame)."""
    return abs(a.x - b.x) + abs(a.y - b.y)
