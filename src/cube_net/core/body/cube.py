# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`CUBE`: the unit cube as a `Body`, with the cross from docs/idea.txt as its starting net.

Every face is the unit square `(u, v)` in `[0, 1]^2` of its own frame, seen from outside the cube, corners
counter-clockwise. Frames are chosen so that in the default net every face is placed by a pure translation, e.g.
face 2 local `(0, 0)` is sheet `(11, 12)`. The tables below are just that net written down; everything else (which
faces meet at an edge or a vertex, how one face's frame continues into its neighbour's) is derived by `Body`.
"""

from collections.abc import Mapping
from types import MappingProxyType

from cube_net.core.body.body import Body, Face, VertexName
from cube_net.core.geometry import Rigid90, Vec

FACES: tuple[Face, ...] = (1, 2, 3, 4, 5, 6)

VERTICES: tuple[VertexName, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")

# The corners of every face's local square, counter-clockwise, starting at the origin.
LOCAL_CORNERS: tuple[Vec, Vec, Vec, Vec] = (Vec(0, 0), Vec(1, 0), Vec(1, 1), Vec(0, 1))

# The vertex at each of `LOCAL_CORNERS` of each face, read off the default net in docs/idea.txt.
FACE_CORNERS: Mapping[Face, tuple[VertexName, VertexName, VertexName, VertexName]] = MappingProxyType(
    {
        1: ("C", "D", "B", "A"),
        2: ("H", "G", "D", "C"),
        3: ("G", "F", "B", "D"),
        4: ("E", "H", "C", "A"),
        5: ("A", "B", "F", "E"),
        6: ("E", "F", "G", "H"),
    }
)

# Sheet position of local (0, 0) of each face in the default net (H_1 = (11, 12), see docs/idea.txt).
DEFAULT_FACE_ORIGINS: Mapping[Face, Vec] = MappingProxyType(
    {
        1: Vec(11, 13),
        2: Vec(11, 12),
        3: Vec(12, 12),
        4: Vec(10, 12),
        5: Vec(11, 10),
        6: Vec(11, 11),
    }
)

# Faces are added to the default net in this order, so vertex ids (creation order) number the images of each cube
# vertex exactly as in docs/idea.txt: A_1 = (11, 14), A_2 = (10, 13), A_3 = (11, 10), E_1 = (11, 11), E_2 = (10, 12).
BUILD_ORDER: tuple[Face, ...] = (1, 2, 6, 3, 4, 5)


def cube_body() -> Body:
    """The cube built from the tables above."""
    return Body(
        {face: (LOCAL_CORNERS, FACE_CORNERS[face]) for face in FACES},
        [(face, Rigid90.translation(DEFAULT_FACE_ORIGINS[face])) for face in BUILD_ORDER],
    )


# The one cube.
CUBE = cube_body()
