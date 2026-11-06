"""`AppSettings`: settings of the application as a whole (not of a project), stored with `QSettings`."""

from PyQt6.QtCore import QSettings

# Debug labels (A_1, x_2, ...) next to all vertices. ON while the app is being developed; switch to False later.
DEFAULT_SHOW_VERTEX_LABELS = True

_SHOW_VERTEX_LABELS = "debug/show_vertex_labels"


class AppSettings:
    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = QSettings() if settings is None else settings

    @property
    def show_vertex_labels(self) -> bool:
        value = self._settings.value(_SHOW_VERTEX_LABELS, DEFAULT_SHOW_VERTEX_LABELS, type=bool)
        return bool(value)

    @show_vertex_labels.setter
    def show_vertex_labels(self, value: bool) -> None:
        self._settings.setValue(_SHOW_VERTEX_LABELS, value)
