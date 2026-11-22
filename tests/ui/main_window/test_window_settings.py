# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main window: the settings panel, the style, the language."""

from pathlib import Path

import pytest
from PyQt6.QtCore import QPoint, QPointF, QSettings, Qt
from pytestqt.qtbot import QtBot
from window_checks import in_window, session_lines, settings_in

from cube_net.core.body import CUBE
from cube_net.core.project import save_project
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.main_window import (
    MainWindow,
)
from cube_net.ui.style import DEFAULT_STYLE, Style


class TestSettingsPanel:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.resize(1200, 800)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_the_menu_bar(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        menu_bar = window.menuBar()
        assert menu_bar is not None
        assert [a.text() for a in menu_bar.actions()][:3] == ["&File", "&Edit", "&Settings"]

    def test_it_opens_and_closes(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        panel = window.settings_panel
        assert not panel.isVisible()
        window.settings_action.trigger()
        assert panel.isVisible()
        window.settings_action.trigger()
        assert not panel.isVisible()

    def test_the_tabs(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        tabs = window.settings_panel.tabs
        assert [tabs.tabText(i) for i in range(tabs.count())] == ["Preferences", "Style"]

    def test_over_the_right_of_the_sheet_and_the_sheet_stays(self, qtbot: QtBot, tmp_path: Path) -> None:

        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        before = view.from_sheet(QPointF(11, 12))
        window.settings_action.trigger()
        panel = window.settings_panel
        area = in_window(view)
        assert panel.geometry().right() == area.right()
        assert panel.geometry().top() == area.top()
        assert panel.geometry().height() == area.height()
        screen = window.screen()
        assert screen is not None
        assert panel.width() <= screen.geometry().width() / 3
        assert view.from_sheet(QPointF(11, 12)) == before

    def test_it_follows_the_window(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.resize(1000, 700)
        qtbot.waitUntil(lambda: window.settings_panel.geometry().right() == in_window(window.sheet_view).right())
        assert window.settings_panel.geometry().top() == in_window(window.sheet_view).top()
        assert window.settings_panel.height() == window.sheet_view.height()

    def test_over_the_template_sheet_too(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.new_template_action.trigger()
        area = in_window(window.template_mode.view)
        assert window.settings_panel.geometry().topRight() == area.topRight()
        assert window.settings_panel.height() == area.height()

    def test_the_sheet_works_while_it_is_open(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.sheet_view.left_pressed.emit(10.0, 13.0)
        assert window.editor.state.value == "cutting"

    def test_preferences_switches_are_the_same_as_before(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        tab = window.settings_panel.preferences
        assert tab.show_labels.text() == "Show vertex labels"
        assert tab.auto_log.text() == "Auto-start logging"
        assert tab.show_labels.isChecked() == window.settings.show_vertex_labels
        tab.show_labels.setChecked(False)
        assert not window.show_labels_action.isChecked()
        assert window.settings.show_vertex_labels is False
        item = window.sheet_view.net_item()
        assert item is not None and item.labels() is None
        window.show_labels_action.setChecked(True)
        assert tab.show_labels.isChecked()

    def test_auto_log_only_decides_about_the_next_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        tab = window.settings_panel.preferences
        assert tab.auto_log.text() == "Auto-start logging"
        assert window.recorder is None and not tab.auto_log.isChecked()
        tab.auto_log.setChecked(True)
        assert window.recorder is None  # it doesn't start now
        assert window.settings.record_session is True
        window.logging_action.trigger()
        tab.auto_log.setChecked(False)
        assert window.recorder is not None  # nor does it stop
        assert window.settings.record_session is False
        window.stop_recording("test over")

    def test_auto_log_starts_it_at_launch(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_panel.preferences.auto_log.setChecked(True)
        other = MainWindow(settings=window.settings, session_dir=tmp_path)
        qtbot.addWidget(other)
        assert other.recorder is not None
        other.stop_recording("test over")

    def test_max_zoom(self, qtbot: QtBot, tmp_path: Path) -> None:

        window = self.make(qtbot, tmp_path, record=True)
        view = window.sheet_view
        view.zoom_by(1e6, QPointF(100, 100))
        assert view.scale_factor() == pytest.approx(1000)
        window.settings_panel.preferences.max_zoom.setValue(700)
        assert window.settings.max_zoom == 700
        assert view.scale_factor() == pytest.approx(700)
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1] == "settings max_zoom 700"
        assert not window.is_dirty  # not part of the project
        window.stop_recording("test over")

    def test_the_max_zoom_setting_is_used_from_the_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        settings = settings_in(tmp_path, record=False)
        settings.max_zoom = 3000
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        assert window.sheet_view.zoom_limits()[1] == 3000
        assert window.settings_panel.preferences.max_zoom.value() == 3000

    def test_the_start_zoom_is_as_far_out_as_it_goes(self, qtbot: QtBot, tmp_path: Path) -> None:
        """The default net takes 50% of the screen height at the start, which is also the zoom-out limit."""
        window = self.make(qtbot, tmp_path)
        assert window.sheet_view.scale_factor() == pytest.approx(window.sheet_view.zoom_limits()[0])

    def test_the_rearranged_net_decides_how_far_out(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path)
        view = window.sheet_view
        before = view.zoom_limits()[0]
        h = net_style.CUT_HITBOX_PX / 2 / view.scale_factor()
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11.75, 10 + h)
        assert window.editor.state.value == "cut_approving"
        assert view.zoom_limits()[0] < before


class TestStyle:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def style(self, window: MainWindow) -> Style:
        style = window.project_settings.style
        assert style is not None
        return style

    def test_a_change_is_the_projects_and_used_at_once(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path, record=True)
        tab = window.settings_panel.style_tab
        tab.edge_width.setValue(8)
        assert net_style.EDGE_WIDTH_PX == 8
        assert net_style.CUT_HITBOX_PX == 12  # still 1.5 times as wide: a hovered cut is drawn this wide too
        assert self.style(window).edge_width == 8
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1].startswith("project style tiling=")
        assert window.is_dirty  # the style is the project's
        assert window.settings.legacy_style is None  # never written to the application's settings
        window.stop_recording("test over")

    def test_the_style_is_saved_with_the_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.core.project import load_project
        from cube_net.ui.sheet import net_style
        from cube_net.ui.style import DEFAULT_STYLE

        window = self.make(qtbot, tmp_path)
        window.settings_panel.style_tab.hatch_columns.setValue(3)
        path = tmp_path / "style.cubenet"
        assert window.save_project_to(path)
        assert not window.is_dirty
        saved = load_project(path).settings.style
        assert saved is not None and saved.hatch_columns == 3
        window.start_new_project()
        assert self.style(window) == DEFAULT_STYLE and DEFAULT_STYLE.hatch_columns == net_style.HATCH_COLUMNS
        assert window.settings_panel.style_tab.hatch_columns.value() == DEFAULT_STYLE.hatch_columns
        assert window.open_project_from(path)
        assert net_style.HATCH_COLUMNS == 3 and window.settings_panel.style_tab.hatch_columns.value() == 3
        assert not window.is_dirty

    def test_a_template_has_its_own_style(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.core.project import load_document
        from cube_net.ui.sheet import net_style
        from cube_net.ui.style import DEFAULT_STYLE

        window = self.make(qtbot, tmp_path)
        window.settings_panel.style_tab.hatch_columns.setValue(3)  # the project's
        window.new_template_action.trigger()
        assert window.template_mode.style == DEFAULT_STYLE and DEFAULT_STYLE.hatch_columns == net_style.HATCH_COLUMNS
        assert not window.is_dirty
        window.settings_panel.style_tab.hatch_rows.setValue(7)
        assert window.template_mode.style.hatch_rows == 7 and window.is_dirty and window.isWindowModified()
        path = tmp_path / "t.nettemplate"
        assert window.save_template_to(path)
        assert not window.is_dirty
        document = load_document(path)
        assert document.style is not None and document.style.hatch_rows == 7  # type: ignore[union-attr]
        window.start_new_template()
        assert window.template_mode.style == DEFAULT_STYLE
        assert window.open_project_from(path)
        assert net_style.HATCH_ROWS == 7 and not window.is_dirty

    def test_documents_of_an_older_version_get_its_style(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Up to now Settings -> Style was the application's: what it was then is the style of what was saved then."""
        from dataclasses import replace

        from cube_net.core.history import History
        from cube_net.core.project import TemplateDocument, new_project, save_template
        from cube_net.core.template import TemplateEditor, TemplateSnapshot
        from cube_net.ui.sheet import net_style

        stored = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
        stored.setValue("style/hatch_columns", 4)
        stored.sync()
        project, template = tmp_path / "old.cubenet", tmp_path / "old.nettemplate"
        save_project(new_project(), project)  # no style, as one saved before would have
        save_template(TemplateDocument(TemplateSnapshot(TemplateEditor().template), History()), template)
        window = self.make(qtbot, tmp_path)
        assert self.style(window).hatch_columns != 4  # a new project: the built-in Cube's
        assert window.open_project_from(project)
        assert self.style(window) == replace(DEFAULT_STYLE, hatch_columns=4) and net_style.HATCH_COLUMNS == 4
        assert not window.is_dirty  # filled in, not changed
        assert window.open_project_from(template)
        assert window.template_mode.style.hatch_columns == 4 and not window.is_dirty

    def test_face_colours_are_the_projects(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.core.project import load_project
        from cube_net.ui import palette

        window = self.make(qtbot, tmp_path, record=True)
        tab = window.settings_panel.style_tab
        assert window.project_settings.face_colors == CUBE.colors
        tab.face_fields[0].edit.setText("")
        qtbot.keyClicks(tab.face_fields[0].edit, "123abc")
        assert palette.FACE_COLORS[1].name().upper() == "#123ABC"
        assert tab.face_swatches[0].color().name().upper() == "#123ABC"
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1].startswith("project face_colors #123ABC/")
        assert window.is_dirty
        path = tmp_path / "colours.cubenet"
        assert window.save_project_to(path)
        assert load_project(path).settings.face_colors == ("#123ABC", *CUBE.colors[1:])
        window.start_new_project()
        assert window.project_settings.face_colors == CUBE.colors
        assert tab.face_fields[0].color() == CUBE.colors[0]
        assert window.open_project_from(path)
        assert palette.FACE_COLORS[1].name().upper() == "#123ABC"
        assert not window.is_dirty
        window.stop_recording("test over")

    def test_the_face_colours_of_an_older_version(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Version 1.2.0 kept the face colours in the Style: projects saved by it, and new ones, start with them."""
        from cube_net.core.project import new_project
        from cube_net.ui import palette

        older = ("#111111", "#222222", "#333333", "#444444", "#555555", "#666666")
        stored = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
        stored.setValue("style/face_colors", ",".join(older))
        stored.sync()
        path = tmp_path / "old.cubenet"
        save_project(new_project(), path)  # no colours, as one saved by 1.2.0 would have
        window = self.make(qtbot, tmp_path)
        assert window.project_settings.face_colors == older
        assert window.open_project_from(path)
        assert window.project_settings.face_colors == older
        assert palette.FACE_COLORS[6].name().upper() == "#666666"
        assert not window.is_dirty  # filled in, not changed

    def test_a_new_window_has_the_built_in_cubes_style(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet import net_style
        from cube_net.ui.style import DEFAULT_STYLE

        net_style.set_sizes(5.0, 10.0, 10, 5, 10, 1.0)
        window = self.make(qtbot, tmp_path)
        assert self.style(window) == DEFAULT_STYLE and DEFAULT_STYLE.vertex_radius == net_style.VERTEX_RADIUS_PX
        assert window.settings_panel.style_tab.vertex_radius.value() == DEFAULT_STYLE.vertex_radius

    def test_the_hitbox_follows_the_thickness(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path)
        window.settings_panel.style_tab.edge_width.setValue(15)
        h = net_style.CUT_HITBOX_PX * 0.9 / window.sheet_view.scale_factor()
        window.sheet_view.mouse_moved.emit(10 + h, 12.5)
        assert window.cut_hover.hovered() is not None

    def test_the_net_is_painted_anew(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        before = window.sheet_view.viewport().grab().toImage()
        window.settings_panel.style_tab.hatch_columns.setValue(3)
        qtbot.wait(20)
        after = window.sheet_view.viewport().grab().toImage()
        assert before != after

    def test_restore_default_after_yes(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.settings_panel import style_tab as tabs
        from cube_net.ui.style import DEFAULT_STYLE

        window = self.make(qtbot, tmp_path)
        tab = window.settings_panel.style_tab
        tab.hatch_columns.setValue(3)
        tab.edge_width.setValue(9)
        asked: list[str] = []
        monkeypatch.setattr("cube_net.ui.settings_panel.section.confirm_restore", lambda _p, name: asked.append(name))
        tab.sections[tabs.FACE_TILING].restore_button.click()
        assert asked == ["Faces tiling"]
        assert self.style(window).hatch_columns == 3  # said no
        monkeypatch.setattr("cube_net.ui.settings_panel.section.confirm_restore", lambda *_: True)
        tab.sections[tabs.FACE_TILING].restore_button.click()
        assert self.style(window).hatch_columns == DEFAULT_STYLE.hatch_columns
        assert tab.hatch_columns.value() == DEFAULT_STYLE.hatch_columns
        assert self.style(window).edge_width == 9  # only that section


class TestBlinkSetting:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def succeed(self, window: MainWindow) -> None:
        window.bounding.target.setValue(13)  # the cross has 12.000

    def test_on_by_default(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.settings_panel.preferences.blink.isChecked()
        self.succeed(window)
        assert window.bounding.blinking

    def test_off_means_steadily_green(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        self.succeed(window)
        window.settings_panel.preferences.blink.setChecked(False)
        assert not window.bounding.blinking and window.bounding.success
        assert window.settings.blink_on_success is False
        window.save_project_to(tmp_path / "cube.cubenet")
        window.settings_panel.preferences.blink.setChecked(True)
        assert not window.is_dirty  # an app setting, not the project's
        window.settings_panel.preferences.blink.setChecked(False)
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1] == "settings blink off"
        window.stop_recording("test over")

    def test_used_from_the_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        settings = settings_in(tmp_path, record=False)
        settings.blink_on_success = False
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        assert not window.settings_panel.preferences.blink.isChecked()
        self.succeed(window)
        assert not window.bounding.blinking and window.bounding.success


class TestLastSettingsTab:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
        settings.record_session = False
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_preferences_the_first_time(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        assert window.settings_panel.tab_name() == "preferences"

    def test_the_same_tab_when_opened_again(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.settings_panel.show_tab("Style")
        window.settings_action.trigger()
        window.settings_action.trigger()
        assert window.settings_panel.tab_name() == "style"

    def test_and_in_the_next_run(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.settings_panel.show_tab("Style")
        other = self.make(qtbot, tmp_path)
        other.settings_action.trigger()
        assert other.settings_panel.tab_name() == "style"


class TestSettingsPanelOpenAtStart:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
        settings.record_session = False
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        window.resize(1200, 800)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_open_the_first_time(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.settings_panel.isVisible()
        assert window.settings_action.isChecked()

    def test_left_open_starts_open_in_its_place(self, qtbot: QtBot, tmp_path: Path) -> None:
        first = self.make(qtbot, tmp_path)
        first.settings_action.trigger()
        first.settings_action.trigger()  # hidden and shown again: left open
        window = self.make(qtbot, tmp_path)
        assert window.settings_action.isChecked()
        assert window.settings_panel.isVisible()
        view = in_window(window.sheet_view)
        qtbot.waitUntil(lambda: window.settings_panel.geometry().right() == view.right())
        assert window.settings_panel.height() == window.sheet_view.height()

    def test_left_closed_starts_closed(self, qtbot: QtBot, tmp_path: Path) -> None:
        self.make(qtbot, tmp_path).settings_action.trigger()  # open the first time: this hides it
        assert not self.make(qtbot, tmp_path).settings_panel.isVisible()

    def test_the_hide_button_is_like_clicking_settings(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        window.settings_panel.hide_button.click()
        assert not window.settings_panel.isVisible()
        assert not window.settings_action.isChecked()
        assert window.settings.settings_open is False
        window.settings_action.trigger()
        assert window.settings_panel.isVisible()


def test_no_number_field_of_the_window_takes_the_wheel(qtbot: QtBot, tmp_path: Path) -> None:
    from PyQt6.QtGui import QWheelEvent
    from PyQt6.QtWidgets import QAbstractSpinBox, QApplication

    window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.show()
    window.settings_action.trigger()
    qtbot.waitExposed(window)
    fields = window.findChildren(QAbstractSpinBox)
    assert window.bounding.target in fields and window.settings_panel.style_tab.edge_width in fields
    assert len(fields) == 8  # target area, max zoom, tiling (2), dashes, thickness, radius, grid
    before = [field.text() for field in fields]
    for field in fields:
        pos = QPointF(field.width() / 2, field.height() / 2)
        event = QWheelEvent(
            pos,
            field.mapToGlobal(pos),
            QPoint(0, 0),
            QPoint(0, 360),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.sendEvent(field, event)
    assert [field.text() for field in fields] == before
    assert not window.is_dirty


class TestLanguage:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
        settings.record_session = record
        window = MainWindow(settings=settings, session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def choose(self, window: MainWindow, name: str) -> None:
        box = window.settings_panel.preferences.language
        box.setCurrentIndex(box.findText(name))

    def texts(self, window: MainWindow) -> dict[str, str]:
        menu_bar = window.menuBar()
        assert menu_bar is not None
        prefs = window.settings_panel.preferences
        return {
            "menus": " ".join(a.text() for a in menu_bar.actions()),
            "open": window.open_action.text(),
            "ruler": window.ruler_action.text(),
            "target": window.bounding.target_label.text(),
            "area": window.bounding.label.text().split("\n")[0],
            "tabs": " ".join(window.settings_panel.tabs.tabText(i) for i in range(2)),
            "labels": prefs.show_labels.text(),
            "language": prefs.language_label.text(),
            "title": window.windowTitle(),
        }

    def test_first_in_preferences(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        prefs = window.settings_panel.preferences
        box = prefs.language
        assert [box.itemText(i) for i in range(box.count())] == ["English", "Русский"]
        assert prefs.language_label.text() == "Language"
        layout = prefs.layout()
        assert layout is not None
        first = layout.itemAt(0)
        assert first is not None and first.layout() is not None
        assert first.layout().indexOf(box) >= 0  # type: ignore[union-attr]

    def test_everything_changes_at_once(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        english = self.texts(window)
        self.choose(window, "Русский")
        russian = self.texts(window)
        assert russian == {
            "menus": "&Файл &Правка &Настройки &Справка",
            "open": "&Открыть...",
            "ruler": "Линейка",
            "target": "Цель",
            "area": "Площадь",
            "tabs": "Основные Стиль",
            "labels": "Показывать метки вершин",
            "language": "Язык",
            "title": "[*]Без имени — Cube Net",
        }
        self.choose(window, "English")
        assert self.texts(window) == english

    def test_the_list_does_not_move(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.settings_action.trigger()
        box = window.settings_panel.preferences.language
        before = box.mapTo(window, box.rect().topLeft())
        self.choose(window, "Русский")
        qtbot.wait(20)
        assert box.mapTo(window, box.rect().topLeft()) == before

    def test_remembered_and_used_at_start(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.i18n import Language

        window = self.make(qtbot, tmp_path, record=True)
        self.choose(window, "Русский")
        assert window.settings.language is Language.RUSSIAN
        assert window.recorder is not None
        assert session_lines(window.recorder.log.path)[-1] == "settings language ru"
        window.stop_recording("test over")
        other = self.make(qtbot, tmp_path)
        assert other.ruler_action.text() == "Линейка"
        assert other.settings_panel.preferences.language.currentText() == "Русский"

    def test_also_in_help_one_setting(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.ui.i18n import Language

        window = self.make(qtbot, tmp_path)
        window.help_action.trigger()
        help_window = window.help_window
        assert help_window is not None
        box = help_window.language
        box.setCurrentIndex(box.findText("Русский"))
        assert window.settings.language is Language.RUSSIAN and window.ruler_action.text() == "Линейка"
        assert window.settings_panel.preferences.language.currentText() == "Русский"
        self.choose(window, "English")  # and the other way round
        assert box.currentText() == "English"

    def test_not_a_change_of_the_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.choose(window, "Русский")
        assert not window.is_dirty

    def test_the_wheel_does_not_change_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        from PyQt6.QtGui import QWheelEvent
        from PyQt6.QtWidgets import QApplication

        window = self.make(qtbot, tmp_path)
        box = window.settings_panel.preferences.language
        pos = QPointF(box.width() / 2, box.height() / 2)
        event = QWheelEvent(
            pos,
            box.mapToGlobal(pos),
            QPoint(0, 0),
            QPoint(0, -360),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.sendEvent(box, event)
        assert box.currentText() == "English"

    def test_error_messages_in_the_language(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        self.choose(window, "Русский")
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _parent, _title, text, **_: told.append(text))
        bad = tmp_path / "bad.cubenet"
        bad.write_text("Hello!")
        window.open_project_from(bad)
        assert told == [f"Не удалось открыть {bad}. Это не проект Cube Net."]


def test_the_settings_panel_takes_the_width_its_texts_need(qtbot: QtBot, tmp_path: Path) -> None:
    from cube_net.ui.i18n import TRANSLATIONS, Language

    window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
    qtbot.addWidget(window)
    window.resize(1500, 900)
    window.show()
    qtbot.waitExposed(window)
    window.settings_action.trigger()
    placed: list[int] = []
    original = window.settings_panel.place_over
    window.settings_panel.place_over = lambda area, width: (placed.append(1), original(area, width))  # type: ignore[method-assign]
    TRANSLATIONS.set_language(Language.RUSSIAN)
    assert placed
