# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolBar
from pytestqt.qtbot import QtBot

from cube_net.ui.instruments.button_look import tool_buttons_style
from cube_net.ui.template.draw_hole_button import DrawHoleButton


def test_text_hint_and_clicks(qtbot: QtBot) -> None:
    toolbar = QToolBar()
    toolbar.setOrientation(Qt.Orientation.Vertical)
    toolbar.setStyleSheet(tool_buttons_style())
    qtbot.addWidget(toolbar)
    button = DrawHoleButton(toolbar)
    assert button.button.text() == "Draw\nhole" and button.button.toolTip() == "Hotkey: H"
    with qtbot.waitSignal(button.clicked):
        button.button.click()
    button.set_enabled(False)
    assert not button.button.isEnabled()
    hint = button.button.sizeHint()
    assert hint.width() == hint.height()
    assert button.button.icon().isNull()  # just its text
