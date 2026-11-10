"""The scripts do what the help says, on the real editor, and nothing on the way is rejected."""

from collections.abc import Sequence

import pytest
from PyQt6.QtCore import QSize
from pytestqt.qtbot import QtBot

from cube_net.core.editor import EditorState
from cube_net.core.geometry import Vec
from cube_net.ui.help.demo import scenes
from cube_net.ui.help.demo.demo_sheet import DemoSheet
from cube_net.ui.help.demo.player import DEFAULT_SIZE
from cube_net.ui.help.demo.steps import Step
from cube_net.ui.sheet.cursors import CursorKind


def played(qtbot: QtBot, *parts: Sequence[Step], size: QSize = DEFAULT_SIZE) -> DemoSheet:
    sheet = DemoSheet(size)
    qtbot.addWidget(sheet)
    sheet.show()
    qtbot.waitExposed(sheet)
    rejected: list[Vec] = []
    sheet.workspace.cut_tool.rejected.connect(rejected.append)
    for part in parts:
        for _ in sheet.play(part, instant=True):
            pass
    assert rejected == []
    return sheet


def points(sheet: DemoSheet) -> list[tuple[float, float]]:
    """The cut line's points, to a thousandth (where the end lands on the perimeter is rounded to that)."""
    line = sheet.workspace.editor.cut_line
    assert line is not None
    return [(round(float(p.position.x), 3), round(float(p.position.y), 3)) for p in line.points]


def rounded(*ps: tuple[float, float]) -> list[tuple[float, float]]:
    return [(round(x, 3), round(y, 3)) for x, y in ps]


def test_the_cut_has_two_segments_from_a_1_to_the_middle_of_a_3_b_3(qtbot: QtBot) -> None:
    sheet = played(qtbot, scenes.CUT)
    assert sheet.workspace.editor.state is EditorState.CUT_EDITING
    assert points(sheet) == rounded(scenes.A_1, scenes.TURN, scenes.END)


def test_adjusting_ends_with_a_zigzag_of_three_segments(qtbot: QtBot) -> None:
    sheet = played(qtbot, scenes.CUT, scenes.ADJUST)
    assert points(sheet) == rounded(scenes.A_1, scenes.ASIDE, scenes.TURN, scenes.NEW_END)
    # 3 points; the end moved; a point added and moved; one more added, moved and deleted.
    assert sheet.workspace.editor.history.done_count == 3 + 1 + 2 + 3


def test_the_end_is_twice_as_close_to_f_1_as_to_g_1() -> None:
    x, y = scenes.NEW_END
    assert x == 12 and (y - 11) * 2 == pytest.approx(12 - y)


@pytest.mark.parametrize("size", [QSize(640, 440), QSize(428, 400)], ids=["wide", "half"])
def test_the_good_glue_is_approved(qtbot: QtBot, size: QSize) -> None:
    sheet = played(qtbot, scenes.CUT, scenes.ADJUST, scenes.GLUE_GOOD, size=size)
    editor = sheet.workspace.editor
    assert editor.state is EditorState.DEFAULT
    assert len(editor.net.vertices) > 14  # the new net, with the cut in it


def test_the_bad_glue_overlaps_and_is_cancelled(qtbot: QtBot) -> None:
    sheet = played(qtbot, scenes.CUT, scenes.ADJUST, scenes.GLUE_BAD[:4])
    rearranged = sheet.workspace.editor.rearranged
    assert rearranged is not None and not rearranged.valid
    for _ in sheet.play(scenes.GLUE_BAD[4:], instant=True):
        pass
    assert sheet.workspace.editor.state is EditorState.CUT_EDITING
    assert points(sheet) == rounded(scenes.A_1, scenes.ASIDE, scenes.TURN, scenes.NEW_END)


def test_the_overlap_is_shown_for_5_seconds() -> None:
    from cube_net.ui.help.demo.steps import CLICK_MS, Move, Wait

    first, second = (i for i, step in enumerate(scenes.GLUE_BAD) if type(step).__name__ == "Press")
    between = scenes.GLUE_BAD[first + 1 : second]
    total = sum(s.ms for s in between if isinstance(s, (Wait, Move)))
    assert total - CLICK_MS == scenes.CANCEL_AFTER_MS == 5000


def test_ctrl_shows_the_red_x_over_the_point_to_delete(qtbot: QtBot) -> None:
    ctrl = scenes.ADJUST.index(next(s for s in scenes.ADJUST if type(s).__name__ == "Keys"))
    sheet = played(qtbot, scenes.CUT, scenes.ADJUST[: ctrl + 1])
    assert sheet.pointer.kind() is CursorKind.DELETE
