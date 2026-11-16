# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`PathLabel`: the footer's path of the file being edited (the project's or the template's); nothing for one that has
no file yet. Too long for the room it has, it's shortened in the middle ("/home/…/projects/second.cubenet"), so that
where it starts and the file's name stay in sight; its tooltip has all of it."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget


class PathLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = ""
        # It takes the room there is and never asks for more: a long path can't widen the window.
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def set_path(self, path: Path | None) -> None:
        self._path = "" if path is None else str(path)
        self.setToolTip(self._path)
        self._fit()

    def path(self) -> str:
        """All of it (what's shown may be shortened)."""
        return self._path

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        room = self.contentsRect().width()
        self.setText(self.fontMetrics().elidedText(self._path, Qt.TextElideMode.ElideMiddle, max(room, 0)))
