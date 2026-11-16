# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from pytestqt.qtbot import QtBot

from cube_net.core.template import Label
from cube_net.ui.template.assign_vertex_window import AssignVertexWindow

TAKEN = {Label("A", 1), Label("A", 2)}


def make(qtbot: QtBot, label: Label | None = None) -> AssignVertexWindow:
    window = AssignVertexWindow(label, TAKEN.__contains__, lambda name: 3 if name == "A" else 1)
    qtbot.addWidget(window)
    return window


def test_a_vertex_without_a_label(qtbot: QtBot) -> None:
    window = make(qtbot)
    assert (window.name.text(), window.index.value()) == ("", 1)
    assert window.typed() is None


def test_a_label_to_change(qtbot: QtBot) -> None:
    window = make(qtbot, Label("CT", 12))
    assert (window.name.text(), window.index.value()) == ("CT", 12)


def test_capital_latin_letters_only(qtbot: QtBot) -> None:
    window = make(qtbot)
    qtbot.keyClicks(window.name, "q1-zx")
    assert window.name.text() == "QZ"


def test_assign(qtbot: QtBot) -> None:
    window = make(qtbot)
    qtbot.keyClicks(window.name, "b")
    window.index.setValue(7)
    window.assign_button.click()
    assert window.result() == AssignVertexWindow.DialogCode.Accepted
    assert window.label() == Label("B", 7)


def test_no_name_no_label(qtbot: QtBot) -> None:
    window = make(qtbot, Label("B", 1))
    window.name.clear()
    window.assign_button.click()
    assert window.result() == AssignVertexWindow.DialogCode.Accepted and window.label() is None


@pytest.mark.parametrize(("answer", "label"), [(True, Label("A", 3)), (False, None)])
def test_a_label_taken(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, answer: bool, label: Label | None) -> None:
    asked = []
    monkeypatch.setattr(
        "cube_net.ui.template.assign_vertex_window.ask_yes_no", lambda _parent, text: asked.append(text) or answer
    )
    window = make(qtbot)
    qtbot.keyClicks(window.name, "a")
    window.index.setValue(2)
    window.assign_button.click()
    assert asked == ["Such label already exists. Assign first free index?"]
    if answer:
        assert window.result() == AssignVertexWindow.DialogCode.Accepted and window.label() == label
    else:
        assert window.result() != AssignVertexWindow.DialogCode.Accepted  # still open: back to the fields
