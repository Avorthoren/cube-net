"""`AppSettings`: settings of the application as a whole (not of a project), stored with `QSettings`."""

from dataclasses import fields, replace
from pathlib import Path

from PyQt6.QtCore import QSettings

from cube_net.ui.i18n.language import Language
from cube_net.ui.sheet.zoom import DEFAULT_MAX_ZOOM, MAX_ZOOM_RANGE
from cube_net.ui.style import DEFAULT_STYLE, Style, StyleError

# Labels (A_1, x_2, ...) next to all vertices: they stay in the app (they tell apart vertices on the same face).
# ON while the app is being developed; False for releases.
DEFAULT_SHOW_VERTEX_LABELS = True

# Session recording: a compact log of user input (one file per launch), so that problems can be reproduced exactly.
# ON while the app is being developed; False for releases.
DEFAULT_RECORD_SESSION = True

# The Bounds button blinks while the area is below the target (otherwise it's just green).
DEFAULT_BLINK_ON_SUCCESS = True

_SHOW_VERTEX_LABELS = "debug/show_vertex_labels"
_RECORD_SESSION = "debug/record_session"
_BLINK_ON_SUCCESS = "view/blink_on_success"
_LAST_PROJECT = "project/last"
_MAX_ZOOM = "view/max_zoom"
_SETTINGS_TAB = "view/settings_tab"
_SETTINGS_OPEN = "view/settings_open"
_LANGUAGE = "view/language"
_STYLE = "style/"


class AppSettings:
    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = QSettings() if settings is None else settings

    @property
    def show_vertex_labels(self) -> bool:
        return self._bool(_SHOW_VERTEX_LABELS, DEFAULT_SHOW_VERTEX_LABELS)

    @show_vertex_labels.setter
    def show_vertex_labels(self, value: bool) -> None:
        self._settings.setValue(_SHOW_VERTEX_LABELS, value)

    @property
    def record_session(self) -> bool:
        """Whether recording is on (at launch, and whenever the user switches it)."""
        return self._bool(_RECORD_SESSION, DEFAULT_RECORD_SESSION)

    @record_session.setter
    def record_session(self, value: bool) -> None:
        self._settings.setValue(_RECORD_SESSION, value)

    @property
    def blink_on_success(self) -> bool:
        return self._bool(_BLINK_ON_SUCCESS, DEFAULT_BLINK_ON_SUCCESS)

    @blink_on_success.setter
    def blink_on_success(self, value: bool) -> None:
        self._settings.setValue(_BLINK_ON_SUCCESS, value)

    @property
    def language(self) -> Language:
        """The application's language (English if it's not one it knows)."""
        value = str(self._settings.value(_LANGUAGE, Language.ENGLISH.value, type=str))
        return next((language for language in Language if language.value == value), Language.ENGLISH)

    @language.setter
    def language(self, language: Language) -> None:
        self._settings.setValue(_LANGUAGE, language.value)

    @property
    def settings_open(self) -> bool:
        """Whether the settings panel was open when the user last showed or hid it (so that it's open at start)."""
        return self._bool(_SETTINGS_OPEN, False)

    @settings_open.setter
    def settings_open(self, value: bool) -> None:
        self._settings.setValue(_SETTINGS_OPEN, value)

    @property
    def settings_tab(self) -> str:
        """The name of the settings panel's tab the user looked at last ("": none yet)."""
        return str(self._settings.value(_SETTINGS_TAB, "", type=str))

    @settings_tab.setter
    def settings_tab(self, name: str) -> None:
        self._settings.setValue(_SETTINGS_TAB, name)

    @property
    def last_project(self) -> Path | None:
        """The file of the project the user worked on last, to reopen it at start."""
        value = self._settings.value(_LAST_PROJECT, "", type=str)
        return Path(value) if value else None

    @last_project.setter
    def last_project(self, path: Path | None) -> None:
        if path is None:
            self._settings.remove(_LAST_PROJECT)
        else:
            self._settings.setValue(_LAST_PROJECT, str(path))
        self._settings.sync()  # it matters most when the app doesn't get to end normally

    @property
    def max_zoom(self) -> int:
        """How far in the sheet can be zoomed: pixels per unit. A stored value that's out of range or not a number gives
        the default."""
        try:
            value = int(self._settings.value(_MAX_ZOOM, DEFAULT_MAX_ZOOM))
        except TypeError, ValueError:
            return DEFAULT_MAX_ZOOM
        low, high = MAX_ZOOM_RANGE
        return value if low <= value <= high else DEFAULT_MAX_ZOOM

    @max_zoom.setter
    def max_zoom(self, value: int) -> None:
        low, high = MAX_ZOOM_RANGE
        if not low <= value <= high:
            raise ValueError(f"the maximum zoom must be from {low} to {high} pixels per unit, got {value}")
        self._settings.setValue(_MAX_ZOOM, value)

    @property
    def style(self) -> Style:
        """Settings -> Style. A stored value that's missing, out of range or not what it should be gives that value's
        default (the others stay)."""
        values = {
            field.name: _read_style_value(
                field.name, self._settings.value(_STYLE + field.name), getattr(DEFAULT_STYLE, field.name)
            )
            for field in fields(Style)
        }
        try:
            return Style(**values)  # type: ignore[arg-type]
        except StyleError:
            return DEFAULT_STYLE

    @style.setter
    def style(self, style: Style) -> None:
        for field in fields(Style):
            value = getattr(style, field.name)
            self._settings.setValue(_STYLE + field.name, ",".join(value) if isinstance(value, tuple) else value)

    def _bool(self, key: str, default: bool) -> bool:
        return bool(self._settings.value(key, default, type=bool))


def _read_style_value(name: str, stored: object, fallback: object) -> object:
    """One value of a stored style, or `fallback` if it isn't a valid one."""
    if stored is None:
        return fallback
    try:
        if isinstance(fallback, tuple):
            value: object = tuple(str(stored).upper().split(","))
        elif isinstance(fallback, str):
            value = str(stored).upper()
        else:
            value = type(fallback)(stored)  # type: ignore[call-arg]
        replace(DEFAULT_STYLE, **{name: value})  # checks it
    except TypeError, ValueError:
        return fallback
    return value
