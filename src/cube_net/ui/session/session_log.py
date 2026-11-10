# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`SessionLog`: the session file. One line per entry: `<seconds since start> <kind> <fields...>`.

Header lines start with `#`. The file is line-buffered, so it's complete even if the application crashes.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TextIO


class SessionLog:
    def __init__(self, path: Path, clock: Callable[[], float] = time.monotonic) -> None:
        self.path = path
        self._clock = clock
        self._start = clock()
        self._file: TextIO | None = path.open("w", encoding="utf-8", buffering=1)

    @classmethod
    def create_in(cls, directory: Path, now: datetime | None = None) -> SessionLog:
        """A new log with a unique name, e.g. `session-20261107-153012-345-4242.log` (time with milliseconds and
        process id; a counter is appended in the unlikely case that such a file already exists)."""
        directory.mkdir(parents=True, exist_ok=True)
        moment = now or datetime.now()
        base = f"session-{moment:%Y%m%d-%H%M%S}-{moment.microsecond // 1000:03d}-{os.getpid()}"
        path = directory / f"{base}.log"
        counter = 2
        while path.exists():
            path = directory / f"{base}-{counter}.log"
            counter += 1
        return cls(path)

    def header(self, text: str) -> None:
        self._write(f"# {text}")

    def write(self, kind: str, *fields: object) -> None:
        elapsed = self._clock() - self._start
        self._write(" ".join([f"{elapsed:.3f}", kind, *(str(f) for f in fields)]))

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    @property
    def closed(self) -> bool:
        return self._file is None

    def _write(self, line: str) -> None:
        if self._file is not None:
            self._file.write(line + "\n")
