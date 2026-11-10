# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import QPoint, Qt
from pytestqt.qtbot import QtBot

from cube_net.ui.help.demo.round_button import RoundButton, Symbol


def test_a_click_and_two_symbols(qtbot: QtBot) -> None:
    button = RoundButton()
    qtbot.addWidget(button)
    button.show()
    play = button.grab().toImage()
    button.set_symbol(Symbol.REPLAY)
    assert button.symbol() is Symbol.REPLAY
    assert button.grab().toImage() != play
    with qtbot.waitSignal(button.clicked):
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton, pos=QPoint(36, 36))
