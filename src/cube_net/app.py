# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Application bootstrap."""

import sys
import tempfile
from importlib.resources import files
from pathlib import Path

from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from cube_net.ui.app_settings import AppSettings
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
    app.setWindowIcon(QIcon(str(ICON)))  # every window's, and the taskbar's
    arguments = sys.argv if argv is None else argv
    if SMOKE_TEST in arguments[1:]:
        with tempfile.TemporaryDirectory() as folder:
            settings = AppSettings(QSettings(str(Path(folder) / "settings.ini"), QSettings.Format.IniFormat))
            window = MainWindow(settings=settings, session_dir=Path(folder))
            window.show()
            QTimer.singleShot(SMOKE_TEST_MS, app.quit)
            return app.exec()
    window = MainWindow()
    window.show()
    window.reopen_last_project()
    return app.exec()
