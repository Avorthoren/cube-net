# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The crash report: a file next to the session logs, `crash-report-<time>-<pid>.log`, for the author to find out what
happened.

It's written in parts, the traceback first: it needs almost nothing of the application. Every other part
(`CrashSection`) is worked out on its own, and one that fails says so in its place: the rest is still written. The file
is written line by line as it goes, so whatever was written before a failure stays.
"""

import platform
import sys
import threading
import time
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TextIO

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
from PyQt6.QtWidgets import QApplication

from cube_net import __version__
from cube_net.ui.i18n import TRANSLATIONS
from cube_net.ui.session.session_log import unique_log_path

# What the reports' names start with (the session logs': "session").
PREFIX = "crash-report"


@dataclass(frozen=True)
class CrashSection:
    title: str

    # Works the section's text out (it may fail: the report says so instead).
    text: Callable[[], str]


def write_crash_report(
    directory: Path,
    error: tuple[type[BaseException], BaseException, TracebackType | None],
    sections: Sequence[CrashSection],
    started: float,
    now: datetime | None = None,
) -> Path:
    """Write a new report into `directory`: `error`'s traceback, then the environment (`started`: when the application
    started, `time.monotonic`), then `sections`. Returns its path."""
    path = unique_log_path(directory, PREFIX, now)
    with path.open("w", encoding="utf-8", buffering=1) as file:
        file.write(f"# Cube Net {__version__} crash report\n")
        _write(file, "Traceback", "".join(traceback.format_exception(*error)))
        everything = [CrashSection("Environment", lambda: environment_text(started, now)), *sections]
        for section in everything:
            try:
                text = section.text()
            except Exception as e:  # the report goes on without it
                text = "This part couldn't be written:\n" + "".join(traceback.format_exception(e))
            _write(file, section.title, text)
    return path


def environment_text(started: float, now: datetime | None = None) -> str:
    """Where and when it happened: versions, system, screen, language, time, how long the application had run."""
    lines = [
        f"version: {__version__} ({'packaged' if getattr(sys, 'frozen', False) else 'from source'})",
        f"python: {platform.python_version()}, Qt: {QT_VERSION_STR}, PyQt: {PYQT_VERSION_STR}",
        f"system: {platform.platform()}",
    ]
    app = QApplication.instance()
    screen = app.primaryScreen() if isinstance(app, QApplication) else None
    if screen is not None:
        size = screen.geometry()
        lines.append(f"screen: {size.width()}x{size.height()} dpr {screen.devicePixelRatio():g}")
    lines.append(f"language: {TRANSLATIONS.language.value}")
    lines.append(f"time: {(now or datetime.now()).isoformat(sep=' ', timespec='seconds')}")
    lines.append(f"running for: {time.monotonic() - started:.1f} s")
    lines.append(f"thread: {threading.current_thread().name}")
    return "\n".join(lines)


def _write(file: TextIO, title: str, text: str) -> None:
    file.write(f"\n## {title}\n\n{text.rstrip()}\n")
