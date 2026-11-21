# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main window: new, open and save, unsaved changes, nothing open, files from outside, the saved state."""

from fractions import Fraction as F
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot
from window_checks import session_lines, settings_in

from cube_net.ui.dialogs.new_project_window import NewProjectChoice, Start, builtin_project
from cube_net.ui.main_window import (
    APP_TITLE,
    MainWindow,
)
from cube_net.ui.save_changes_dialog import SaveChoice


class TestProjects:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def close_line(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def rearrange(self, window: MainWindow) -> None:
        self.close_line(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))

    def shown(self, window: MainWindow) -> tuple[object, ...]:
        item = window.sheet_view.net_item()
        assert item is not None
        labels = item.labels() or {}
        return (
            window.editor.state,
            sorted(str(v.position) for v in window.net.vertices),
            [p.position for p in window.cut_tool.item.points()],
            len(item.glue()),
            len(item.overlapping()),
            window.bounding.label.text(),
            window.cut_tool.approve_button.position(),
            window.approve_action.isEnabled(),
            window.undo_action.isEnabled(),
            window.redo_action.isEnabled(),
            sorted((str(v.position), str(name)) for v, name in labels.items()),
            [(p, name) for p, name in window.cut_tool.item.labels()],
        )

    def reopened(self, qtbot: QtBot, tmp_path: Path, window: MainWindow) -> MainWindow:
        """The project in another window, as after a restart."""
        path = tmp_path / "cube.cubenet"
        assert window.save_project_to(path)
        other = self.make(qtbot, tmp_path)
        assert other.open_project_from(path)
        return other

    def test_every_state_comes_back_as_it_was_shown(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        view.left_pressed.emit(11.5, 14 - h)
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        view.left_pressed.emit(11.75, 10 + h)
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        window.approve_action.trigger()
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)
        window.undo_action.trigger()
        assert self.shown(self.reopened(qtbot, tmp_path, window)) == self.shown(window)

    def test_undo_and_redo_work_after_reopening(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearrange(window)
        window.approve_action.trigger()
        other = self.reopened(qtbot, tmp_path, window)
        other.undo_action.trigger()
        window.undo_action.trigger()
        assert self.shown(other) == self.shown(window)
        for _ in range(2):
            other.redo_action.trigger()
            window.redo_action.trigger()
            assert self.shown(other) == self.shown(window)
        assert other.editor.state.value == "default"

    def test_the_tools_work_on_the_opened_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.rearrange(window)
        other = self.reopened(qtbot, tmp_path, window)
        other.approve_action.trigger()
        assert other.editor.state.value == "default"
        assert other.net is other.editor.net
        h = self.hitbox(other)
        other.sheet_view.mouse_moved.emit(10 + h, 12.5)
        assert other.cut_hover.hovered() is not None
        other.sheet_view.left_pressed.emit(10 + h, 12.5)
        assert other.editor.state.value == "cutting"

    def test_an_overlap_comes_back(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(12 - h, 13.5)
        view.left_pressed.emit(11 + h, 11.5)
        view.left_pressed.emit(12.75, 13 - h)
        other = self.reopened(qtbot, tmp_path, window)
        item = other.sheet_view.net_item()
        assert item is not None and item.overlapping()
        assert not other.cut_tool.approve_button.enabled()
        other.sheet_view.left_pressed.emit(12.75, 13.0)  # the "x" undoes it, for good
        other.sheet_view.left_released.emit(12.75, 13.0)
        assert other.editor.state.value == "cut_editing"
        assert not other.redo_action.isEnabled()

    def test_settings_come_back_and_are_used(self, qtbot: QtBot, tmp_path: Path) -> None:
        from fractions import Fraction

        from cube_net.core.project_settings import ProjectSettings

        window = self.make(qtbot, tmp_path)
        window.project_settings = ProjectSettings(Fraction(5))
        other = self.reopened(qtbot, tmp_path, window)
        assert other.project_settings.area_threshold == 5

    def test_a_drag_in_progress_is_forgotten(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        path = tmp_path / "cube.cubenet"
        assert window.save_project_to(path)
        window.sheet_view.left_pressed.emit(11.5, 13.5)
        window.sheet_view.mouse_moved.emit(11.7, 13.7)
        assert window.cut_tool.dragging
        assert window.open_project_from(path)
        assert not window.cut_tool.dragging
        assert window.undo_action.isEnabled()
        window.sheet_view.left_released.emit(11.7, 13.7)  # nothing happens
        line = window.editor.cut_line
        assert line is not None and float(line.points[1].position.x) == 11.5

    def test_the_title_tells_the_file(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert "cube.cubenet" not in window.windowTitle()
        window.save_project_to(tmp_path / "cube.cubenet")
        assert window.windowTitle().startswith("[*]cube.cubenet")
        assert window.project_path == tmp_path / "cube.cubenet"

    def test_opening_a_bad_file_tells_and_changes_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        before = self.shown(window)
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _parent, _title, text, **_: told.append(text))
        bad = tmp_path / "bad.cubenet"
        bad.write_text("Hello!")
        assert not window.open_project_from(bad)
        assert len(told) == 1 and "bad.cubenet" in told[0]
        assert self.shown(window) == before
        assert window.project_path is None

    def test_saving_to_a_bad_place_tells_and_changes_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _parent, _title, text, **_: told.append(text))
        assert not window.save_project_to(tmp_path / "nowhere" / "cube.cubenet")
        assert len(told) == 1
        assert window.project_path is None

    def test_file_menu_comes_first(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        menu_bar = window.menuBar()
        assert menu_bar is not None
        assert menu_bar.actions()[0].text() == "&File"
        assert window.open_action.shortcut().toString() == "Ctrl+O"
        assert window.save_as_action.shortcut().toString() == "Ctrl+Shift+S"

    def test_save_as_adds_the_ending(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PyQt6.QtWidgets import QFileDialog

        window = self.make(qtbot, tmp_path)
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: (str(tmp_path / "cube"), ""))
        window.save_as_action.trigger()
        assert (tmp_path / "cube.cubenet").exists()

    def test_cancelled_dialogs_do_nothing(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PyQt6.QtWidgets import QFileDialog

        window = self.make(qtbot, tmp_path)
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: ("", ""))
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: ("", ""))
        window.save_as_action.trigger()
        window.open_action.trigger()
        assert window.project_path is None

    def test_open_through_the_menu(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PyQt6.QtWidgets import QFileDialog

        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        other = self.make(qtbot, tmp_path)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(path), ""))
        other.open_action.trigger()
        assert other.editor.state.value == "cut_editing"

    def test_recorded(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert lines[-1] == f"project saved {path}"
        window.open_project_from(path)
        lines = session_lines(window.recorder.log.path)
        assert f"project opened {path}" in lines
        assert f"state project {path}" in lines
        window.stop_recording("test over")


class TestUnsavedChanges:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        window.activateWindow()
        qtbot.waitUntil(window.isActiveWindow)
        return window

    def hitbox(self, window: MainWindow) -> float:
        from cube_net.ui.sheet import net_style

        return net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()

    def start_line(self, window: MainWindow) -> None:
        window.sheet_view.left_pressed.emit(11.5, 14 - self.hitbox(window))

    def close_line(self, window: MainWindow) -> None:
        h = self.hitbox(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)

    def answer(self, monkeypatch: pytest.MonkeyPatch, *choices: object) -> list[str]:
        """Make the question answer this, and "don't save" after that (the window gets closed when the test ends);
        returns the list of the projects it was asked about."""

        remaining = list(choices)
        asked: list[str] = []

        def ask(_parent: object, name: str) -> object:
            asked.append(name)
            return remaining.pop(0) if remaining else SaveChoice.DISCARD

        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", ask)
        return asked

    def file_dialogs(self, monkeypatch: pytest.MonkeyPatch, save: str = "", open_: str = "") -> list[str]:
        """Make the file dialogs answer this; returns the list of the dialogs that were shown."""
        from PyQt6.QtWidgets import QFileDialog

        shown: list[str] = []

        def show_save(*_: object) -> tuple[str, str]:
            shown.append("save")
            return save, ""

        def show_open(*_: object) -> tuple[str, str]:
            shown.append("open")
            return open_, ""

        monkeypatch.setattr(QFileDialog, "getSaveFileName", show_save)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", show_open)
        return shown

    # --- what counts as a change -------------------------------------------------------------------------------------

    def test_a_new_window_has_none(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.is_dirty
        assert not window.isWindowModified()

    def test_every_action_is_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        view = window.sheet_view
        h = self.hitbox(window)

        def check(action: object) -> None:
            assert window.save_project_to(path)
            assert not window.isWindowModified()
            assert callable(action)
            action()
            assert window.is_dirty
            assert window.isWindowModified()

        check(lambda: view.left_pressed.emit(11.5, 14 - h))  # the first point
        check(lambda: view.left_pressed.emit(11.5, 13.5))  # a point
        check(lambda: view.left_pressed.emit(12 - h, 13.5))  # the last point

        def move() -> None:
            view.left_pressed.emit(11.5, 13.5)
            view.mouse_moved.emit(11.6, 13.6)
            view.left_released.emit(11.6, 13.6)

        check(move)
        check(window.undo_action.trigger)
        check(window.redo_action.trigger)
        check(lambda: view.left_pressed.emit(11.75, 10 + h))  # rearranged
        check(window.approve_action.trigger)

    def test_what_changes_nothing_is_not_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.save_project_to(tmp_path / "cube.cubenet")
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)  # pressed and released without moving
        view.left_released.emit(11.5, 13.5)
        assert not window.is_dirty
        h = self.hitbox(window)
        view.left_pressed.emit(10.5, 12 + h)  # a useless cut flashes
        assert not window.is_dirty
        view.mouse_moved.emit(11.5, 12.5)
        assert not window.isWindowModified()
        window.ruler_tool.set_active(True)
        view.left_pressed.emit(7.0, 7.0)
        assert not window.is_dirty

    def test_undoing_back_to_the_saved_state_is_still_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        """The history is saved too, and it's not what it was."""
        window = self.make(qtbot, tmp_path)
        self.start_line(window)
        window.save_project_to(tmp_path / "cube.cubenet")
        window.sheet_view.left_pressed.emit(11.5, 13.5)
        window.undo_action.trigger()
        assert window.isWindowModified()

    def test_the_title_shows_the_name(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.windowTitle().startswith("[*]Untitled")
        window.save_project_to(tmp_path / "cube.cubenet")
        assert window.windowTitle().startswith("[*]cube.cubenet")

    # --- Save --------------------------------------------------------------------------------------------------------

    def test_save_without_a_file_asks_for_a_name(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        shown = self.file_dialogs(monkeypatch, save=str(tmp_path / "cube"))
        self.start_line(window)
        window.save_action.trigger()
        assert shown == ["save"]
        assert window.project_path == tmp_path / "cube.cubenet"
        assert not window.is_dirty

    def test_save_with_a_file_just_saves(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.core.project import load_project

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        shown = self.file_dialogs(monkeypatch)
        self.start_line(window)
        window.save_action.trigger()
        assert shown == []
        assert not window.is_dirty
        assert load_project(path).state.points is not None

    def test_ctrl_s(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.save_project_to(tmp_path / "cube.cubenet")
        self.start_line(window)
        qtbot.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
        assert not window.is_dirty

    def test_save_cancelled_changes_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        self.file_dialogs(monkeypatch)
        self.start_line(window)
        window.save_action.trigger()
        assert window.is_dirty
        assert window.project_path is None

    def test_save_as_moves_to_the_new_file(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        window = self.make(qtbot, tmp_path)
        window.save_project_to(tmp_path / "a.cubenet")
        self.file_dialogs(monkeypatch, save=str(tmp_path / "b.cubenet"))
        self.start_line(window)
        window.save_as_action.trigger()
        assert window.project_path == tmp_path / "b.cubenet"
        assert not window.is_dirty

    def test_a_failed_save_leaves_the_changes_unsaved(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda *_, **__: None)
        self.start_line(window)
        assert not window.save_project_to(tmp_path / "nowhere" / "cube.cubenet")
        assert window.is_dirty
        assert window.isWindowModified()

    # --- New ---------------------------------------------------------------------------------------------------------

    def test_new_with_nothing_to_lose_does_not_ask(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        asked = self.answer(monkeypatch)
        window.new_action.trigger()
        assert asked == []

    def test_new_starts_all_over(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from fractions import Fraction

        from cube_net.core.project_settings import DEFAULT_AREA_THRESHOLD, ProjectSettings

        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.sheet_view.left_pressed.emit(11.75, 10 + self.hitbox(window))
        window.approve_action.trigger()
        window.project_settings = ProjectSettings(Fraction(5))
        window.save_project_to(tmp_path / "cube.cubenet")
        names_before = window.point_labels.saved()[0]
        assert names_before
        window.new_action.trigger()
        assert window.editor.state.value == "default"
        assert window.editor.approved_cuts == 0
        assert window.net is window.editor.net
        assert window.bounding.label.text() == "Area\n12.000"
        assert window.cut_tool.item.points() == ()
        assert not window.undo_action.isEnabled() and not window.redo_action.isEnabled()
        assert window.project_path is None
        assert window.windowTitle().startswith("[*]Untitled")
        assert not window.is_dirty and not window.isWindowModified()
        assert window.project_settings.area_threshold == DEFAULT_AREA_THRESHOLD
        assert window.point_labels.saved()[0] == {}

    def test_new_cancel(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        window = self.make(qtbot, tmp_path)
        asked = self.answer(monkeypatch, SaveChoice.CANCEL)
        self.close_line(window)
        window.new_action.trigger()
        assert asked == ["Untitled"]
        assert window.editor.state.value == "cut_editing"
        assert window.is_dirty

    def test_new_discard(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        saved = path.read_bytes()
        asked = self.answer(monkeypatch, SaveChoice.DISCARD)
        self.close_line(window)
        window.new_action.trigger()
        assert asked == ["cube.cubenet"]
        assert window.editor.state.value == "default"
        assert path.read_bytes() == saved

    def test_new_save(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.core.project import load_project

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        self.answer(monkeypatch, SaveChoice.SAVE)
        self.close_line(window)
        window.new_action.trigger()
        assert window.editor.state.value == "default"
        assert window.project_path is None
        assert load_project(path).state.points is not None

    def test_new_save_but_the_name_is_cancelled(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.SAVE)
        shown = self.file_dialogs(monkeypatch)
        self.close_line(window)
        window.new_action.trigger()
        assert shown == ["save"]
        assert window.editor.state.value == "cut_editing"
        assert window.is_dirty

    def test_new_save_but_saving_fails(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        window = self.make(qtbot, tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda *_, **__: None)
        self.answer(monkeypatch, SaveChoice.SAVE)
        self.file_dialogs(monkeypatch, save=str(tmp_path / "nowhere" / "cube.cubenet"))
        self.close_line(window)
        window.new_action.trigger()
        assert window.editor.state.value == "cut_editing"

    def test_the_tools_work_after_new(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        window.new_action.trigger()
        self.close_line(window)
        assert window.editor.state.value == "cut_editing"
        window.undo_action.trigger()
        assert window.editor.state.value == "cutting"

    def test_new_cube_with_a_hole(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.core.project.builtin_templates import cube_with_a_hole
        from cube_net.ui import palette
        from cube_net.ui.sheet import net_style

        monkeypatch.setattr(
            "cube_net.ui.main_window.choose_new_project",
            lambda *_: NewProjectChoice(Start.CUBE_WITH_A_HOLE, None, builtin_project(Start.CUBE_WITH_A_HOLE)),
        )
        window = self.make(qtbot, tmp_path)
        window.new_action.trigger()
        body = window.net.body
        template = cube_with_a_hole()
        assert len(body.face_numbers) == len({face.color for face in template.state.template.faces})  # one per colour
        assert window.editor.origin == template.state.origin
        assert window.project_settings.style == template.style
        assert template.style is not None and template.style.hatch_rows == net_style.HATCH_ROWS
        assert len(window.settings_panel.style_tab.face_fields) == len(body.face_numbers)
        assert palette.face_color(body, 1).name().upper() == template.state.template.faces[0].color
        assert window.project_path is None and not window.is_dirty
        self.close_line(window)  # the tools work on it

    def test_new_cancelled_in_its_window(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cube_net.ui.main_window.choose_new_project", lambda *_: None)
        window = self.make(qtbot, tmp_path)
        asked = self.answer(monkeypatch)
        self.close_line(window)
        window.new_action.trigger()
        assert asked == []  # nothing to leave
        assert window.editor.state.value == "cut_editing"

    def test_new_with_a_template_that_is_not_valid_opens_it(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.core.history import History
        from cube_net.core.project import TemplateDocument
        from cube_net.core.template import TemplateEditor, TemplateSnapshot

        path = tmp_path / "unfinished.nettemplate"
        document = TemplateDocument(TemplateSnapshot(TemplateEditor().template), History())
        monkeypatch.setattr(
            "cube_net.ui.main_window.choose_new_project",
            lambda *_: NewProjectChoice(Start.CUSTOM, path, template=document),
        )
        window = self.make(qtbot, tmp_path)
        window.new_action.trigger()
        assert window.in_template_mode and window.template_mode.path == path
        assert window.settings.last_project == path

    # --- Open --------------------------------------------------------------------------------------------------------

    def test_open_cancel_shows_no_file_dialog(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.CANCEL)
        shown = self.file_dialogs(monkeypatch)
        self.close_line(window)
        window.open_action.trigger()
        assert shown == []
        assert window.editor.state.value == "cut_editing"

    def test_open_discard(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        self.answer(monkeypatch, SaveChoice.DISCARD)
        self.file_dialogs(monkeypatch, open_=str(path))
        self.close_line(window)
        window.open_action.trigger()
        assert window.editor.state.value == "default"
        assert not window.is_dirty

    def test_open_dialog_cancelled_keeps_the_changes(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.DISCARD)
        self.file_dialogs(monkeypatch)
        self.close_line(window)
        window.open_action.trigger()
        assert window.editor.state.value == "cut_editing"
        assert window.is_dirty

    def test_an_opened_project_has_no_changes(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        window.open_project_from(path)
        assert not window.is_dirty and not window.isWindowModified()
        window.undo_action.trigger()
        assert window.is_dirty and window.isWindowModified()

    # --- Quit --------------------------------------------------------------------------------------------------------

    def test_quit_with_nothing_to_lose_does_not_ask(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        asked = self.answer(monkeypatch)
        window.quit_action.trigger()
        assert asked == []
        assert not window.isVisible()

    def test_quit_cancel_stays(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.CANCEL)
        self.close_line(window)
        window.quit_action.trigger()
        assert window.isVisible()
        assert window.is_dirty

    def test_quit_discard_goes(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.DISCARD)
        self.close_line(window)
        window.quit_action.trigger()
        assert not window.isVisible()

    def test_quit_save_goes(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.core.project import load_project

        window = self.make(qtbot, tmp_path)
        path = tmp_path / "cube.cubenet"
        window.save_project_to(path)
        self.answer(monkeypatch, SaveChoice.SAVE)
        self.close_line(window)
        window.quit_action.trigger()
        assert not window.isVisible()
        assert load_project(path).state.points is not None

    def test_quit_save_cancelled_stays(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.SAVE)
        self.file_dialogs(monkeypatch)
        self.close_line(window)
        window.quit_action.trigger()
        assert window.isVisible()

    def test_closing_the_window_is_quitting(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        asked = self.answer(monkeypatch, SaveChoice.CANCEL, SaveChoice.DISCARD)
        self.close_line(window)
        assert not window.close()
        assert window.isVisible()
        assert window.close()
        assert asked == ["Untitled", "Untitled"]

    def test_closing_during_a_drag_forgets_it(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        window = self.make(qtbot, tmp_path)
        self.answer(monkeypatch, SaveChoice.CANCEL)
        self.close_line(window)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)
        view.mouse_moved.emit(11.7, 13.7)
        assert window.cut_tool.dragging
        assert not window.close()
        assert not window.cut_tool.dragging
        assert window.undo_action.isEnabled()
        line = window.editor.cut_line
        assert line is not None and float(line.points[1].position.x) == 11.5
        assert float(window.cut_tool.item.points()[1].position.x) == 11.5

    # --- the rest ----------------------------------------------------------------------------------------------------

    def test_not_while_dragging(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.close_line(window)
        actions = (
            window.new_action,
            window.open_action,
            window.save_action,
            window.save_as_action,
            window.quit_action,
        )
        assert all(action.isEnabled() for action in actions)
        view = window.sheet_view
        view.left_pressed.emit(11.5, 13.5)
        assert not any(action.isEnabled() for action in actions)
        view.left_released.emit(11.5, 13.5)
        assert all(action.isEnabled() for action in actions)

    def test_shortcuts_and_order(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.new_action.shortcut().toString() == "Ctrl+N"
        assert window.save_action.shortcut().toString() == "Ctrl+S"
        assert window.quit_action.shortcut().toString() == "Ctrl+Q"
        menu = window.new_action.associatedObjects()[0]
        texts = [a.text() for a in menu.actions() if not a.isSeparator()]  # type: ignore[union-attr]
        assert texts == ["&New", "New &Template", "&Open...", "&Save", "Save &As...", "&Quit"]
        assert window.new_template_action.shortcut().toString() == "Ctrl+T"

    def test_recorded(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        window = MainWindow(settings=settings_in(tmp_path, record=True), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        self.answer(monkeypatch, SaveChoice.DISCARD)
        self.close_line(window)
        window.new_action.trigger()
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert "project unsaved changes discard" in lines
        assert "project new cube" in lines
        assert "state project untitled" in lines[lines.index("project new cube") :]
        window.stop_recording("test over")


class TestNothingOpen:
    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path, empty=True)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_the_grey_area_and_nothing_that_works_on_a_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert window.nothing_open and window.stack.currentWidget() is window.empty_area
        assert window.windowTitle() == APP_TITLE and not window.is_dirty and window.save_state.text() == ""
        for action in (window.save_action, window.save_as_action, window.undo_action, window.redo_action):
            assert not action.isEnabled()
        assert not window.approve_action.isEnabled() and not window.validate_action.isEnabled()
        for action in (window.new_action, window.new_template_action, window.open_action, window.quit_action):
            assert action.isEnabled()
        assert not window.ruler_action.isVisible() and not window.bounding.action.isVisible()
        assert not window.net_area.action.isVisible()
        assert not window.settings_panel.style_tab.isEnabled()

    def test_a_project_ends_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.new_action.trigger()  # the Cube
        assert not window.nothing_open and window.stack.currentWidget() is window.sheet_view
        assert window.windowTitle().startswith("[*]Untitled")
        assert window.ruler_action.isVisible() and window.bounding.action.isVisible()
        assert window.settings_panel.style_tab.isEnabled() and window.save_as_action.isEnabled()

    def test_a_template_ends_it(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.new_template_action.trigger()
        assert not window.nothing_open and window.in_template_mode
        assert window.net_area.action.isVisible() and window.settings_panel.style_tab.isEnabled()

    def test_closing_asks_nothing(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        asked: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda _p, name: asked.append(name))
        window = self.make(qtbot, tmp_path)
        window.close()
        assert asked == [] and not window.isVisible()


class TestProjectFilesFromOutside:
    """A project file given at start (a double-click on Windows and Linux), or asked for while running (macOS)."""

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def saved(self, qtbot: QtBot, tmp_path: Path, name: str) -> Path:
        window = self.make(qtbot, tmp_path)
        path = tmp_path / name
        assert window.save_project_to(path)
        window.close()
        return path

    def test_at_start_instead_of_the_last_one(self, qtbot: QtBot, tmp_path: Path) -> None:
        last = self.saved(qtbot, tmp_path, "last.cubenet")
        given = self.saved(qtbot, tmp_path, "given.cubenet")
        window = self.make(qtbot, tmp_path)
        window.settings.last_project = last
        window.open_project_at_start(given)
        assert window.project_path == given
        assert window.settings.last_project == given  # it's the one worked on now

    def test_at_start_a_broken_one_lets_the_user_decide(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        broken = tmp_path / "broken.cubenet"
        broken.write_bytes(b"not a project")
        asked: list[str] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_after_load_failed",
            lambda _parent, message: asked.append(message) or AfterLoadFailed.NEW_PROJECT,
        )
        window = self.make(qtbot, tmp_path)
        window.open_project_at_start(broken)
        assert len(asked) == 1 and window.project_path is None  # a new project

    def test_asked_for_while_running(self, qtbot: QtBot, tmp_path: Path) -> None:
        given = self.saved(qtbot, tmp_path, "given.cubenet")
        window = self.make(qtbot, tmp_path)
        window.open_project_requested(given)
        assert window.project_path == given

    def test_unsaved_changes_are_asked_about_first(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        given = self.saved(qtbot, tmp_path, "given.cubenet")
        window = self.make(qtbot, tmp_path)
        window._on_target_changed(F(5))  # an unsaved change
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.CANCEL)
        window.open_project_requested(given)
        assert window.project_path is None  # kept
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)
        window.open_project_requested(given)
        assert window.project_path == given

    def test_the_same_project_just_comes_to_the_front(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        given = self.saved(qtbot, tmp_path, "given.cubenet")
        window = self.make(qtbot, tmp_path)
        window.open_project_requested(given)
        window._on_target_changed(F(5))
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: pytest.fail("not asked"))
        window.open_project_requested(given)
        assert window.is_dirty  # nothing reloaded, the change is still there
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)  # closing


class TestSavedOrNot:
    """The user sees whether there are unsaved changes, and that saving did something."""

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def change(self, window: MainWindow) -> None:
        from cube_net.ui.sheet import net_style

        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - net_style.CUT_HITBOX_PX / 2 / view.scale_factor())  # a cut started

    def test_a_new_project_says_nothing(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        assert not window.isWindowModified() and window.save_state.text() == ""

    def test_a_change_shows(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)  # closing
        window = self.make(qtbot, tmp_path)
        self.change(window)
        assert window.isWindowModified()  # the "*" before the name
        assert window.windowTitle().startswith("[*]")
        assert window.save_state.text() == "Unsaved changes"

    def test_saving_shows_where_and_that_all_is_saved(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        self.change(window)
        path = tmp_path / "net.cubenet"
        assert window.save_project_to(path)
        assert not window.isWindowModified()
        assert window.save_state.text() == "Saved"
        assert window.statusBar().currentMessage() == f"Saved to {path}"

    def test_saving_without_changes_still_answers(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        path = tmp_path / "net.cubenet"
        window.save_project_to(path)
        window.statusBar().clearMessage()
        window.save_action.trigger()  # Ctrl+S with nothing changed
        assert window.statusBar().currentMessage() == f"Saved to {path}"

    def test_undo_is_a_change_too(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The project's file has its history: after an undo it would be another file."""

        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)  # closing
        window = self.make(qtbot, tmp_path)
        self.change(window)
        window.save_project_to(tmp_path / "net.cubenet")
        window.undo_action.trigger()
        assert window.save_state.text() == "Unsaved changes" and window.isWindowModified()
