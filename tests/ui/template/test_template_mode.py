# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Vec
from cube_net.core.project import load_document
from cube_net.core.template import Label, TemplateState
from cube_net.ui.style import DEFAULT_STYLE
from cube_net.ui.template.template_mode import TemplateMode

# A cross (the cube's net), its labels, and its folds (docs/idea.txt).
CROSS = [
    (11, 10, "A", 3), (12, 10, "B", 3), (12, 11, "F", 1), (12, 12, "G", 1), (13, 12, "F", 2), (13, 13, "B", 2),
    (12, 13, "D", 1), (12, 14, "B", 1), (11, 14, "A", 1), (11, 13, "C", 1), (10, 13, "A", 2), (10, 12, "E", 2),
    (11, 12, "H", 1), (11, 11, "E", 1),
]  # fmt: skip
FOLDS = [("C1", "D1"), ("H1", "G1"), ("E1", "F1"), ("C1", "H1"), ("D1", "G1")]


@pytest.fixture
def mode(qtbot: QtBot) -> TemplateMode:
    parent = QWidget()
    qtbot.addWidget(parent)
    mode = TemplateMode(parent, lambda *_: None)
    for x, y, *_ in [*CROSS, CROSS[0]]:
        assert mode.editor.add_point(Vec(x, y)) is None
    ids = {v.position: v.id for v in mode.editor.template.vertices}
    for x, y, name, index in CROSS:
        mode.editor.set_label(ids[Vec(x, y)], Label(name, index))
    labels = {str(v.label): v.id for v in mode.editor.template.vertices}
    for a, b in FOLDS:
        assert mode.editor.add_fold(labels[a], labels[b]) is None
    for index in range(len(mode.editor.template.faces)):
        mode.editor.set_face_color(index, f"#0000{index:02X}")
    mode.tool.refresh()
    return mode


def told(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    texts: list[str] = []
    monkeypatch.setattr("cube_net.ui.template.template_mode.tell", lambda _p, _t, text, **_: texts.append(text))
    return texts


def test_no_problems(mode: TemplateMode, monkeypatch: pytest.MonkeyPatch) -> None:
    texts = told(monkeypatch)
    mode.validate()
    assert texts == ["No problems found."]


@pytest.mark.parametrize(
    ("loaded", "text"),
    [
        (1, "You have a face without a color. Double-click on the face to assign its color."),
        (2, "You have faces without a color. Double-click on a face to assign its color."),
    ],
)
def test_faces_without_a_colour(mode: TemplateMode, monkeypatch: pytest.MonkeyPatch, loaded: int, text: str) -> None:
    from dataclasses import replace as changed

    from cube_net.core.history import History
    from cube_net.core.template import TemplateSnapshot

    template = mode.editor.template
    faces = tuple(changed(face, color=None) if i < loaded else face for i, face in enumerate(template.faces))
    mode.editor.load(TemplateSnapshot(changed(template, faces=faces)), History())
    texts = told(monkeypatch)
    mode.validate()
    assert texts == [text]


@pytest.mark.parametrize("answer", [True, False])
def test_gaps_in_indices(mode: TemplateMode, monkeypatch: pytest.MonkeyPatch, answer: bool) -> None:
    a3 = next(v.id for v in mode.editor.template.vertices if str(v.label) == "A3")
    mode.editor.set_label(a3, Label("A", 7))
    texts = told(monkeypatch)
    asked: list[str] = []
    monkeypatch.setattr("cube_net.ui.template.template_mode.ask_yes_no", lambda _p, text: asked.append(text) or answer)
    mode.validate()
    assert asked == ["Indices for vertex A have gaps. Reindex automatically?"]
    if answer:
        assert texts == ["Vertices automatically reindexed.\nNo other problems found."]
        assert str(mode.editor.template.vertex(a3).label) == "A3"
    else:
        assert texts == [] and str(mode.editor.template.vertex(a3).label) == "A7"


# A style, not the default one.
STYLE = replace(DEFAULT_STYLE, hatch_rows=7)


def test_save_and_show_again(mode: TemplateMode, tmp_path: Path, qtbot: QtBot) -> None:
    path = tmp_path / "cross.nettemplate"
    mode.set_style(STYLE)
    assert mode.is_dirty
    mode.save_to(path)
    assert mode.path == path and not mode.is_dirty
    document = load_document(path)
    assert document.style == STYLE  # type: ignore[union-attr]
    mode.show(None, None, DEFAULT_STYLE)
    assert mode.editor.state is TemplateState.INITIAL and mode.area() is None and mode.style == DEFAULT_STYLE
    mode.show(document, path, STYLE)  # type: ignore[arg-type]
    assert mode.area() == 6 and mode.style == STYLE and not mode.is_dirty
