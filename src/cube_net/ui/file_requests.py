# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`FileRequests`: the project files the system asks the application to open while it runs.

macOS doesn't put a double-clicked file on the command line: it sends it to the running application as an event
(also at launch, just after the start), and that's how a file dropped on the app's Dock icon arrives too. On Windows
and Linux the file comes on the command line instead (`app.project_argument`), and this never fires.
"""

from collections.abc import Callable
from pathlib import Path
from typing import cast

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtGui import QFileOpenEvent


class FileRequests(QObject):
    def __init__(self, open_file: Callable[[Path], None], parent: QObject | None = None) -> None:
        """`open_file` is called with each file asked for."""
        super().__init__(parent)
        self._open_file = open_file

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if event is not None and event.type() == QEvent.Type.FileOpen:
            name = cast(QFileOpenEvent, event).file()
            if name:
                self._open_file(Path(name))
                return True
        return False
