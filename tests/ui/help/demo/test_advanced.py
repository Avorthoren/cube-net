# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

from pytestqt.qtbot import QtBot

from cube_net.core.editor import EditorState
from cube_net.core.geometry import Vec
from cube_net.ui.help.demo import advanced
from cube_net.ui.help.demo.demo_sheet import DemoSheet
from cube_net.ui.help.demo.steps import Move, Type
from cube_net.ui.help.demo.torus import torus_project
from cube_net.ui.sheet.coordinates_text import coordinate_lines


def sheet(qtbot: QtBot) -> DemoSheet:
    demo = DemoSheet(advanced.SIZE, advanced.SHOWN, project=torus_project(), coordinates=True)
    qtbot.addWidget(demo)
    demo.show()
    qtbot.waitExposed(demo)
    return demo


def play(demo: DemoSheet, steps: list) -> None:
    for _ in demo.play(steps, instant=True):
        pass


def test_the_cut_typed_and_with_a_slope_glued_and_approved(qtbot: QtBot) -> None:
    demo = sheet(qtbot)
    editor = demo.workspace.editor
    rejected: list[Vec] = []
    demo.workspace.cut_tool.rejected.connect(rejected.append)
    end = next(i for i, step in enumerate(advanced.ADVANCED) if step == Type("\n") and i > 40)  # the end typed
    play(demo, advanced.ADVANCED[: end + 1])
    assert editor.state is EditorState.CUT_EDITING and editor.cut_line is not None
    # (42, 64) typed off the net; the segment after it at the slope -4 : 1, ending where it reaches the net.
    assert [p.position for p in editor.cut_line.points] == [Vec(41, 61), Vec(42, 64), Vec(F(171, 4), 61)]
    glued = next(i for i, step in enumerate(advanced.ADVANCED) if step == Move(advanced.J_1, 1200))
    play(demo, advanced.ADVANCED[end + 1 : glued])
    assert rejected == [] and editor.state is EditorState.DEFAULT
    assert all(advanced.SHOWN.contains(v.position) for v in editor.net.vertices)


def test_the_origin_moved_and_the_coordinates_hint(qtbot: QtBot) -> None:
    demo = sheet(qtbot)
    hint = demo.coordinates_hint
    assert hint is not None
    play(demo, advanced.ADVANCED[:-3])  # the mouse rests on J_1
    editor = demo.workspace.editor
    assert editor.origin.shown(Vec(F(124, 3), 62)) == Vec(F(1, 2), 12)  # J_1, exactly where the segment crosses
    assert hint.lines() == coordinate_lines(Vec(F(1, 2), 12))
    play(demo, advanced.ADVANCED[-3:])  # and on A_3
    assert hint.lines() == coordinate_lines(Vec(F(-5, 6), 12))
