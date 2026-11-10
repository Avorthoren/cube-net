# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtGui import QAction
from pytestqt.qtbot import QtBot

from cube_net.ui.settings_panel.preferences_tab import PreferencesTab


def make(qtbot: QtBot) -> tuple[PreferencesTab, QAction, QAction]:
    labels, logs = QAction("labels"), QAction("logs")
    for action in (labels, logs):
        action.setCheckable(True)
    labels.setChecked(True)
    tab = PreferencesTab(labels, logs, True, 1234)
    qtbot.addWidget(tab)
    return tab, labels, logs


def test_wording(qtbot: QtBot) -> None:
    tab, _, _ = make(qtbot)
    assert (tab.show_labels.text(), tab.auto_log.text()) == ("Show vertex labels", "Auto-start logging")


def test_boxes_and_actions_are_one_switch(qtbot: QtBot) -> None:
    tab, labels, logs = make(qtbot)
    assert tab.show_labels.isChecked() and not tab.auto_log.isChecked()
    tab.auto_log.setChecked(True)
    assert logs.isChecked()
    labels.setChecked(False)
    assert not tab.show_labels.isChecked()


def test_max_zoom(qtbot: QtBot) -> None:
    tab, _, _ = make(qtbot)
    assert tab.max_zoom.value() == 1234
    assert (tab.max_zoom.minimum(), tab.max_zoom.maximum()) == (500, 10000)
    with qtbot.waitSignal(tab.max_zoom_changed) as blocker:
        tab.max_zoom.setValue(2000)
    assert blocker.args == [2000]


def test_max_zoom_unit_is_outside_the_field(qtbot: QtBot) -> None:
    from PyQt6.QtWidgets import QLabel

    tab, _, _ = make(qtbot)
    assert tab.max_zoom.suffix() == ""
    assert any(label.text() == "px per unit" for label in tab.findChildren(QLabel))


def test_blink_like_the_other_switches(qtbot: QtBot) -> None:
    tab, _, _ = make(qtbot)
    tab.show()
    assert tab.blink.text() == "Blink when target area achieved"
    assert tab.blink.isChecked()
    top = tab.blink.mapTo(tab, tab.blink.rect().topLeft())
    assert top.x() == tab.auto_log.mapTo(tab, tab.auto_log.rect().topLeft()).x()
    assert tab.auto_log.mapTo(tab, tab.auto_log.rect().topLeft()).y() < top.y()
    assert top.y() < tab.max_zoom.mapTo(tab, tab.max_zoom.rect().topLeft()).y()
    with qtbot.waitSignal(tab.blink_changed) as blocker:
        tab.blink.setChecked(False)
    assert blocker.args == [False]
