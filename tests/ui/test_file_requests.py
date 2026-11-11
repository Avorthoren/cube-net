# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.file_requests import FileRequests


class FileOpen:
    """What macOS sends (PyQt can't make a real QFileOpenEvent): its type and its file."""

    def __init__(self, name: str) -> None:
        self.name = name

    def type(self) -> QEvent.Type:
        return QEvent.Type.FileOpen

    def file(self) -> str:
        return self.name


def test_a_file_the_system_asks_for_is_opened(qtbot: QtBot) -> None:
    """macOS sends a double-clicked file to the running application like this."""
    opened: list[Path] = []
    requests = FileRequests(opened.append)
    app = QApplication.instance()
    assert requests.eventFilter(app, FileOpen("/home/me/net.cubenet"))  # type: ignore[arg-type]
    assert opened == [Path("/home/me/net.cubenet")]
    assert not requests.eventFilter(app, FileOpen(""))  # type: ignore[arg-type]
    assert opened == [Path("/home/me/net.cubenet")]


def test_other_events_go_on(qtbot: QtBot) -> None:
    opened: list[Path] = []
    requests = FileRequests(opened.append)
    widget = QWidget()
    qtbot.addWidget(widget)
    assert not requests.eventFilter(widget, QEvent(QEvent.Type.Show))
    assert opened == []
