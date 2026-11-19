# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`tr` and `bind`: the texts in the current language, and keeping widgets' texts in it when it changes."""

from collections.abc import Callable
from typing import Any

from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QLibraryInfo, QObject, QTranslator, pyqtSignal

from cube_net.ui.i18n.language import Language
from cube_net.ui.i18n.russian import RUSSIAN, RUSSIAN_PLURALS

_TABLES: dict[Language, dict[str, str]] = {Language.ENGLISH: {}, Language.RUSSIAN: RUSSIAN}


class Translations(QObject):
    # The language changed: texts must be set anew.
    changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._language = Language.ENGLISH
        self._bindings: list[tuple[QObject, Callable[[str], Any], str, dict[str, object]]] = []
        self._qt_translator: QTranslator | None = None

    @property
    def language(self) -> Language:
        return self._language

    def set_language(self, language: Language) -> None:
        """Speak `language` from now on: every bound text changes at once, and so do Qt's own (standard buttons, file
        dialogs)."""
        if language is self._language:
            return
        self._language = language
        self._install_qt_translations()
        self._bindings = [b for b in self._bindings if not sip.isdeleted(b[0])]
        for _owner, setter, text, values in self._bindings:
            setter(self.tr(text, **values))
        self.changed.emit()

    def tr(self, text: str, **values: object) -> str:
        """`text` in the current language, with `values` put into its {placeholders}. A text with a number {n} may have
        its forms for numbers in Russian (`RUSSIAN_PLURALS`): 1 действие, 2 действия, 5 действий."""
        translated = _TABLES[self._language].get(text, text)
        n = values.get("n")
        if self._language is Language.RUSSIAN and text in RUSSIAN_PLURALS and isinstance(n, int):
            translated = RUSSIAN_PLURALS[text][russian_plural(n)]
        return translated.format(**values) if values else translated

    def bind(self, owner: QObject, setter: Callable[[str], Any], text: str, **values: object) -> None:
        """Set `text` with `setter` now, and again whenever the language changes, for as long as `owner` lives."""
        setter(self.tr(text, **values))
        self._bindings.append((owner, setter, text, values))

    def _install_qt_translations(self) -> None:
        app = QCoreApplication.instance()
        if app is None:
            return
        if self._qt_translator is not None:
            app.removeTranslator(self._qt_translator)
            self._qt_translator = None
        if self._language is Language.ENGLISH:
            return
        translator = QTranslator(self)
        if translator.load(
            f"qtbase_{self._language.value}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        ):
            app.installTranslator(translator)
            self._qt_translator = translator


def russian_plural(n: int) -> int:
    """Which form a Russian noun takes after the number `n`: 0 for 1, 21, 31...; 1 for 2-4, 22-24...; 2 for the rest
    (5-20, 25-30...)."""
    if n % 10 == 1 and n % 100 != 11:
        return 0
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return 1
    return 2


def in_every_language(text: str) -> list[str]:
    """`text` in each language (to make room for the longest one)."""
    return [_TABLES[language].get(text, text) for language in Language]


# The one there is.
TRANSLATIONS = Translations()


def tr(text: str, **values: object) -> str:
    return TRANSLATIONS.tr(text, **values)


def bind(owner: QObject, setter: Callable[[str], Any], text: str, **values: object) -> None:
    TRANSLATIONS.bind(owner, setter, text, **values)
