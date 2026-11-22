# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the main window's tests share: the settings of a test's window, its session log's lines, where a widget is."""

from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, QSettings
from PyQt6.QtWidgets import QWidget

from cube_net.ui.app_settings import AppSettings


def in_window(widget: QWidget) -> QRect:
    """Where `widget` is in the main window (the settings panel is placed in the window's own coordinates)."""
    window = widget.window()
    assert window is not None
    return QRect(widget.mapTo(window, QPoint(0, 0)), widget.size())


def settings_in(tmp_path: Path, record: bool) -> AppSettings:
    settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    settings.record_session = record
    settings.settings_open = False  # as the user left it; it's open only at the very first start
    return settings


def session_lines(path: Path) -> list[str]:
    """Lines of a session file without the times."""
    return [line if line.startswith("#") else line.split(" ", 1)[1] for line in path.read_text().splitlines()]
