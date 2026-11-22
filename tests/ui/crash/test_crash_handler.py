# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from PyQt6.QtCore import QTimer
from pytestqt.qtbot import QtBot

from cube_net.ui.crash.crash_handler import CrashHandler
from cube_net.ui.crash.crash_report import CrashSection


class Outcome:
    """What the handler did instead of showing the window and closing the application."""

    def __init__(self) -> None:
        self.shown: list[Path | None] = []
        self.closed: list[int] = []


@pytest.fixture
def outcome() -> Outcome:
    return Outcome()


@pytest.fixture
def handler(tmp_path: Path, outcome: Outcome) -> Iterator[CrashHandler]:
    crashes = CrashHandler(lambda: tmp_path / "sessions", show=outcome.shown.append, close=outcome.closed.append)
    hooks = sys.excepthook, threading.excepthook
    crashes.install()
    yield crashes
    crashes.uninstall()
    assert (sys.excepthook, threading.excepthook) == hooks  # given back


def raised() -> tuple[type[BaseException], BaseException, object]:
    try:
        raise ValueError("broken")
    except ValueError as e:
        return type(e), e, e.__traceback__


def reports(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "sessions").glob("crash-report-*.log"))


def test_a_report_the_window_and_the_end(
    handler: CrashHandler, outcome: Outcome, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ended: list[bool] = []
    handler.sections = lambda: [CrashSection("State", lambda: "state here")]
    handler.end_recording = lambda: ended.append(True)
    handler.handle(*raised())  # type: ignore[arg-type]
    [path] = reports(tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "ValueError: broken" in text and "state here" in text
    assert ended == [True] and outcome.shown == [path] and outcome.closed == [1]
    assert "ValueError: broken" in capsys.readouterr().err  # printed too, as before


def test_whatever_fails_on_the_way_the_application_still_closes(
    handler: CrashHandler, outcome: Outcome, tmp_path: Path
) -> None:
    def broken() -> list[CrashSection]:
        raise RuntimeError("no sections")

    def no_recording() -> None:
        raise RuntimeError("no recording")

    handler.sections = broken
    handler.end_recording = no_recording
    handler.handle(*raised())  # type: ignore[arg-type]
    assert len(reports(tmp_path)) == 1 and outcome.closed == [1]


def test_a_report_that_cannot_be_saved(tmp_path: Path, outcome: Outcome) -> None:
    (tmp_path / "sessions").write_text("a file, not a folder")
    crashes = CrashHandler(lambda: tmp_path / "sessions", show=outcome.shown.append, close=outcome.closed.append)
    crashes.handle(*raised())  # type: ignore[arg-type]
    assert outcome.shown == [None] and outcome.closed == [1]


def test_only_the_first_exception_is_handled(
    handler: CrashHandler, outcome: Outcome, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def show(path: Path | None) -> None:  # the window waits meanwhile: another error comes
        handler.handle(*raised())  # type: ignore[arg-type]

    handler._show = show  # type: ignore[method-assign]
    handler.handle(*raised())  # type: ignore[arg-type]
    assert len(reports(tmp_path)) == 1 and outcome.closed == [1]
    assert "Another exception while the first one is handled" in capsys.readouterr().err


@pytest.mark.qt_no_exception_capture
def test_an_exception_in_a_qt_callback(handler: CrashHandler, outcome: Outcome, qtbot: QtBot) -> None:
    def callback() -> None:
        raise ValueError("in a slot")

    QTimer.singleShot(0, callback)
    qtbot.waitUntil(lambda: outcome.closed == [1])
    assert len(outcome.shown) == 1


def test_an_exception_in_a_background_thread_is_handled_in_the_main_one(
    handler: CrashHandler, outcome: Outcome, qtbot: QtBot
) -> None:
    def work() -> None:
        raise ValueError("in a thread")

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    assert outcome.closed == []  # not there: in the main thread's event loop
    qtbot.waitUntil(lambda: outcome.closed == [1])


def test_ctrl_c_is_left_as_it_is(handler: CrashHandler, outcome: Outcome, capsys: pytest.CaptureFixture[str]) -> None:
    handler.handle(KeyboardInterrupt, KeyboardInterrupt(), None)
    assert outcome.closed == [] and "KeyboardInterrupt" in capsys.readouterr().err
