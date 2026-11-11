# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pytestqt.qtbot import QtBot

from cube_net.ui.updates.latest_release import LatestRelease, UpdateCheckError
from cube_net.ui.updates.update_check import UpdateCheck

RELEASE = LatestRelease("1.2.0", "notes", "https://example.com")


def test_the_answer_comes_as_a_signal(qtbot: QtBot) -> None:
    check = UpdateCheck(lambda: RELEASE)
    with qtbot.waitSignal(check.found) as blocker:
        check.start()
    assert blocker.args == [RELEASE]
    qtbot.waitUntil(lambda: not check.running())


def test_no_release_yet(qtbot: QtBot) -> None:
    check = UpdateCheck(lambda: None)
    with qtbot.waitSignal(check.found) as blocker:
        check.start()
    assert blocker.args == [None]


def test_a_failure_says_why(qtbot: QtBot) -> None:
    def failing() -> LatestRelease | None:
        raise UpdateCheckError("no network")

    check = UpdateCheck(failing)
    with qtbot.waitSignal(check.failed) as blocker:
        check.start()
    assert blocker.args == ["no network"]


def test_anything_else_going_wrong_too(qtbot: QtBot) -> None:
    def broken() -> LatestRelease | None:
        raise KeyError("tag_name")

    check = UpdateCheck(broken)
    with qtbot.waitSignal(check.failed) as blocker:
        check.start()
    assert blocker.args[0].startswith("KeyError")
