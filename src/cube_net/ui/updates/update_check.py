# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`UpdateCheck`: asks for the latest release in the background (the network may be slow, or not there: the window
never waits for it), and tells the answer as a signal, back in the window's thread."""

import threading
from collections.abc import Callable

from PyQt6.QtCore import QObject, pyqtSignal

from cube_net.ui.updates.latest_release import LatestRelease, UpdateCheckError


class UpdateCheck(QObject):
    # The latest release (None: there's no release yet).
    found = pyqtSignal(object)

    # Why it couldn't be found out.
    failed = pyqtSignal(str)

    def __init__(self, fetch: Callable[[], LatestRelease | None], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._fetch = fetch
        self._thread: threading.Thread | None = None

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="update check", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            release = self._fetch()
        except UpdateCheckError as error:
            self.failed.emit(str(error))
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")
        else:
            self.found.emit(release)
