# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""A pytest plugin for the release script: it tells how far the tests are, so that the script can show one line of
progress instead of pytest's output (which it shows only if the tests fail).

`release.py` loads it (`-p scripts.pytest_progress`) and gives it a file descriptor in $CUBE_NET_TEST_PROGRESS_FD:
after the collection and after every test, it writes "<done> <total>" there, a line each. Without that variable it
does nothing.
"""

import os
from typing import IO

import pytest

# The variable with the file descriptor to write the progress to.
VARIABLE = "CUBE_NET_TEST_PROGRESS_FD"


class _Progress:
    def __init__(self) -> None:
        self.out: IO[str] | None = None
        self.total = 0
        self.done = 0

    def tell(self) -> None:
        if self.out is not None:
            self.out.write(f"{self.done} {self.total}\n")
            self.out.flush()


_PROGRESS = _Progress()


def pytest_collection_finish(session: pytest.Session) -> None:
    descriptor = os.environ.get(VARIABLE)
    if descriptor is None:
        return
    _PROGRESS.out = os.fdopen(int(descriptor), "w", encoding="utf-8")
    _PROGRESS.total = len(session.items)
    _PROGRESS.tell()


def pytest_runtest_logfinish(nodeid: str, location: tuple[str, int | None, str]) -> None:
    _PROGRESS.done += 1
    _PROGRESS.tell()


def pytest_unconfigure(config: pytest.Config) -> None:
    if _PROGRESS.out is not None:
        _PROGRESS.out.close()
        _PROGRESS.out = None
