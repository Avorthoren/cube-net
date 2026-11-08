from pathlib import Path

from PyQt6.QtCore import QSettings

from cube_net.ui.app_settings import DEFAULT_RECORD_SESSION, DEFAULT_SHOW_VERTEX_LABELS, AppSettings


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


def test_record_session_default_and_persisted(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    assert s.record_session is DEFAULT_RECORD_SESSION
    s.record_session = False
    assert settings_at(tmp_path / "s.ini").record_session is False


def test_last_project(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    assert s.last_project is None
    s.last_project = tmp_path / "cube.cubenet"
    assert settings_at(tmp_path / "s.ini").last_project == tmp_path / "cube.cubenet"
    s.last_project = None
    assert settings_at(tmp_path / "s.ini").last_project is None


def test_last_project_reaches_the_file_at_once(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    s.last_project = tmp_path / "cube.cubenet"
    assert "cube.cubenet" in (tmp_path / "s.ini").read_text()
