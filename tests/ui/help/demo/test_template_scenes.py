# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Template tab's scripts make the built-in Cube with a hole, each from where the one before it ends, and nothing
on the way is rejected."""

from collections.abc import Sequence

from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Vec
from cube_net.core.project import TemplateDocument
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.template import Template, ValidationStatus
from cube_net.ui.dialogs.message_window import MessageWindow
from cube_net.ui.help.demo import template_scenes
from cube_net.ui.help.demo.demo_sheet import DemoSheet
from cube_net.ui.help.demo.steps import Step, Wait
from cube_net.ui.template.template_tool import TemplateTool


def make(qtbot: QtBot, start: TemplateDocument, panel: bool = False) -> DemoSheet:
    shown = template_scenes.PANEL_SHOWN if panel else template_scenes.SHOWN
    sheet = DemoSheet(template_scenes.SIZE, shown, template=start, panel=panel)
    qtbot.addWidget(sheet)
    sheet.show()
    qtbot.waitExposed(sheet)
    return sheet


def play(sheet: DemoSheet, steps: Sequence[Step]) -> None:
    assert isinstance(sheet.tool, TemplateTool)
    rejected: list[Vec] = []
    sheet.tool.rejected.connect(lambda p, _problem: rejected.append(p))
    for _ in sheet.play(steps, instant=True):
        pass
    assert rejected == []


def template(sheet: DemoSheet) -> Template:
    assert isinstance(sheet.tool, TemplateTool)
    return sheet.tool.editor.template


def positions(t: Template) -> list[Vec]:
    return [v.position for v in t.vertices]


def built_in() -> Template:
    return cube_with_a_hole().state.template


def corners(t: Template) -> list[list[Vec]]:
    return sorted(sorted(t.position(i) for i in face.corners) for face in t.faces)


def test_the_loop_drawn_and_closed_where_the_next_animation_starts(qtbot: QtBot) -> None:
    sheet = make(qtbot, template_scenes.empty_start())
    play(sheet, template_scenes.DRAW_LOOP)
    drawn, start = template(sheet), template_scenes.loop_start().state.template
    assert drawn.closed and positions(drawn) == positions(built_in()) == positions(start)
    assert corners(drawn) == corners(start)


def test_the_hole_and_the_folds_drawn_as_the_built_in_has_them(qtbot: QtBot) -> None:
    sheet = make(qtbot, template_scenes.loop_start(), panel=True)
    play(sheet, template_scenes.FOLDS_AND_HOLE)
    drawn, start = template(sheet), template_scenes.folds_start().state.template
    assert len(drawn.holes) == 1 and not drawn.drawing_hole
    assert [v.position for v in drawn.holes[0].vertices] == [v.position for v in built_in().holes[0].vertices]
    assert len(drawn.folds) == len(built_in().folds)
    assert corners(drawn) == corners(start) == corners(built_in())


def test_the_green_face_coloured_and_s_named(qtbot: QtBot) -> None:
    sheet = make(qtbot, template_scenes.folds_start())
    play(sheet, template_scenes.COLORS_AND_LABELS)
    drawn = template(sheet)
    assert [face.color for face in drawn.faces].count(template_scenes.GREEN) == 2
    assert sorted(str(v.label) for v in drawn.all_vertices if v.label is not None) == ["S1", "S2", "S3"]
    expected = {str(v.label): v.position for v in built_in().all_vertices if str(v.label).startswith("S")}
    assert {str(v.label): v.position for v in drawn.all_vertices if v.label is not None} == expected
    assert sheet.small_window is None and sheet.menu is None


def test_validate_says_what_is_missing_then_that_nothing_is(qtbot: QtBot) -> None:
    sheet = make(qtbot, template_scenes.validate_start(), panel=True)
    steps = template_scenes.VALIDATING
    first_message = steps.index(Wait(3600))
    play(sheet, steps[:first_message])
    window = sheet.small_window
    assert isinstance(window, MessageWindow) and "labels" in window.text()
    assert sheet.validate_button is not None and sheet.validate_button.status is ValidationStatus.INVALID
    play(sheet, steps[first_message:-2])
    window = sheet.small_window
    assert isinstance(window, MessageWindow) and "No problems found" in window.text()
    assert sheet.validate_button.status is ValidationStatus.VALID
    play(sheet, steps[-2:])
    assert sheet.small_window is None
    assert all(v.label is not None for v in template(sheet).all_vertices)
