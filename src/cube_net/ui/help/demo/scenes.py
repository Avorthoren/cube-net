# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The scripts of the animations of Help -> Help, on the default net (the cross: the column 11..12 x 10..14 with the
arm 10..13 x 12..13).

1. `CUT`: a cut of two segments from A_1 to the middle of A_3-B_3.
2. `ADJUST`, from where `CUT` ends: the end is dragged along the perimeter onto G_1-F_1; a new point in the middle of
   the first segment is dragged aside (the line zigzags); one more point is added, dragged almost to E_1 and deleted
   with CTRL.
3. From where `ADJUST` ends, side by side: `GLUE_GOOD` glues onto the end of the right arm (F_2-B_2) and approves;
   `GLUE_BAD` glues onto the bottom of the right arm, which makes the halves overlap, and the button cancels it.
"""

from PyQt6.QtCore import Qt

from cube_net.ui.help.demo.steps import Keys, Move, Point, Press, Release, Step, Wait, click

# Where the mouse is before the first animation: to the right of the net, below the arm.
START: Point = (13.4, 10.6)

# A little inside a cut (units): within its hitbox at any size of the animations.
INSIDE = 0.03

# The points of the cut.
A_1: Point = (11.0, 14.0)
TURN: Point = (11.6, 12.2)
END: Point = (11.5, 10.0)

# Where `ADJUST` moves the end to (on G_1-F_1, twice as close to F_1 as to G_1), and the point it adds and drags aside.
NEW_END: Point = (12.0, 11 + 1 / 3)
ADDED: Point = ((A_1[0] + TURN[0]) / 2, (A_1[1] + TURN[1]) / 2)
ASIDE: Point = (11.75, 13.45)

# The point added and deleted again: in the middle of the last segment, then dragged down and left, almost to E_1.
PASSING: Point = ((TURN[0] + NEW_END[0]) / 2, (TURN[1] + NEW_END[1]) / 2)
NEAR_E_1: Point = (11.12, 11.12)


CUT: list[Step] = [
    Move(START, 0),
    Wait(500),
    Move(A_1, 1000),
    Wait(300),
    *click(),
    Wait(350),
    Move(TURN, 900),
    Wait(250),
    *click(),
    Wait(350),
    Move((END[0], END[1] + INSIDE), 900),  # just inside the net: the cut A_3-B_3 is clicked
    Wait(250),
    *click(),
    Wait(400),
]

ADJUST: list[Step] = [
    Wait(400),
    Move(END, 700),
    Wait(250),
    Press(),
    Wait(150),
    Move(NEW_END, 1500, via=((12.0, 10.0),)),  # the end walks along the perimeter, round the corner B_3
    Wait(150),
    Release(),
    Wait(500),
    Move(ADDED, 900),
    Wait(300),
    *click(),
    Wait(400),
    Press(),
    Wait(150),
    Move(ASIDE, 800),
    Wait(150),
    Release(),
    Wait(500),
    Move(PASSING, 900),
    Wait(300),
    *click(),
    Wait(400),
    Press(),
    Wait(150),
    Move(NEAR_E_1, 900),
    Wait(150),
    Release(),
    Wait(600),
    Keys(Qt.KeyboardModifier.ControlModifier),
    Wait(700),
    *click(),
    Wait(300),
    Keys(Qt.KeyboardModifier.NoModifier),
    Wait(400),
]

# The edges glued onto, and where their buttons appear (the middle of the edge, which stays where it is).
GOOD_EDGE: Point = (13.0, 12.5)
BAD_EDGE: Point = (12 + 5 / 6, 12.0)  # the right arm below, from where the line divides it (12 2/3) to F_2

GLUE_GOOD: list[Step] = [
    Wait(400),
    Move((GOOD_EDGE[0] - INSIDE, GOOD_EDGE[1]), 1000),
    Wait(700),  # its counterpart blinks
    *click(),
    Wait(1000),
    Move(GOOD_EDGE, 500),
    Wait(400),
    *click(),
    Wait(500),
    Move((13.5, 11.0), 700),
]

# How long the overlap is shown before the button cancels it (ms, from click to click).
CANCEL_AFTER_MS = 5000

GLUE_BAD: list[Step] = [
    Wait(400),
    Move((BAD_EDGE[0], BAD_EDGE[1] + INSIDE), 1000),
    Wait(700),
    *click(),
    Wait(CANCEL_AFTER_MS - 500 - 400),  # the overlap is shown
    Move(BAD_EDGE, 500),
    Wait(400),
    *click(),
    Wait(500),
    Move((13.5, 11.0), 700),
]
