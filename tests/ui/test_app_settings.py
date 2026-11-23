# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

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


def test_last_view(tmp_path: Path) -> None:
    from cube_net.ui.sheet.view_place import LastView, ViewPlace

    s = settings_at(tmp_path / "s.ini")
    assert s.last_view is None
    view = LastView(tmp_path / "cube.cubenet", ViewPlace(11.25, -3.0625, 123.456))
    s.last_view = view
    assert settings_at(tmp_path / "s.ini").last_view == view
    s.last_view = None
    assert settings_at(tmp_path / "s.ini").last_view is None


@pytest.mark.parametrize("stored", ["", "1 2", "a b c", "1 2 0", "1 2 -3", "nan 2 3", "1 inf 3"])
def test_a_last_view_stored_wrong_is_none(tmp_path: Path, stored: str) -> None:
    s = settings_at(tmp_path / "s.ini")
    s._settings.setValue("project/last_view_file", str(tmp_path / "cube.cubenet"))
    s._settings.setValue("project/last_view", stored)
    assert s.last_view is None


def test_window_geometry(tmp_path: Path) -> None:
    from PyQt6.QtCore import QByteArray

    s = settings_at(tmp_path / "s.ini")
    assert s.window_geometry is None
    s.window_geometry = QByteArray(b"\x01\xd9\xd0\xcb geometry")
    assert settings_at(tmp_path / "s.ini").window_geometry == QByteArray(b"\x01\xd9\xd0\xcb geometry")


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


def store_style(path: Path, **values: object) -> None:
    """What an older version wrote for Settings -> Style."""
    stored = QSettings(str(path), QSettings.Format.IniFormat)
    for key, value in values.items():
        stored.setValue(f"style/{key}", value)
    stored.sync()


def test_the_style_of_an_older_version(tmp_path: Path) -> None:
    """Up to now the application kept Settings -> Style; documents saved then open with it. It's never written."""
    from dataclasses import fields, replace

    from cube_net.ui.style import DEFAULT_STYLE

    assert settings_at(tmp_path / "s.ini").legacy_style is None
    changed = replace(DEFAULT_STYLE, edge_width=7.5, hatch_columns=3)
    store_style(tmp_path / "s.ini", **{field.name: getattr(changed, field.name) for field in fields(changed)})
    assert settings_at(tmp_path / "s.ini").legacy_style == changed


def test_a_style_of_an_older_version_without_some_values(tmp_path: Path) -> None:
    from dataclasses import replace

    from cube_net.ui.style import DEFAULT_STYLE

    store_style(tmp_path / "s.ini", hatch_columns=3)
    assert settings_at(tmp_path / "s.ini").legacy_style == replace(DEFAULT_STYLE, hatch_columns=3)


@pytest.mark.parametrize(
    ("key", "stored"),
    [("edge_width", "99"), ("edge_width", "abc"), ("hatch_rows", "0"), ("grid_color", "#xyz")],
)
def test_a_bad_style_value_gives_just_its_default(tmp_path: Path, key: str, stored: str) -> None:
    from cube_net.ui.style import DEFAULT_STYLE

    store_style(tmp_path / "s.ini", vertex_radius=20.0)
    store_style(tmp_path / "s.ini", **{key: stored})
    style = settings_at(tmp_path / "s.ini").legacy_style
    assert style is not None
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


def test_instruments_shown_default_and_persisted(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    assert s.instruments_shown is True  # shown at the very first start
    s.instruments_shown = False
    assert settings_at(tmp_path / "s.ini").instruments_shown is False


def test_language_default_and_persisted(tmp_path: Path) -> None:
    from cube_net.ui.i18n import Language

    s = settings_at(tmp_path / "s.ini")
    assert s.language is Language.ENGLISH
    s.language = Language.RUSSIAN
    assert settings_at(tmp_path / "s.ini").language is Language.RUSSIAN
    QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat).setValue("view/language", "xx")
    assert settings_at(tmp_path / "s.ini").language is Language.ENGLISH


def test_a_style_saved_with_too_small_vertices_gets_them_large_enough(tmp_path: Path) -> None:
    store_style(tmp_path / "s.ini", edge_width=5.0, vertex_radius=3.0)  # before vertices had their least size
    style = settings_at(tmp_path / "s.ini").legacy_style
    assert style is not None and style.vertex_radius == 3.5


def test_menu_entry_not_asked_yet_then_remembered(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    assert s.menu_entry is None
    s.menu_entry = False
    assert settings_at(tmp_path / "s.ini").menu_entry is False
    s.menu_entry = True
    assert settings_at(tmp_path / "s.ini").menu_entry is True


def test_update_settings(tmp_path: Path) -> None:
    import datetime

    s = settings_at(tmp_path / "s.ini")
    assert s.check_updates is True and s.last_update_check is None and s.skipped_update is None
    s.check_updates = False
    s.last_update_check = datetime.date(2026, 11, 12)
    s.skipped_update = "1.2.0"
    again = settings_at(tmp_path / "s.ini")
    assert again.check_updates is False
    assert again.last_update_check == datetime.date(2026, 11, 12)
    assert again.skipped_update == "1.2.0"


def test_show_vertex_coordinates_default_and_persisted(tmp_path: Path) -> None:
    from cube_net.ui.app_settings import DEFAULT_SHOW_VERTEX_COORDINATES

    s = settings_at(tmp_path / "s.ini")
    assert s.show_vertex_coordinates is DEFAULT_SHOW_VERTEX_COORDINATES is True
    s.show_vertex_coordinates = False
    assert settings_at(tmp_path / "s.ini").show_vertex_coordinates is False


def test_help_not_shown_at_a_start_yet_then_remembered(tmp_path: Path) -> None:
    s = settings_at(tmp_path / "s.ini")
    assert s.help_shown is False  # a first start, or the first after an update to a version with it
    s.help_shown = True
    assert settings_at(tmp_path / "s.ini").help_shown is True


def test_the_face_colours_of_an_older_version(tmp_path: Path) -> None:
    """Version 1.2.0 kept the face colours in Settings -> Style; they are read, never written."""
    assert settings_at(tmp_path / "s.ini").legacy_face_colors is None
    stored = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    stored.setValue("style/face_colors", "#111111,#222222,#333333,#444444,#555555,#66660a")
    stored.sync()
    s = settings_at(tmp_path / "s.ini")
    assert s.legacy_face_colors == ("#111111", "#222222", "#333333", "#444444", "#555555", "#66660A")


@pytest.mark.parametrize("stored", ["#111111", "#111111,#222222,#333333,#444444,#555555,red", ""])
def test_unusable_face_colours_of_an_older_version(tmp_path: Path, stored: str) -> None:
    QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat).setValue("style/face_colors", stored)
    assert settings_at(tmp_path / "s.ini").legacy_face_colors is None
