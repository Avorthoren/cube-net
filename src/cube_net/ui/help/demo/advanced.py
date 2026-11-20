# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The script of Help -> Help's Advanced features animation, on the torus project's net (`torus_project`, the origin at
(44, 50)), with the coordinates hint.

A cut starts at (41, 61), on the edge of the hole; its next point is typed in Place a vertex's window: (42, 64), off
the net. The slope of the next segment is set (-4 : 1) and the mouse wanders about: the segment keeps its slope. The
end is typed too (y = -2 from the origin, at (46, 48)): the line ends where it reaches the net again. The half with the
counterpart of (53, 49.25)-(53, 51) is glued onto it and approved. Then the origin is moved: J_1, at x = -2.667 from it,
is given x = -8/3; the mouse rests on J_1 and on A_3, which show their coordinates from the moved origin.
"""

from fractions import Fraction as F

from PyQt6.QtCore import QSize

from cube_net.core.geometry import Box, Vec
from cube_net.ui.help.demo.steps import Move, Point, RightClick, Step, ToItem, Type, Wait, click
from cube_net.ui.sheet.sheet_context_menu import MOVE_ORIGIN, PLACE_VERTEX, SET_SLOPE

# The animation's size, and what it shows: the net before and after, and the cut's point off it.
SIZE = QSize(540, 720)
SHOWN = Box(Vec(39, F(228, 5)), Vec(55, F(335, 5)))

# Where the mouse is before the animation: left of the net.
START: Point = (39.6, 57.0)

# The cut's start, on the edge of the hole, and where the right clicks for its next points are (near where they go).
CUT_START: Point = (41.0, 61.0)
NEAR_OFF_NET: Point = (41.9, 63.5)
SLOPE_HERE: Point = (42.84, 62.23)
NEAR_END: Point = (45.6, 49.2)

# Where the mouse wanders while the slope is set: wide waves down the sheet.
WAVES: tuple[Point, ...] = ((48.5, 60.0), (40.5, 57.0), (48.5, 54.0), (41.0, 51.5))

# Where the edge is clicked to glue the other half onto it, and the approve button (in its middle).
GLUE: Point = (52.92, 50.04)
APPROVE: Point = (53.0, 50.125)

# J_1 and A_3 of the net after the cut (the names the project gives them).
J_1: Point = (41.333, 62.0)
A_3: Point = (40.0, 62.0)

ADVANCED: list[Step] = [
    Move(START, 0),
    Wait(500),
    Move(CUT_START, 900),
    Wait(300),
    *click(),
    Wait(500),
    Move(NEAR_OFF_NET, 700),
    Wait(400),
    RightClick(),
    Wait(600),
    ToItem(PLACE_VERTEX, 500),
    Wait(250),
    *click(),
    Wait(700),
    Type("14"),
    Wait(300),
    Type("\t\t", 300),
    Type("-2"),
    Wait(700),
    Type("\n"),
    Wait(800),
    Move(SLOPE_HERE, 600),
    Wait(400),
    RightClick(),
    Wait(600),
    ToItem(SET_SLOPE, 500),
    Wait(250),
    *click(),
    Wait(700),
    Type("-4"),
    Wait(300),
    Type("\t", 300),
    Type("1"),
    Wait(700),
    Type("\n"),
    Wait(600),
    Move(NEAR_END, 4000, WAVES),  # the segment keeps its slope wherever the mouse goes
    Wait(500),
    RightClick(),
    Wait(600),
    ToItem(PLACE_VERTEX, 500),
    Wait(250),
    *click(),
    Wait(700),
    Type("-2"),
    Wait(700),
    Type("\n"),
    Wait(1000),
    Move(GLUE, 1200),
    Wait(800),  # its counterpart blinks
    *click(),
    Wait(1200),
    Move(APPROVE, 400),
    Wait(400),
    *click(),
    Wait(1000),
    Move(J_1, 1200),
    Wait(400),
    RightClick(),
    Wait(600),
    ToItem(MOVE_ORIGIN, 500),
    Wait(250),
    *click(),
    Wait(700),
    Type("\t\t", 300),
    Type("-8"),
    Wait(300),
    Type("\t", 300),
    Type("3"),
    Wait(700),
    Type("\n"),
    Wait(600),
    Move(J_1, 700),
    Wait(3000),
    Move(A_3, 700),
    Wait(3000),
]
