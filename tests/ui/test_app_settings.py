from pathlib import Path

from PyQt6.QtCore import QSettings

from cube_net.ui.app_settings import DEFAULT_SHOW_VERTEX_LABELS, AppSettings


def settings_at(path: Path) -> AppSettings:
    return AppSettings(QSettings(str(path), QSettings.Format.IniFormat))


def test_default(tmp_path: Path) -> None:
    assert settings_at(tmp_path / "s.ini").show_vertex_labels is DEFAULT_SHOW_VERTEX_LABELS


def test_persisted(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    s.show_vertex_labels = False
    assert settings_at(tmp_path / "s.ini").show_vertex_labels is False
    s.show_vertex_labels = True
    assert settings_at(tmp_path / "s.ini").show_vertex_labels is True
