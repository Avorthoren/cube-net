# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from cube_net.ui.save_changes_dialog import SaveChoice, ask_save_changes


def answering(act: Callable[[QMessageBox], None]) -> None:
    """Once the question is up, do this to it."""

    def answer() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, QMessageBox)
        act(box)

    QTimer.singleShot(0, answer)


def clicking(button: QMessageBox.StandardButton) -> Callable[[QMessageBox], None]:
    def click(box: QMessageBox) -> None:
        found = box.button(button)
        assert found is not None
        found.click()

    return click


@pytest.mark.parametrize(
    ("button", "choice"),
    [
        (QMessageBox.StandardButton.Save, SaveChoice.SAVE),
        (QMessageBox.StandardButton.Discard, SaveChoice.DISCARD),
        (QMessageBox.StandardButton.Cancel, SaveChoice.CANCEL),
    ],
)
def test_the_answers(qtbot: QtBot, button: QMessageBox.StandardButton, choice: SaveChoice) -> None:
    answering(clicking(button))
    assert ask_save_changes(None, "cube.cubenet") is choice


def test_closing_the_question_means_cancel(qtbot: QtBot) -> None:
    answering(lambda box: box.close())
    assert ask_save_changes(None, "cube.cubenet") is SaveChoice.CANCEL


def test_escape_means_cancel(qtbot: QtBot) -> None:
    answering(lambda box: qtbot.keyClick(box, Qt.Key.Key_Escape))
    assert ask_save_changes(None, "cube.cubenet") is SaveChoice.CANCEL


def test_what_it_says(qtbot: QtBot) -> None:
    seen: dict[str, object] = {}

    def look(box: QMessageBox) -> None:
        discard = box.button(QMessageBox.StandardButton.Discard)
        assert discard is not None
        seen.update(text=box.text(), discard=discard.text(), default=box.defaultButton())
        clicking(QMessageBox.StandardButton.Cancel)(box)

    answering(look)
    ask_save_changes(None, "cube.cubenet")
    assert "cube.cubenet" in str(seen["text"])
    assert seen["discard"] == "Don't save"
    assert seen["default"] is not None


def test_it_does_not_stay_behind(qtbot: QtBot) -> None:
    from PyQt6.QtCore import QCoreApplication, QEvent
    from PyQt6.QtWidgets import QWidget

    parent = QWidget()
    qtbot.addWidget(parent)
    answering(clicking(QMessageBox.StandardButton.Cancel))
    ask_save_changes(parent, "cube.cubenet")
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert parent.findChildren(QMessageBox) == []
