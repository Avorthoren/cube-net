from pathlib import Path

import pytest
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


def test_max_zoom_default_and_persisted(tmp_path: Path) -> None:
    from cube_net.ui.sheet.zoom import DEFAULT_MAX_ZOOM

    s = settings_at(tmp_path / "s.ini")
    assert s.max_zoom == DEFAULT_MAX_ZOOM
    s.max_zoom = 2500
    assert settings_at(tmp_path / "s.ini").max_zoom == 2500


@pytest.mark.parametrize("value", [499, 10001, -1])
def test_max_zoom_out_of_range_is_refused(tmp_path: Path, value: int) -> None:
    s = settings_at(tmp_path / "s.ini")
    with pytest.raises(ValueError):
        s.max_zoom = value


@pytest.mark.parametrize("stored", ["99999", "abc", "100"])
def test_max_zoom_nonsense_in_the_file_gives_the_default(tmp_path: Path, stored: str) -> None:
    from cube_net.ui.sheet.zoom import DEFAULT_MAX_ZOOM

    QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat).setValue("view/max_zoom", stored)
    assert settings_at(tmp_path / "s.ini").max_zoom == DEFAULT_MAX_ZOOM


def test_style_default_and_persisted(tmp_path: Path) -> None:
    from dataclasses import replace

    from cube_net.ui.style import DEFAULT_STYLE

    s = settings_at(tmp_path / "s.ini")
    assert s.style == DEFAULT_STYLE
    changed = replace(DEFAULT_STYLE, edge_width=7.5, hatch_columns=3, face_colors=("#000000",) * 6)
    s.style = changed
    assert settings_at(tmp_path / "s.ini").style == changed


@pytest.mark.parametrize(
    ("key", "stored"),
    [("edge_width", "99"), ("edge_width", "abc"), ("hatch_rows", "0"), ("grid_color", "#xyz"), ("face_colors", "#1")],
)
def test_a_bad_style_value_gives_just_its_default(tmp_path: Path, key: str, stored: str) -> None:
    from dataclasses import replace

    from cube_net.ui.style import DEFAULT_STYLE

    s = settings_at(tmp_path / "s.ini")
    s.style = replace(DEFAULT_STYLE, vertex_radius=20.0)
    QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat).setValue(f"style/{key}", stored)
    style = settings_at(tmp_path / "s.ini").style
    assert getattr(style, key) == getattr(DEFAULT_STYLE, key)
    assert style.vertex_radius == 20.0


def test_blink_on_success_default_and_persisted(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    assert s.blink_on_success is True
    s.blink_on_success = False
    assert settings_at(tmp_path / "s.ini").blink_on_success is False


def test_settings_tab_default_and_persisted(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    assert s.settings_tab == ""
    s.settings_tab = "Style"
    assert settings_at(tmp_path / "s.ini").settings_tab == "Style"


def test_settings_open_default_and_persisted(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    assert s.settings_open is True  # open at the very first start
    s.settings_open = False
    assert settings_at(tmp_path / "s.ini").settings_open is False


def test_language_default_and_persisted(tmp_path: Path) -> None:
    from cube_net.ui.i18n import Language

    s = settings_at(tmp_path / "s.ini")
    assert s.language is Language.ENGLISH
    s.language = Language.RUSSIAN
    assert settings_at(tmp_path / "s.ini").language is Language.RUSSIAN
    QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat).setValue("view/language", "xx")
    assert settings_at(tmp_path / "s.ini").language is Language.ENGLISH


def test_a_style_saved_with_too_small_vertices_gets_them_large_enough(tmp_path: Path) -> None:
    from dataclasses import replace

    from cube_net.ui.style import DEFAULT_STYLE

    s = settings_at(tmp_path / "s.ini")
    s.style = replace(DEFAULT_STYLE, edge_width=5.0, vertex_radius=3.0)  # before vertices had their least size
    assert settings_at(tmp_path / "s.ini").style.vertex_radius == 3.5
