"""`AppSettings`: settings of the application as a whole (not of a project), stored with `QSettings`."""

from PyQt6.QtCore import QSettings

# Debug labels (A_1, x_2, ...) next to all vertices. ON while the app is being developed; switch to False later.
DEFAULT_SHOW_VERTEX_LABELS = True

# Session recording: a compact log of user input (one file per launch), so that problems can be reproduced exactly.
# ON while the app is being developed; switch to False later.
DEFAULT_RECORD_SESSION = True

_SHOW_VERTEX_LABELS = "debug/show_vertex_labels"
_RECORD_SESSION = "debug/record_session"


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

    def _bool(self, key: str, default: bool) -> bool:
        return bool(self._settings.value(key, default, type=bool))
