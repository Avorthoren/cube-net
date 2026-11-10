"""`tr` and `bind`: the texts in the current language, and keeping widgets' texts in it when it changes."""

from collections.abc import Callable
from typing import Any

from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QLibraryInfo, QObject, QTranslator, pyqtSignal

from cube_net.ui.i18n.language import Language
from cube_net.ui.i18n.russian import RUSSIAN

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
        """`text` in the current language, with `values` put into its {placeholders}."""
        translated = _TABLES[self._language].get(text, text)
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


def in_every_language(text: str) -> list[str]:
    """`text` in each language (to make room for the longest one)."""
    return [_TABLES[language].get(text, text) for language in Language]


# The one there is.
TRANSLATIONS = Translations()


def tr(text: str, **values: object) -> str:
    return TRANSLATIONS.tr(text, **values)


def bind(owner: QObject, setter: Callable[[str], Any], text: str, **values: object) -> None:
    TRANSLATIONS.bind(owner, setter, text, **values)
