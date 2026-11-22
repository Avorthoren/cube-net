# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

import pytest
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from cube_net.core.body import CUBE
from cube_net.core.history import History
from cube_net.core.net import validate_net
from cube_net.core.project import TemplateDocument, save_project, save_template
from cube_net.core.project.builtin_templates import cube_with_a_hole
from cube_net.core.template import TemplateEditor, TemplateSnapshot
from cube_net.ui.dialogs.new_project_window import NewProjectWindow, Start, builtin_project
from cube_net.ui.style import DEFAULT_STYLE

MODULE = "cube_net.ui.dialogs.new_project_window"


def make(qtbot: QtBot) -> NewProjectWindow:
    window = NewProjectWindow("Cube Net templates (*.nettemplate)")
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def choose(window: NewProjectWindow, start: Start, path: Path | None = None) -> None:
    window.start.setCurrentIndex(window.start.findData(start))
    if path is not None:
        window.file.setText(str(path))
    window.create_button.click()


def test_the_cube_is_chosen_at_first_and_the_file_is_only_for_custom(qtbot: QtBot) -> None:
    window = make(qtbot)
    assert window.selected() is Start.CUBE
    assert [window.start.itemText(i) for i in range(3)] == ["Cube", "Cube with a hole", "Custom template"]
    size = window.size()
    assert not window.file_line.isVisible()
    window.start.setCurrentIndex(window.start.findData(Start.CUSTOM))
    assert window.file_line.isVisible() and window.file.isVisible() and window.browse.isVisible()
    window.start.setCurrentIndex(window.start.findData(Start.CUBE_WITH_A_HOLE))
    assert not window.file_line.isVisible()
    assert window.size() == size  # the line's room stays


def test_the_lines_are_centred(qtbot: QtBot) -> None:
    window = make(qtbot)
    window.start.setCurrentIndex(window.start.findData(Start.CUSTOM))
    middle = window.width() / 2

    def centre(*widgets: QWidget) -> float:
        left = min(w.mapTo(window, QPoint(0, 0)).x() for w in widgets)
        right = max(w.mapTo(window, QPoint(w.width(), 0)).x() for w in widgets)
        return (left + right) / 2

    assert abs(centre(window.start) - middle) <= 2
    assert abs(centre(window.file, window.browse) - middle) <= 2
    assert abs(centre(window.cancel_button, window.create_button) - middle) <= 2
    assert window.start.width() < window.file.width()  # no wider than its options need


def test_cube(qtbot: QtBot) -> None:
    window = make(qtbot)
    choose(window, Start.CUBE)
    choice = window.choice()
    assert choice is not None and choice.start is Start.CUBE and choice.path is None and choice.template is None
    assert choice.project is not None and choice.project.state.net.body is CUBE
    assert choice.project.settings.style == DEFAULT_STYLE
    assert not window.isVisible()


def test_cube_with_a_hole(qtbot: QtBot) -> None:
    window = make(qtbot)
    choose(window, Start.CUBE_WITH_A_HOLE)
    choice = window.choice()
    assert choice is not None and choice.project is not None
    validate_net(choice.project.state.net)
    assert choice.project.settings.style == cube_with_a_hole().style
    assert choice.project.state.origin == cube_with_a_hole().state.origin


def test_builtin_project_of_the_cube_has_the_style_files_style() -> None:
    assert builtin_project(Start.CUBE).settings.style == DEFAULT_STYLE


def test_a_valid_custom_template(qtbot: QtBot, tmp_path: Path) -> None:
    path = tmp_path / "torus.nettemplate"
    save_template(cube_with_a_hole(), path)
    window = make(qtbot)
    choose(window, Start.CUSTOM, path)
    choice = window.choice()
    assert choice is not None and choice.path == path and choice.project is not None and choice.template is None
    validate_net(choice.project.state.net)
    assert choice.project.settings.style == cube_with_a_hole().style


def test_no_file_yet(qtbot: QtBot) -> None:
    window = make(qtbot)
    choose(window, Start.CUSTOM)
    assert window.choice() is None and window.isVisible()


@pytest.mark.parametrize("kind", ["missing", "project"])
def test_a_file_that_is_no_template_is_said_so(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    told: list[str] = []
    monkeypatch.setattr(f"{MODULE}.tell", lambda _p, _t, text, **_: told.append(text))
    path = tmp_path / "x.cubenet"
    if kind == "project":
        save_project(builtin_project(Start.CUBE), path)
    window = make(qtbot)
    choose(window, Start.CUSTOM, path)
    assert window.choice() is None and window.isVisible()
    assert len(told) == 1
    if kind == "project":
        assert told == [f"{path} is a project, not a template."]


@pytest.mark.parametrize("answer", [True, False])
def test_a_template_that_is_not_valid(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: bool
) -> None:
    asked: list[str] = []
    monkeypatch.setattr(f"{MODULE}.ask_yes_no", lambda _p, text: asked.append(text) or answer)
    path = tmp_path / "empty.nettemplate"
    save_template(TemplateDocument(TemplateSnapshot(TemplateEditor().template), History()), path)
    window = make(qtbot)
    choose(window, Start.CUSTOM, path)
    assert asked == ["Template is not valid. Open template?"]
    choice = window.choice()
    if answer:
        assert choice is not None and choice.project is None and choice.template is not None and choice.path == path
        assert not window.isVisible()
    else:
        assert choice is None and window.isVisible()  # back to the window


def test_a_template_that_is_not_valid_and_open_already(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing to open: the window only says it's not valid, and stays."""
    asked: list[str] = []
    told: list[str] = []
    monkeypatch.setattr(f"{MODULE}.ask_yes_no", lambda _p, text: asked.append(text) or True)
    monkeypatch.setattr(f"{MODULE}.tell", lambda _p, _t, text, **_: told.append(text))
    path = tmp_path / "empty.nettemplate"
    save_template(TemplateDocument(TemplateSnapshot(TemplateEditor().template), History()), path)
    window = NewProjectWindow("Cube Net templates (*.nettemplate)", open_template=tmp_path / "." / "empty.nettemplate")
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    choose(window, Start.CUSTOM, path)
    assert told == ["Template is not valid."] and asked == []
    assert window.choice() is None and window.isVisible()


def test_cancel(qtbot: QtBot) -> None:
    window = make(qtbot)
    window.cancel_button.click()
    assert window.choice() is None and not window.isVisible()
