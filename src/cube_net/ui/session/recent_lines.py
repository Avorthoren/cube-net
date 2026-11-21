# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`RecentLines`: the latest lines of a session log's kind, kept in memory only, never written anywhere by itself.

The application records its input into one all the time (`start_recent_input`), recording or not: a crash report
shows what led to the crash (`ui/crash`). It takes what a `SessionLog` takes, so a `SessionRecorder` writes into it.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable

# How many lines are kept: the latest ones.
RECENT_LINES = 500


class RecentLines:
    def __init__(self, size: int = RECENT_LINES, clock: Callable[[], float] = time.monotonic) -> None:
        self._lines: deque[str] = deque(maxlen=size)
        self._clock = clock
        self._start = clock()

    def header(self, text: str) -> None:
        self._lines.append(f"# {text}")

    def write(self, kind: str, *fields: object) -> None:
        elapsed = self._clock() - self._start
        self._lines.append(" ".join([f"{elapsed:.3f}", kind, *(str(f) for f in fields)]))

    def close(self) -> None:
        """Nothing to close: it goes on keeping lines (a `SessionLog`'s method, for a recorder)."""

    @property
    def closed(self) -> bool:
        return False

    def lines(self) -> list[str]:
        """The lines kept, oldest first."""
        return list(self._lines)
