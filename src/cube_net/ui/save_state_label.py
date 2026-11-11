# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`SaveStateLabel`: the status bar's word on the project: "Unsaved changes" (orange) while something isn't saved,
"Saved" once all of it is in the project's file, nothing for a new project nobody has changed yet.

It's always as wide as its longest text, so the status bar doesn't shift when it changes.
"""

from PyQt6.QtWidgets import QLabel, QWidget

from cube_net.ui import palette
from cube_net.ui.i18n import TRANSLATIONS, tr

UNSAVED_TEXT = "Unsaved changes"
SAVED_TEXT = "Saved"


class SaveStateLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dirty = False
        self._has_file = False
        TRANSLATIONS.changed.connect(self._show)
        self._show()

    def set_state(self, dirty: bool, has_file: bool) -> None:
        """Whether there are unsaved changes, and whether the project has a file (a new one has none)."""
        self._dirty, self._has_file = dirty, has_file
        self._show()

    def _show(self) -> None:
        metrics = self.fontMetrics()
        self.setMinimumWidth(max(metrics.horizontalAdvance(tr(t)) for t in (UNSAVED_TEXT, SAVED_TEXT)) + 8)
        if self._dirty:
            self.setText(tr(UNSAVED_TEXT))
            self.setStyleSheet(f"color: {palette.UNSAVED.name()}; font-weight: bold;")
        else:
            self.setText(tr(SAVED_TEXT) if self._has_file else "")
            self.setStyleSheet(f"color: {palette.SAVED.name()};")
