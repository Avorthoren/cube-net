# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import QPoint, QPointF, QSize, Qt
from pytestqt.qtbot import QtBot

from cube_net.core.editor import EditorState
from cube_net.ui.help.demo.demo_sheet import FRAME_MS, DemoSheet
from cube_net.ui.help.demo.steps import Keys, Move, Wait, click
from cube_net.ui.sheet.cursors import CursorKind


def make(qtbot: QtBot) -> DemoSheet:
    sheet = DemoSheet(QSize(560, 400))
    qtbot.addWidget(sheet)
    sheet.show()
    qtbot.waitExposed(sheet)
    return sheet


def test_the_waits_of_a_script(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    waits = list(sheet.play([Move((11.5, 12.5), 0), Move((11.6, 12.5), FRAME_MS * 3), Wait(500)]))
    assert waits == [FRAME_MS] * 4 + [500]
    assert list(sheet.play([Move((11.5, 12.5), 300), Wait(500)], instant=True)) == []


def test_scripted_clicks_reach_the_tools(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    for _ in sheet.play([Move((11.0, 14.0), 0), *click()], instant=True):
        pass
    assert sheet.workspace.editor.state is EditorState.CUTTING
    assert sheet.pointer.kind() is CursorKind.SCISSORS


def test_the_users_mouse_means_nothing(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    viewport = sheet.view.viewport()
    assert viewport is not None
    at = sheet.view.from_sheet(QPointF(11.0, 14.0)).toPoint()
    qtbot.mouseClick(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at)
    assert sheet.workspace.editor.state is EditorState.DEFAULT
    qtbot.mouseMove(viewport, QPoint(5, 5))
    assert sheet.mouse() is None


def test_held_keys_go_with_the_mouse(qtbot: QtBot) -> None:
    sheet = make(qtbot)
    for _ in sheet.play([Move((11.5, 12.5), 0), Keys(Qt.KeyboardModifier.ControlModifier)], instant=True):
        pass
    assert sheet.view.ctrl_held()


def test_labels_of_the_cut_lines_new_points_too(qtbot: QtBot) -> None:
    sheet = DemoSheet(QSize(560, 400), labels=True)
    qtbot.addWidget(sheet)
    item = sheet.view.net_item()
    assert item is not None and item.labels() is not None
    for _ in sheet.play([Move((11.0, 14.0), 0), *click(), Move((11.6, 12.2), 0), *click()], instant=True):
        pass
    assert sheet.workspace.cut_tool.item.labels() != ()  # the new point is named
    sheet.set_labels_shown(False)
    assert item.labels() is None and sheet.workspace.cut_tool.item.labels() == ()


def test_the_bounding_rectangle_if_wanted(qtbot: QtBot) -> None:
    from cube_net.core.geometry import Vec

    assert DemoSheet(QSize(560, 400)).bounding_item is None
    sheet = DemoSheet(QSize(560, 400), bounds=True)
    qtbot.addWidget(sheet)
    assert sheet.bounding_item is not None
    assert set(sheet.bounding_item.corners()) == {Vec(10, 10), Vec(13, 10), Vec(13, 14), Vec(10, 14)}
    assert not sheet.bounding_item.success()  # 12 isn't below a new project's target
