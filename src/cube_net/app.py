# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Application bootstrap."""

import sys

from PyQt6.QtWidgets import QApplication

from cube_net.ui.main_window import APP_TITLE, MainWindow


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("cube_net")
    window = MainWindow()
    window.show()
    window.reopen_last_project()
    return app.exec()
