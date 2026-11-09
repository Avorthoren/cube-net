"""`AppSettings`: settings of the application as a whole (not of a project), stored with `QSettings`."""

from pathlib import Path

from PyQt6.QtCore import QSettings

# Labels (A_1, x_2, ...) next to all vertices: they stay in the app (they tell apart vertices on the same face).
# ON while the app is being developed; False for releases.
DEFAULT_SHOW_VERTEX_LABELS = True

# Session recording: a compact log of user input (one file per launch), so that problems can be reproduced exactly.
# ON while the app is being developed; False for releases.
DEFAULT_RECORD_SESSION = True

_SHOW_VERTEX_LABELS = "debug/show_vertex_labels"
_RECORD_SESSION = "debug/record_session"
_LAST_PROJECT = "project/last"


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

    def _bool(self, key: str, default: bool) -> bool:
        return bool(self._settings.value(key, default, type=bool))
