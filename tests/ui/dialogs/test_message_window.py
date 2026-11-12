# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QPushButton
from pytestqt.qtbot import QtBot

from cube_net.ui.dialogs.message_window import MessageIcon, MessageWindow, tell

BUTTONS = QDialogButtonBox.StandardButton


class Question:
    """A window with Save, Don't save and Cancel: Save is the default one, Cancel the escape one."""

    def __init__(self, qtbot: QtBot) -> None:
        self.window = MessageWindow("Title", "Save the changes?", "They're lost otherwise.", MessageIcon.WARNING)
        qtbot.addWidget(self.window)
        self.save = self.window.add_standard(BUTTONS.Save)
        self.discard = self.window.add_standard(BUTTONS.Discard, "Don't save")
        self.cancel = self.window.add_standard(BUTTONS.Cancel)
        self.window.set_default(self.save)
        self.window.set_escape(self.cancel)
        self.window.show()
        qtbot.waitUntil(lambda: QApplication.focusWidget() is self.save)


@pytest.fixture
def question(qtbot: QtBot) -> Question:
    return Question(qtbot)


def test_what_it_shows(question: Question) -> None:
    window = question.window
    assert window.text() == "Save the changes?"
    assert window.informativeText() == "They're lost otherwise."
    assert window.button(BUTTONS.Discard) is question.discard
    assert question.discard.text() == "Don't save"
    assert window.defaultButton() is question.save
    assert window.escape_button() is question.cancel


def test_only_a_close_button_in_the_title_bar(question: Question) -> None:
    flags = question.window.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint  # no minimize or maximize from the window manager
    assert question.window.title_bar.close_button.isVisible()


def test_tab_goes_through_the_buttons(qtbot: QtBot, question: Question) -> None:
    seen: list[QPushButton] = []
    for _ in range(len(question.window.buttons())):
        focused = QApplication.focusWidget()
        assert isinstance(focused, QPushButton)
        seen.append(focused)
        qtbot.keyClick(focused, Qt.Key.Key_Tab)
    assert set(seen) == {question.save, question.discard, question.cancel}
    assert QApplication.focusWidget() is question.save  # and round again


@pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space])
def test_enter_and_space_press_the_default_button(qtbot: QtBot, question: Question, key: Qt.Key) -> None:
    qtbot.keyClick(question.save, key)
    qtbot.waitUntil(lambda: question.window.clicked() is not None)
    assert question.window.clicked() is question.save


@pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Space])
def test_enter_and_space_press_the_button_tab_went_to(qtbot: QtBot, question: Question, key: Qt.Key) -> None:
    question.discard.setFocus()
    qtbot.waitUntil(lambda: QApplication.focusWidget() is question.discard)
    qtbot.keyClick(question.discard, key)
    qtbot.waitUntil(lambda: question.window.clicked() is not None)
    assert question.window.clicked() is question.discard


def test_escape_chooses_the_escape_button(qtbot: QtBot, question: Question) -> None:
    qtbot.keyClick(question.save, Qt.Key.Key_Escape)
    assert question.window.clicked() is question.cancel
    assert not question.window.isVisible()


def test_the_close_button_chooses_the_escape_button(question: Question) -> None:
    question.window.title_bar.close_button.click()
    assert question.window.clicked() is question.cancel
    assert not question.window.isVisible()


def test_ask_returns_the_button_clicked(qtbot: QtBot) -> None:
    window = MessageWindow("Title", "Sure?")
    yes = window.add_standard(BUTTONS.Yes)
    no = window.add_standard(BUTTONS.No)
    window.set_default(no)
    window.set_escape(no)
    QTimer.singleShot(0, yes.click)
    assert window.ask() is yes


def answering(act: Callable[[MessageWindow], None]) -> None:
    def answer() -> None:
        window = QApplication.activeModalWidget()
        assert isinstance(window, MessageWindow)
        act(window)

    QTimer.singleShot(0, answer)


@pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Space, Qt.Key.Key_Escape])
def test_a_message_has_only_ok_and_every_key_closes_it(qtbot: QtBot, key: Qt.Key) -> None:
    seen: list[list[str]] = []

    def press(window: MessageWindow) -> None:
        seen.append([button.text().replace("&", "") for button in window.buttons()])
        ok = window.defaultButton()
        assert ok is not None
        assert ok is window.escape_button()
        qtbot.waitUntil(lambda: QApplication.focusWidget() is ok)
        qtbot.keyClick(ok, key)

    answering(press)
    tell(None, "Title", "Done.")
    assert seen == [["OK"]]
