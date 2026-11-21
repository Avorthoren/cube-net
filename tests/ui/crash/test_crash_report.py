# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from types import TracebackType

from PyQt6.QtWidgets import QApplication

from cube_net import __version__
from cube_net.ui.crash.crash_report import CrashSection, environment_text, write_crash_report


def error() -> tuple[type[BaseException], BaseException, TracebackType | None]:
    try:
        raise ValueError("something broke")
    except ValueError:
        kind, value, trace = sys.exc_info()
    assert kind is not None and value is not None
    return kind, value, trace


def test_the_traceback_the_environment_and_the_sections(tmp_path: Path, qapp: QApplication) -> None:
    moment = datetime(2026, 11, 21, 12, 0, 0, 5000)
    sections = [CrashSection("State", lambda: "state one\nstate two"), CrashSection("Recent input", lambda: "key A")]
    path = write_crash_report(tmp_path / "sessions", error(), sections, time.monotonic(), now=moment)
    assert path == tmp_path / "sessions" / f"crash-report-20261121-120000-005-{os.getpid()}.log"
    text = path.read_text(encoding="utf-8")
    assert text.startswith(f"# Cube Net {__version__} crash report")
    titles = [line for line in text.splitlines() if line.startswith("## ")]
    assert titles == ["## Traceback", "## Environment", "## State", "## Recent input"]
    assert "ValueError: something broke" in text and "state one\nstate two" in text and "key A" in text


def test_a_section_that_fails_leaves_the_others(tmp_path: Path, qapp: QApplication) -> None:
    def broken() -> str:
        raise RuntimeError("no state")

    sections = [CrashSection("State", broken), CrashSection("Recent input", lambda: "key A")]
    text = write_crash_report(tmp_path, error(), sections, time.monotonic()).read_text(encoding="utf-8")
    assert "This part couldn't be written" in text and "RuntimeError: no state" in text
    assert text.index("## State") < text.index("## Recent input") < text.index("key A")


def test_the_environment(qapp: QApplication) -> None:
    text = environment_text(time.monotonic() - 2.5, datetime(2026, 11, 21, 12, 0, 0))
    assert f"version: {__version__} (from source)" in text
    assert "time: 2026-11-21 12:00:00" in text and "running for: 2.5 s" in text and "thread: MainThread" in text
