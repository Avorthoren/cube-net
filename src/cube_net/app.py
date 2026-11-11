# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Application bootstrap: `cube-net [PROJECT_FILE]` (a project file given opens instead of the last one)."""

import sys
import tempfile
from importlib.resources import files
from pathlib import Path

from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from cube_net.ui.app_settings import AppSettings
from cube_net.ui.desktop_integration import ENTRY_NAME, running_appimage
from cube_net.ui.file_requests import FileRequests
from cube_net.ui.main_window import APP_TITLE, MainWindow

# The application's icon (drawn by scripts/make_icon.py).
ICON = files("cube_net.ui.icons") / "cube_net.png"

# The command-line option of the builds' launch test: start, show the window, and quit after a moment (exit code 0),
# with settings of its own (fresh, and gone afterwards: the user's aren't read or changed) and no project reopened.
SMOKE_TEST = "--smoke-test"
SMOKE_TEST_MS = 1500


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("cube_net")
    app.setDesktopFileName(ENTRY_NAME)  # which desktop entry the windows belong to: the Dock shows its icon
    app.setWindowIcon(QIcon(str(ICON)))  # every window's, and the taskbar's
    arguments = sys.argv if argv is None else argv
    if SMOKE_TEST in arguments[1:]:
        with tempfile.TemporaryDirectory() as folder:
            settings = AppSettings(QSettings(str(Path(folder) / "settings.ini"), QSettings.Format.IniFormat))
            window = MainWindow(settings=settings, session_dir=Path(folder))
            window.show()
            QTimer.singleShot(SMOKE_TEST_MS, app.quit)
            return app.exec()
    window = MainWindow(appimage=running_appimage())
    window.show()
    window.offer_menu_entry()  # an AppImage asks once; later it only keeps the entry up to date
    # A file asked for later (macOS sends double-clicked ones so, even at launch) replaces what's shown then.
    app.installEventFilter(FileRequests(window.open_project_requested, app))
    project = project_argument(app.arguments())
    if project is not None:
        window.open_project_at_start(project)
    else:
        window.reopen_last_project()
    return app.exec()


def project_argument(arguments: list[str]) -> Path | None:
    """The project file to open, given on the command line (Windows and Linux put a double-clicked file there): the
    first argument that isn't an option. Qt has taken its own options out of `QApplication.arguments()` already."""
    return next((Path(a) for a in arguments[1:] if not a.startswith("-")), None)
