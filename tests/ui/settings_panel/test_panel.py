# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QScrollArea, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.settings_panel.panel import SettingsPanel
from cube_net.ui.style import DEFAULT_STYLE

# The panels' parents: a panel lives only as long as its parent (the window, in the app).
PARENTS: list[QWidget] = []


def make(qtbot: QtBot) -> SettingsPanel:
    parent = QWidget()
    qtbot.addWidget(parent)
    PARENTS.append(parent)
    labels, logs = QAction("labels", parent), QAction("logs", parent)
    return SettingsPanel(labels, logs, True, 1000, DEFAULT_STYLE, parent)


def test_hidden_at_first(qtbot: QtBot) -> None:
    assert make(qtbot).isHidden()


def test_tabs_scroll(qtbot: QtBot) -> None:
    panel = make(qtbot)
    assert all(isinstance(panel.tabs.widget(i), QScrollArea) for i in range(panel.tabs.count()))


def test_right_side_of_the_area(qtbot: QtBot) -> None:
    panel = make(qtbot)
    panel.place_over(QRect(100, 30, 1500, 700), 3000)
    assert panel.geometry().right() == QRect(100, 30, 1500, 700).right()
    assert (panel.geometry().top(), panel.height()) == (30, 700)


def test_at_most_a_third_of_the_screen(qtbot: QtBot) -> None:
    panel = make(qtbot)
    panel.place_over(QRect(0, 0, 1500, 700), 600)
    assert panel.width() <= 200


def test_show_tab_by_name(qtbot: QtBot) -> None:
    panel = make(qtbot)
    assert panel.tab_name() == "preferences"
    panel.show_tab("Style")
    assert panel.tab_name() == "style"
    panel.show_tab("No such tab")
    assert panel.tab_name() == "style"


def test_hide_button(qtbot: QtBot) -> None:
    panel = make(qtbot)
    assert panel.tabs.cornerWidget() is panel.hide_button
    assert panel.hide_button.text() not in ("x", "X", chr(0x00D7), chr(0x2715))  # nothing that looks like closing
    assert panel.hide_button.toolTip() == "Hide settings"
    with qtbot.waitSignal(panel.hide_requested):
        panel.hide_button.click()
