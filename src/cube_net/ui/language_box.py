# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`LanguageBox`: the list of the application's languages, each in its own language (Settings -> Preferences, and the
top of Help -> Help). It's one setting: whichever list the language is changed in, every one of them shows it."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QWidget

from cube_net.ui.i18n import TRANSLATIONS, Language


class LanguageBox(QComboBox):
    # The user chose another language here (a `Language`).
    chosen = pyqtSignal(object)

    def __init__(self, language: Language, parent: QWidget | None = None) -> None:
        """`language`: the one shown at first."""
        super().__init__(parent)
        for known in Language:
            self.addItem(known.native_name, known)  # in its own language, whatever the current one is
        self.show_language(language)
        self.currentIndexChanged.connect(lambda i: self.chosen.emit(self.itemData(i)))
        TRANSLATIONS.changed.connect(self._follow)  # a method: Qt disconnects it when the box is gone

    def _follow(self) -> None:
        self.show_language(TRANSLATIONS.language)

    def show_language(self, language: Language) -> None:
        """Show `language` (not taken for the user's choice)."""
        self.blockSignals(True)
        self.setCurrentIndex(list(Language).index(language))
        self.blockSignals(False)
