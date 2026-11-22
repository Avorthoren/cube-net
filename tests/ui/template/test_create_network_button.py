# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolBar
from pytestqt.qtbot import QtBot

from cube_net.ui.i18n import TRANSLATIONS, Language
from cube_net.ui.instruments.button_look import tool_buttons_style
from cube_net.ui.template.create_network_button import CreateNetworkButton

# The toolbars of the buttons made (a button lives as long as its toolbar).
TOOLBARS: list[QToolBar] = []


def make(qtbot: QtBot) -> CreateNetworkButton:
    toolbar = QToolBar()
    toolbar.setOrientation(Qt.Orientation.Vertical)
    toolbar.setStyleSheet(tool_buttons_style())
    qtbot.addWidget(toolbar)
    TOOLBARS.append(toolbar)
    return CreateNetworkButton(toolbar)


def test_text_on_two_lines_no_hotkey_and_clicks(qtbot: QtBot) -> None:
    button = make(qtbot)
    assert button.button.text() == "Create\nnetwork" and button.button.toolTip() == ""
    with qtbot.waitSignal(button.clicked):
        button.button.click()
    button.set_enabled(False)
    assert not button.button.isEnabled()
    hint = button.button.sizeHint()
    assert hint.width() == hint.height()


def test_in_russian(qtbot: QtBot) -> None:
    button = make(qtbot)
    TRANSLATIONS.set_language(Language.RUSSIAN)
    assert button.button.text() == "Создать\nразвёртку"
