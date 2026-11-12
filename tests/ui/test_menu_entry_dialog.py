# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QDialogButtonBox
from pytestqt.qtbot import QtBot

from cube_net.ui.dialogs.message_window import MessageWindow
from cube_net.ui.menu_entry_dialog import ask_menu_entry


def answer(button: QDialogButtonBox.StandardButton) -> None:
    """Click `button` of the question as soon as it's shown."""

    def click() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, MessageWindow)
        clicked = box.button(button)
        assert clicked is not None
        clicked.click()

    QTimer.singleShot(0, click)


@pytest.mark.parametrize(
    ("button", "wanted"), [(QDialogButtonBox.StandardButton.Yes, True), (QDialogButtonBox.StandardButton.No, False)]
)
def test_yes_or_no(qtbot: QtBot, button: QDialogButtonBox.StandardButton, wanted: bool) -> None:
    answer(button)
    assert ask_menu_entry(None) is wanted


@pytest.mark.parametrize(("label", "removed"), [("Remove", True), ("Cancel", False)])
def test_removing_is_confirmed(qtbot: QtBot, label: str, removed: bool) -> None:
    from cube_net.ui.menu_entry_dialog import confirm_menu_entry_removal

    def click() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, MessageWindow)
        assert "no longer be in the applications menu" in box.informativeText()  # it says what it means
        button = next(b for b in box.buttons() if b.text().replace("&", "") == label)
        button.click()

    QTimer.singleShot(0, click)
    assert confirm_menu_entry_removal(None) is removed
