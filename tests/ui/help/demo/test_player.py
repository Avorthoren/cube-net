import pytest
from PyQt6.QtCore import QSize
from pytestqt.qtbot import QtBot

from cube_net.core.editor import EditorState
from cube_net.ui.help.demo import player as player_module
from cube_net.ui.help.demo import scenes
from cube_net.ui.help.demo.player import DemoPlayer, PlayerState
from cube_net.ui.help.demo.round_button import Symbol
from cube_net.ui.help.demo.steps import Move, Wait, click


def make(qtbot: QtBot, steps: list, before: list | None = None) -> DemoPlayer:  # type: ignore[type-arg]
    player = DemoPlayer(steps, before or [], QSize(420, 320))
    qtbot.addWidget(player)
    player.show()
    qtbot.waitExposed(player)
    return player


def test_ready_with_the_mouse_where_the_script_starts(qtbot: QtBot) -> None:
    player = make(qtbot, scenes.CUT)
    assert player.state() is PlayerState.READY
    assert player.button.isVisible() and player.button.symbol() is Symbol.PLAY
    assert player.sheet.mouse() == scenes.START


def test_starts_where_others_end(qtbot: QtBot) -> None:
    player = make(qtbot, scenes.ADJUST, [scenes.CUT])
    assert player.sheet.workspace.editor.state is EditorState.CUT_EDITING
    assert player.sheet.mouse() is not None


def test_plays_stays_still_then_offers_a_replay(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(player_module, "STILL_MS", 200)
    player = make(qtbot, [Move((11.0, 14.0), 0), Wait(50), *click()])
    player.button.clicked.emit()
    assert player.state() is PlayerState.PLAYING and not player.button.isVisible()
    qtbot.waitUntil(lambda: player.state() is PlayerState.ENDED, timeout=2000)
    assert player.sheet.workspace.editor.state is EditorState.CUTTING
    assert not player.button.isVisible()  # still for a while
    qtbot.waitUntil(player.button.isVisible, timeout=2000)
    assert player.button.symbol() is Symbol.REPLAY
    first = player.sheet
    player.button.clicked.emit()
    assert player.sheet is not first  # from the beginning, on a fresh sheet
    assert player.state() is PlayerState.PLAYING
