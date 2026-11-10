# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from datetime import datetime
from pathlib import Path

from cube_net.ui.session.session_log import SessionLog


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_unique_name_with_time_and_pid(tmp_path: Path) -> None:
    moment = datetime(2026, 11, 7, 15, 30, 12, 345678)
    log = SessionLog.create_in(tmp_path / "sessions", now=moment)
    assert log.path == tmp_path / "sessions" / f"session-20261107-153012-345-{os.getpid()}.log"
    assert log.path.exists()
    again = SessionLog.create_in(tmp_path / "sessions", now=moment)  # same moment: still a new file
    assert again.path.name == f"session-20261107-153012-345-{os.getpid()}-2.log"
    log.close()
    again.close()


def test_lines_are_compact_with_relative_time(tmp_path: Path) -> None:
    clock = FakeClock()
    log = SessionLog(tmp_path / "s.log", clock=clock)
    log.header("Cube Net session log")
    clock.now = 101.2345
    log.write("press", "L", "11.250,12.500")
    clock.now = 102.5
    log.write("key", "Ctrl+Z")
    log.close()
    assert (tmp_path / "s.log").read_text().splitlines() == [
        "# Cube Net session log",
        "1.234 press L 11.250,12.500",
        "2.500 key Ctrl+Z",
    ]


def test_written_immediately_and_close_is_safe(tmp_path: Path) -> None:
    log = SessionLog(tmp_path / "s.log")
    log.write("press", "L")
    assert "press L" in (tmp_path / "s.log").read_text()  # line-buffered: survives a crash
    log.close()
    assert log.closed
    log.write("ignored")
    log.close()
    assert "ignored" not in (tmp_path / "s.log").read_text()
