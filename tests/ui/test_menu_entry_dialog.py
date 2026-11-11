# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from cube_net.ui.menu_entry_dialog import ask_menu_entry


def answer(button: QMessageBox.StandardButton) -> None:
    """Click `button` of the question as soon as it's shown."""

    def click() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, QMessageBox)
        clicked = box.button(button)
        assert clicked is not None
        clicked.click()

    QTimer.singleShot(0, click)


@pytest.mark.parametrize(
    ("button", "wanted"), [(QMessageBox.StandardButton.Yes, True), (QMessageBox.StandardButton.No, False)]
)
def test_yes_or_no(qtbot: QtBot, button: QMessageBox.StandardButton, wanted: bool) -> None:
    answer(button)
    assert ask_menu_entry(None) is wanted
