# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main window at start: the last project reopened, restored or repaired, and the last view."""

from pathlib import Path

import pytest
from PyQt6.QtCore import QPointF, QSettings
from pytestqt.qtbot import QtBot
from window_checks import session_lines, settings_in

from cube_net.core.body import CUBE
from cube_net.core.geometry import Vec
from cube_net.core.project import save_project
from cube_net.ui.app_settings import AppSettings
from cube_net.ui.dialogs.new_project_window import NewProjectChoice, Start, builtin_project
from cube_net.ui.main_window import (
    MainWindow,
)
from cube_net.ui.save_changes_dialog import SaveChoice
from cube_net.ui.sheet.view_place import ViewPlace


class TestReopeningAtStart:
    def make(self, qtbot: QtBot, tmp_path: Path, record: bool = False) -> MainWindow:
        """A window as after a restart: the settings are in the same place, the project is the new one for now."""
        settings = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
        settings.record_session = record
        window = MainWindow(settings=settings, session_dir=tmp_path, empty=True)  # as the application starts
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def worked_on(self, qtbot: QtBot, tmp_path: Path, name: str = "cube.cubenet") -> Path:
        """A session that ended with this file saved: a closed line in it."""
        from cube_net.ui.sheet import net_style

        window = self.make(qtbot, tmp_path)
        h = net_style.CUT_HITBOX_PX / 2 / window.sheet_view.scale_factor()
        view = window.sheet_view
        view.left_pressed.emit(11.5, 14 - h)
        view.left_pressed.emit(11.5, 13.5)
        view.left_pressed.emit(12 - h, 13.5)
        path = tmp_path / name
        assert window.save_project_to(path)
        return path

    def answers(self, monkeypatch: pytest.MonkeyPatch, *choices: object) -> list[str]:
        """Make the question answer this; returns what it was told."""
        remaining = list(choices)
        told: list[str] = []

        def ask(_parent: object, message: str) -> object:
            told.append(message)
            return remaining.pop(0)

        monkeypatch.setattr("cube_net.ui.main_window.ask_after_load_failed", ask)
        return told

    def test_the_first_time_file_new_s_window(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        told = self.answers(monkeypatch)
        shown: list[bool] = []

        def choose(window: MainWindow, *_: object) -> NewProjectChoice:
            shown.append(window.nothing_open)  # over the grey area, not a project
            return NewProjectChoice(Start.CUBE_WITH_A_HOLE, None, builtin_project(Start.CUBE_WITH_A_HOLE))

        monkeypatch.setattr("cube_net.ui.main_window.choose_new_project", choose)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert told == [] and shown == [True]
        assert not window.nothing_open and window.net.body is not CUBE
        assert window.project_path is None
        assert not window.is_dirty

    def test_the_first_time_given_up_nothing_is_open(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("cube_net.ui.main_window.choose_new_project", lambda *_: None)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.nothing_open
        window.new_action.trigger()  # still there
        assert window.nothing_open

    def test_back_to_what_was_saved(self, qtbot: QtBot, tmp_path: Path) -> None:
        path = self.worked_on(qtbot, tmp_path)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == path
        assert window.windowTitle().startswith("[*]cube.cubenet")
        assert window.editor.state.value == "cut_editing"
        assert not window.is_dirty
        window.undo_action.trigger()
        assert window.editor.state.value == "cutting"

    def test_a_window_alone_opens_nothing(self, qtbot: QtBot, tmp_path: Path) -> None:
        self.worked_on(qtbot, tmp_path)
        window = self.make(qtbot, tmp_path)
        assert window.nothing_open

    def test_the_last_one_saved_wins(self, qtbot: QtBot, tmp_path: Path) -> None:
        self.worked_on(qtbot, tmp_path, "a.cubenet")
        b = self.worked_on(qtbot, tmp_path, "b.cubenet")
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == b

    def test_the_last_one_opened_counts_too(self, qtbot: QtBot, tmp_path: Path) -> None:
        a = self.worked_on(qtbot, tmp_path, "a.cubenet")
        self.worked_on(qtbot, tmp_path, "b.cubenet")
        self.make(qtbot, tmp_path).open_project_from(a)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == a

    def test_a_new_project_changes_nothing_until_it_is_saved(self, qtbot: QtBot, tmp_path: Path) -> None:
        path = self.worked_on(qtbot, tmp_path)
        self.make(qtbot, tmp_path).start_new_project()
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == path

    def test_a_file_that_failed_to_open_is_not_remembered(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        path = self.worked_on(qtbot, tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda *_, **__: None)
        window = self.make(qtbot, tmp_path)
        assert not window.open_project_from(tmp_path / "missing.cubenet")
        assert window.settings.last_project == path

    def test_a_failed_save_is_not_remembered(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        path = self.worked_on(qtbot, tmp_path)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda *_, **__: None)
        window = self.make(qtbot, tmp_path)
        assert not window.save_project_to(tmp_path / "nowhere" / "cube.cubenet")
        assert window.settings.last_project == path

    def test_it_is_gone_the_user_is_told_and_gets_a_new_project(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        path = self.worked_on(qtbot, tmp_path)
        path.unlink()
        told = self.answers(monkeypatch, AfterLoadFailed.NEW_PROJECT)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert len(told) == 1 and "cube.cubenet" in told[0]
        assert window.editor.state.value == "default"  # the Cube, chosen in File -> New's window
        assert not window.nothing_open and window.project_path is None
        assert not window.is_dirty

    def test_it_is_gone_and_no_new_project_is_chosen(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        self.worked_on(qtbot, tmp_path).unlink()
        shown: list[bool] = []

        def ask(window: MainWindow, _message: str) -> AfterLoadFailed:
            shown.append(window.nothing_open)  # no net behind the message
            return AfterLoadFailed.NEW_PROJECT

        monkeypatch.setattr("cube_net.ui.main_window.ask_after_load_failed", ask)
        monkeypatch.setattr("cube_net.ui.main_window.choose_new_project", lambda *_: None)
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert shown == [True] and window.nothing_open

    def test_it_is_damaged_the_user_is_told_why(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        path = self.worked_on(qtbot, tmp_path)
        path.write_text("Hello!")
        told = self.answers(monkeypatch, AfterLoadFailed.NEW_PROJECT)
        self.make(qtbot, tmp_path).reopen_last_project()
        assert "isn't a Cube Net project" in told[0]

    def test_it_is_asked_only_once(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        self.worked_on(qtbot, tmp_path).unlink()
        told = self.answers(monkeypatch, AfterLoadFailed.NEW_PROJECT)
        self.make(qtbot, tmp_path).reopen_last_project()
        self.make(qtbot, tmp_path).reopen_last_project()
        assert len(told) == 1

    def test_open_another_instead(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from PyQt6.QtWidgets import QFileDialog

        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        other = self.worked_on(qtbot, tmp_path, "other.cubenet")
        self.worked_on(qtbot, tmp_path).unlink()
        self.answers(monkeypatch, AfterLoadFailed.OPEN_ANOTHER)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(other), ""))
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert window.project_path == other
        assert window.editor.state.value == "cut_editing"
        assert window.settings.last_project == other

    def test_open_another_dialog_cancelled_leaves_a_new_project(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PyQt6.QtWidgets import QFileDialog

        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        self.worked_on(qtbot, tmp_path).unlink()
        told = self.answers(monkeypatch, AfterLoadFailed.OPEN_ANOTHER)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: ("", ""))
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert len(told) == 1
        assert window.project_path is None
        assert window.settings.last_project is None

    def test_the_other_one_fails_too_asks_again_with_the_new_reason(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from PyQt6.QtWidgets import QFileDialog

        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        self.worked_on(qtbot, tmp_path).unlink()
        bad = tmp_path / "bad.cubenet"
        bad.write_text("Hello!")
        told = self.answers(monkeypatch, AfterLoadFailed.OPEN_ANOTHER, AfterLoadFailed.NEW_PROJECT)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(bad), ""))
        window = self.make(qtbot, tmp_path)
        window.reopen_last_project()
        assert len(told) == 2
        assert "cube.cubenet" in told[0] and "bad.cubenet" in told[1]
        assert window.project_path is None

    def test_recorded(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.ui.load_failed_dialog import AfterLoadFailed

        path = self.worked_on(qtbot, tmp_path)
        window = self.make(qtbot, tmp_path, record=True)
        window.reopen_last_project()
        assert window.recorder is not None
        assert f"project opened {path}" in session_lines(window.recorder.log.path)
        window.stop_recording("test over")
        path.unlink()
        self.answers(monkeypatch, AfterLoadFailed.NEW_PROJECT)
        other = self.make(qtbot, tmp_path, record=True)
        other.settings.last_project = path
        other.reopen_last_project()
        assert other.recorder is not None
        assert f"project reopening failed {path}" in session_lines(other.recorder.log.path)
        other.stop_recording("test over")


class TestRestoring:
    """A file that can't be opened, but has actions to undo: the user may restore its last state that opens."""

    def damaged(self, tmp_path: Path) -> Path:
        import json

        from cube_net.core.project import TemplateDocument, encode_template
        from cube_net.core.project.file import _to_bytes
        from cube_net.core.template import Template, TemplateEditor

        template = Template()
        for x, y in [(10, 10), (11, 10), (12, 10), (12, 11), (11, 11), (10, 11)]:
            template = template.with_vertex_appended(Vec(x, y))
        editor = TemplateEditor(template.closed_loop())
        assert editor.add_fold(1, 4) is None
        data = json.loads(json.dumps(encode_template(TemplateDocument(editor.snapshot(), editor.history))))
        data["templates"][data["states"][data["state"]]["template"]]["faces"].pop()  # a side on no face
        path = tmp_path / "damaged.nettemplate"
        path.write_bytes(_to_bytes(data))
        return path

    def window(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        return window

    def test_restored_with_unsaved_changes(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        asked: list[str] = []
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.ask_yes_no", lambda _p, text: asked.append(text) or True)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _p, _t, text, **_: told.append(text))
        path = self.damaged(tmp_path)
        before = path.read_bytes()
        window = self.window(qtbot, tmp_path)
        assert window.open_project_from(path)
        assert len(asked) == 1 and asked[0].endswith("Try to restore the last valid state?") and "damaged" in asked[0]
        assert told == ["State 1 action ago was restored."]
        assert window.in_template_mode and window.is_dirty and window.template_mode.path == path
        assert path.read_bytes() == before  # not saved by itself

    def test_declined(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.ask_yes_no", lambda *_: False)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _p, _t, text, **_: told.append(text))
        window = self.window(qtbot, tmp_path)
        assert not window.open_project_from(self.damaged(tmp_path))
        assert told == []  # the question said it all

    def test_nothing_to_restore_from(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        asked: list[str] = []
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.ask_yes_no", lambda _p, text: asked.append(text) or True)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _p, _t, text, **_: told.append(text))
        path = tmp_path / "junk.cubenet"
        path.write_bytes(b"not a project")
        window = self.window(qtbot, tmp_path)
        assert not window.open_project_from(path)
        assert asked == [] and len(told) == 1  # the old message only

    def test_unable_to_restore(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        asked: list[str] = []
        opened: list[bool] = []
        monkeypatch.setattr("cube_net.ui.main_window.ask_yes_no", lambda _p, text: asked.append(text) or True)
        monkeypatch.setattr("cube_net.ui.main_window.restore_document", lambda _path: None)
        window = self.window(qtbot, tmp_path)
        monkeypatch.setattr(window, "_on_open", lambda: opened.append(True))
        assert not window.open_project_from(self.damaged(tmp_path))
        assert asked[-1] == "Unable to restore the file. Open another?" and opened == [True]


class TestTooLongNumbers:
    def test_a_refusal_is_told_in_a_warning(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fractions import Fraction

        from cube_net.core.geometry import MAX_NUMBER_DIGITS, Vec
        from cube_net.core.origin import Origin

        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _p, _t, text, **_: told.append(text))
        long = Vec(Fraction(1, 10**MAX_NUMBER_DIGITS), 0)
        window.cut_tool.move_origin(Origin(long, long))
        assert len(told) == 1 and told[0].startswith("Your action was rejected.<br>") and "the origin" in told[0]
        assert window.editor.origin == Origin()


class TestRepairingLongNumbers:
    """Opening a project with numbers too long: the user is asked, and it's repaired (or not opened)."""

    def saved_long_project(self, tmp_path: Path) -> Path:
        from tests.core.project.test_repair import THIRD, long_project

        from cube_net.core.project import save_project
        from cube_net.core.project.file import any_length

        path = tmp_path / "long.cubenet"
        with any_length():
            save_project(long_project(11 + THIRD), path)
        return path

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path)
        qtbot.addWidget(window)
        return window

    def test_repaired_when_the_user_wants(self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cube_net.core.project.repair import needs_repair

        path = self.saved_long_project(tmp_path)
        window = self.make(qtbot, tmp_path)
        asked: list[str] = []
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.ask_yes_no", lambda _p, text, *_: asked.append(text) or True)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _p, _t, text, **_: told.append(text))
        assert window.open_project_from(path)
        assert len(asked) == 1 and asked[0].startswith("Unable to open the file.<br>This version of the application")
        assert "Caution: this will wipe out undo/redo history" in asked[0]
        assert len(told) == 1 and told[0].startswith("Automatic repairment completed.<br>Vertices ")
        assert not needs_repair(window._project()) and window.is_dirty  # not saved by itself

    def test_not_opened_when_the_user_doesnt(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = self.saved_long_project(tmp_path)
        window = self.make(qtbot, tmp_path)
        before = window.editor.net
        monkeypatch.setattr("cube_net.ui.main_window.ask_yes_no", lambda *_: False)
        assert not window.open_project_from(path)
        assert window.editor.net is before and window.project_path is None

    def test_not_opened_when_the_repair_fails(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cube_net.core.project.repair import RepairError

        path = self.saved_long_project(tmp_path)
        window = self.make(qtbot, tmp_path)
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.ask_yes_no", lambda *_: True)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _p, _t, text, **_: told.append(text))

        def failing(_project: object) -> object:
            raise RepairError("a bug")

        monkeypatch.setattr("cube_net.ui.main_window.repair_project", failing)
        assert not window.open_project_from(path)
        assert told == ["Unexpected error during project repairment."] and window.project_path is None

    def test_a_template_repaired_when_the_user_wants(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from tests.core.project.test_template_repair import HAIR, edited

        from cube_net.core.geometry import Vec
        from cube_net.core.project import save_template
        from cube_net.core.project.builtin_templates import cube_with_a_hole

        corner = cube_with_a_hole().state.template.vertices[0]
        path = tmp_path / "long.nettemplate"
        save_template(edited({corner.id: Vec(HAIR, 0)}), path)
        window = self.make(qtbot, tmp_path)
        asked: list[str] = []
        told: list[str] = []
        monkeypatch.setattr("cube_net.ui.main_window.ask_yes_no", lambda _p, text, *_: asked.append(text) or True)
        monkeypatch.setattr("cube_net.ui.main_window.tell", lambda _p, _t, text, **_: told.append(text))
        assert window.open_project_from(path)
        assert len(asked) == 1 and asked[0].endswith(
            'move "bad" vertices in closest appropriate positions? Caution: this will wipe out undo/redo history.'
        )
        assert "body edges" not in asked[0] and str(corner.label)[0] in asked[0]
        assert told and told[0].startswith("Automatic repairment completed.")
        assert window.in_template_mode and window.template_mode.is_dirty
        assert window.template_mode.editor.template == cube_with_a_hole().state.template


class TestLastView:
    """Closing the app and starting it again shows the file reopened where the view was, zoomed as it was."""

    def make(self, qtbot: QtBot, tmp_path: Path) -> MainWindow:
        window = MainWindow(settings=settings_in(tmp_path, record=False), session_dir=tmp_path, empty=True)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)
        return window

    def moved(self, window: MainWindow) -> ViewPlace:
        view = window.template_mode.view if window.in_template_mode else window.sheet_view
        view.zoom_by(1.7, QPointF(120, 90))
        view.pan_by(53, -31)
        return view.place()

    def reopened(self, qtbot: QtBot, tmp_path: Path, window: MainWindow) -> MainWindow:
        window.close()
        again = self.make(qtbot, tmp_path)
        again.reopen_last_project()
        return again

    def near(self, a: ViewPlace, b: ViewPlace) -> bool:
        return a.scale == b.scale and abs(a.x - b.x) < 1 / a.scale and abs(a.y - b.y) < 1 / a.scale

    def test_a_project(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.start_new_project()
        assert window.save_project_to(tmp_path / "cube.cubenet")
        place = self.moved(window)
        again = self.reopened(qtbot, tmp_path, window)
        assert self.near(again.sheet_view.place(), place)

    def test_a_template(self, qtbot: QtBot, tmp_path: Path) -> None:
        from cube_net.core.project import save_template
        from cube_net.core.project.builtin_templates import cube_with_a_hole

        path = tmp_path / "torus.nettemplate"
        save_template(cube_with_a_hole(), path)
        window = self.make(qtbot, tmp_path)
        assert window.open_project_from(path)
        place = self.moved(window)
        again = self.reopened(qtbot, tmp_path, window)
        assert again.in_template_mode and self.near(again.template_mode.view.place(), place)

    def test_another_file_opened_is_shown_as_always(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.start_new_project()
        assert window.save_project_to(tmp_path / "cube.cubenet")
        first = window.sheet_view.place()
        self.moved(window)
        window.close()
        other = tmp_path / "other.cubenet"
        save_project(builtin_project(Start.CUBE), other)
        window.settings.last_project = other  # (opened by another way since: the view kept isn't its)
        again = self.make(qtbot, tmp_path)
        again.reopen_last_project()
        assert self.near(again.sheet_view.place(), first)

    def test_nothing_kept_for_an_untitled_project(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)
        window = self.make(qtbot, tmp_path)
        window.start_new_project()
        self.moved(window)
        window.close()
        assert window.settings.last_view is None

    def test_the_window_size_too(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        window.resize(733, 517)
        qtbot.waitUntil(lambda: window.size().width() == 733)
        window.close()
        again = self.make(qtbot, tmp_path)
        assert (again.width(), again.height()) == (733, 517)

    def test_the_first_start_fills_most_of_the_screen(self, qtbot: QtBot, tmp_path: Path) -> None:
        window = self.make(qtbot, tmp_path)
        screen = window.screen()
        assert screen is not None
        assert window.width() == int(screen.availableGeometry().width() * 0.8)
