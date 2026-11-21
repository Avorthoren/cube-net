# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main window: making a template."""

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from window_checks import session_lines, settings_in

from cube_net.ui.main_window import (
    APP_TITLE,
    MainWindow,
)
from cube_net.ui.save_changes_dialog import SaveChoice


class TestTemplates:
    """File -> New Template: making a template in the same window, on its own sheet."""

    PILLOW = ((10, 10), (11, 10), (12, 10), (12, 11), (11, 11), (10, 11))

    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=record), session_dir=tmp_path)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def draw(self, window: MainWindow) -> None:
        view = window.template_mode.view
        for x, y in [*self.PILLOW, self.PILLOW[0]]:
            view.left_pressed.emit(float(x), float(y))

    def torus_template_in(self, window: MainWindow, tmp_path: Path, new_color: str | None = None) -> Path:
        """The built-in Cube with a hole, saved and opened; `new_color`: then its one-piece face of the first colour
        used once gets that colour (an unsaved change)."""
        from collections import Counter

        from cube_net.core.project import save_template
        from cube_net.core.project.builtin_templates import cube_with_a_hole

        path = tmp_path / "torus.nettemplate"
        save_template(cube_with_a_hole(), path)
        assert window.open_project_from(path)
        if new_color is not None:
            faces = window.template_mode.editor.template.faces
            counts = Counter(face.color for face in faces)
            index = next(i for i, face in enumerate(faces) if counts[face.color] == 1)
            window.template_mode.tool.set_face_color(index, new_color)
        return path

    def validated(self, window: MainWindow, monkeypatch: pytest.MonkeyPatch, save: bool = False) -> list[str]:
        asked: list[str] = []
        monkeypatch.setattr(
            "cube_net.ui.template.template_mode.ask_yes_no", lambda _p, text: asked.append(text) or save
        )
        window.validate_action.trigger()
        return asked

    def test_validated_saved_when_the_user_says_so(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.core.project import TemplateDocument, load_document
        from cube_net.core.template import ValidationStatus

        window = self.make(qtbot, tmp_path)
        path = self.torus_template_in(window, tmp_path, "#123456")
        assert self.validated(window, monkeypatch, save=True) == ["No problems found.\nSave the template?"]
        assert not window.is_dirty
        document = load_document(path)
        assert isinstance(document, TemplateDocument) and document.validation is ValidationStatus.VALID
        assert "#123456" in [face.color for face in document.state.template.faces]

    def test_validated_untitled_saved_as(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.core.project.builtin_templates import cube_with_a_hole

        window = self.make(qtbot, tmp_path)
        window._show_template(cube_with_a_hole(), None)
        path = tmp_path / "mine"
        monkeypatch.setattr("cube_net.ui.main_window.QFileDialog.getSaveFileName", lambda *_: (str(path), ""))
        self.validated(window, monkeypatch, save=True)
        assert path.with_suffix(".nettemplate").exists() and not window.is_dirty

    def test_create_network_only_while_validated(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        button = window.create_network_button
        assert not button.action.isVisible()  # a project
        self.torus_template_in(window, tmp_path)
        assert button.action.isVisible() and button.button.text() == "Create\nnetwork"
        assert not button.button.isEnabled()
        self.validated(window, monkeypatch)
        assert button.button.isEnabled()
        window.template_mode.tool.set_face_color(0, "#123456")  # not the template validated any more
        assert not button.button.isEnabled()
        window.undo_action.trigger()
        assert button.button.isEnabled()  # the validated one again

    @pytest.mark.parametrize("choice", [SaveChoice.SAVE, SaveChoice.DISCARD, SaveChoice.CANCEL])
    def test_create_network_from_the_template_as_it_is(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, choice: SaveChoice
    ) -> None:
        from cube_net.core.project import TemplateDocument, load_document

        window = self.make(qtbot, tmp_path)
        path = self.torus_template_in(window, tmp_path, "#123456")
        self.validated(window, monkeypatch)
        asked: list[str] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_save_changes", lambda _parent, name: asked.append(name) or choice
        )
        window.create_network_button.button.click()
        assert asked == ["torus.nettemplate"]
        saved = load_document(path)
        assert isinstance(saved, TemplateDocument)
        assert ("#123456" in [face.color for face in saved.state.template.faces]) is (choice is SaveChoice.SAVE)
        if choice is SaveChoice.CANCEL:
            assert window.in_template_mode
            return
        assert not window.in_template_mode and window.project_path is None
        colors = window._project().settings.face_colors
        assert colors is not None and "#123456" in colors

    def test_create_network_without_unsaved_changes_asks_nothing(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window = self.make(qtbot, tmp_path)
        self.torus_template_in(window, tmp_path)
        self.validated(window, monkeypatch, save=True)  # (saved: no unsaved changes)
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: pytest.fail("asked"))
        window.create_network_button.button.click()
        assert not window.in_template_mode and len(window.editor.net.vertices) == 36

    def test_new_template_shows_the_template_sheet_and_its_instruments(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.new_template_action.trigger()
        assert window.in_template_mode
        assert window.stack.currentWidget() is window.template_mode.view
        assert window.windowTitle() == f"[*]Untitled — {APP_TITLE}"
        assert window.net_area.action.isVisible() and window.validate_action.isVisible()
        assert not window.ruler_action.isVisible() and not window.approve_action.isVisible()
        assert not window.bounding.action.isVisible()
        assert window.settings_panel.preferences.show_labels.isHidden()
        assert window.validate_action.shortcut().toString() == "V"
        self.draw(window)
        assert window.net_area.label.text() == "Net area\n2.000"
        assert window.is_dirty and window.undo_action.isEnabled()
        window.undo_action.trigger()
        assert window.net_area.label.text() == "Net area\n—"

    def test_saved_opened_and_back_to_a_project(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.core.project import load_document

        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)
        window = self.make(qtbot, tmp_path)
        window.new_template_action.trigger()
        self.draw(window)
        path = tmp_path / "pillow.nettemplate"
        assert window.save_template_to(path)
        assert not window.is_dirty and window.windowTitle() == f"[*]pillow.nettemplate — {APP_TITLE}"
        assert len(load_document(path).state.template.vertices) == 6  # type: ignore[union-attr]
        window.new_action.trigger()
        assert not window.in_template_mode and not window.net_area.action.isVisible()
        assert window.open_project_from(path)
        assert window.in_template_mode and not window.is_dirty
        assert window.template_mode.editor.state.value == "finalization"
        assert window.template_mode.editor.history.can_undo  # the history came along

    def test_leaving_an_unsaved_template_asks(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        asked: list[str] = []
        monkeypatch.setattr(
            "cube_net.ui.main_window.ask_save_changes", lambda _parent, name: asked.append(name) or SaveChoice.CANCEL
        )
        window = self.make(qtbot, tmp_path)
        window.new_template_action.trigger()
        self.draw(window)
        window.new_action.trigger()
        assert asked == ["Untitled"] and window.in_template_mode

    def test_validate(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.template.template_mode.tell", lambda _p, _t, text, **_: told.append(text))
        window = self.make(qtbot, tmp_path)
        window.new_template_action.trigger()
        assert not window.validate_action.isEnabled()  # the loop isn't closed
        self.draw(window)
        assert window.validate_action.isEnabled()
        window.validate_action.trigger()
        assert told == ["You have a face without a color. Double-click on the face to assign its color."]
        window.template_mode.tool.set_face_color(0, "#FFFFFF")
        window.validate_action.trigger()
        assert told[-1] == "Some vertices don't have assigned labels. Name each vertex."

    def test_the_validate_button(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cube_net.ui.template.template_mode.tell", lambda *_, **__: None)
        window = self.make(qtbot, tmp_path)
        button = window.validate_button.button
        assert not window.validate_button.action.isVisible()  # a project
        window.new_template_action.trigger()
        assert window.validate_button.action.isVisible() and window.draw_hole_button.separator.isVisible()
        assert window.draw_hole_button.action.isVisible() and window.draw_hole_action.shortcut().toString() == "H"
        assert not button.isEnabled() and button.text() == "Validate\ntemplate"  # the loop isn't closed
        self.draw(window)
        assert button.isEnabled()
        button.click()
        assert button.text() == "Invalid" and button.isEnabled()  # to see what's wrong again
        window.undo_action.trigger()
        window.redo_action.trigger()  # the same template: still Invalid
        assert button.text() == "Invalid"
        window.template_mode.tool.set_face_color(0, "#FFFFFF")
        assert button.text() == "Validate\ntemplate" and button.isEnabled()
        window.new_action.trigger()

    def test_recorded(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path, record=True)
        window.new_template_action.trigger()
        self.draw(window)
        assert window.recorder is not None
        lines = session_lines(window.recorder.log.path)
        assert "template new" in lines
        assert "template add 10.000,10.000" in lines and "template close 10.000,10.000" in lines
        assert any(line.startswith("state template untitled") for line in lines)
        window.stop_recording("test over")
