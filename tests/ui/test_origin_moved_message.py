# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from cube_net.core.geometry import Vec
from cube_net.ui.dialogs.message_window import MessageWindow
from cube_net.ui.origin_moved_message import origin_moved_text, subscripted, tell_origin_moved
from cube_net.ui.sheet.coordinates_text import coordinate_lines


def test_the_text_with_and_without_a_name() -> None:
    assert origin_moved_text("C_1") == "Coordinates of C<sub>1</sub> were set to:"
    assert origin_moved_text(None) == "Coordinates of the point were set to:"


def test_says_the_hints_lines_and_ok_closes_it(qtbot: QtBot) -> None:
    seen: list[tuple[str, str]] = []

    def answer() -> None:
        window = QApplication.activeModalWidget()
        assert isinstance(window, MessageWindow)
        seen.append((window.text(), window.informativeText()))
        assert window.text_label.textFormat() is Qt.TextFormat.RichText
        window.buttons()[0].click()

    QTimer.singleShot(50, answer)
    tell_origin_moved(None, "C_1", Vec(F(21, 2), 13))
    assert seen == [("Coordinates of C<sub>1</sub> were set to:", "\n".join(coordinate_lines(Vec(F(21, 2), 13))))]


def test_the_index_as_a_subscript() -> None:
    assert subscripted("C_1") == "C<sub>1</sub>"
    assert subscripted("AB_12") == "AB<sub>12</sub>"
    assert subscripted("C") == "C"  # no index
