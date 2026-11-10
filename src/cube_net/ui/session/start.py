# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Starting and stopping session recording.

A recording starts either when the app is launched with recording on, or later when the user turns it on. Either way
the file says so in its header, and the caller writes the current state right after (see `MainWindow`), so the file
alone is enough to reproduce the session. Turning recording off ends the file with a `stop` line; turning it on
again starts a new file.
"""

import platform
import sys
from pathlib import Path

from PyQt6.QtCore import QT_VERSION_STR, QStandardPaths, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication

from cube_net import __version__
from cube_net.ui.session.session_log import SessionLog
from cube_net.ui.session.session_recorder import SessionRecorder

# Why a recording started / stopped (written into the file).
STARTED_AT_LAUNCH = "at app launch"
STARTED_BY_USER = "turned on by the user"
STOPPED_BY_USER = "turned off by the user"
WINDOW_CLOSED = "the main window was closed"


def session_log_directory() -> Path:
    """Where session logs go, e.g. ~/.local/share/cube_net/Cube Net/sessions on Linux."""
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return Path(base) / "sessions"


def open_session_log_folder(directory: Path | None = None) -> bool:
    """Open the folder with the session logs in the system's file manager. Returns False if that failed."""
    folder = directory or session_log_directory()
    folder.mkdir(parents=True, exist_ok=True)
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


def start_session_recording(app: QApplication, reason: str, directory: Path | None = None) -> SessionRecorder:
    """Create a new session file, write the environment and `reason` into its header, and record all input."""
    log = SessionLog.create_in(directory or session_log_directory())
    log.header(f"Cube Net {__version__} session log")
    log.header(f"python {platform.python_version()}, Qt {QT_VERSION_STR}, {platform.platform()}")
    screen = app.primaryScreen()
    if screen is not None:
        size = screen.geometry()
        log.header(f"screen {size.width()}x{size.height()} dpr {screen.devicePixelRatio():g}")
    log.header(f"recording started: {reason}")
    recorder = SessionRecorder(log, parent=app)
    app.installEventFilter(recorder)
    app.aboutToQuit.connect(lambda: _finish(log, "quit"))
    print(f"Recording session to {log.path}", file=sys.stderr)
    return recorder


def stop_session_recording(app: QApplication, recorder: SessionRecorder, reason: str) -> None:
    """End the recording: a final `stop <reason>` line, then no more input is recorded into this file."""
    app.removeEventFilter(recorder)
    recorder.detach()
    _finish(recorder.log, "stop", reason)
    recorder.setParent(None)  # from now on owned by Python only: freed when nothing refers to it any more


def _finish(log: SessionLog, kind: str, *fields: object) -> None:
    if not log.closed:
        log.write(kind, *fields)
        log.close()
