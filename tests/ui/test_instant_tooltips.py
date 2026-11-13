# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF
from PyQt6.QtGui import QEnterEvent, QHelpEvent
from PyQt6.QtWidgets import QApplication, QCheckBox, QSpinBox, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.instant_tooltips import InstantTooltips


class Panel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.box = QCheckBox("Show vertex labels", self)
        self.box.setToolTip("Hotkey: L")
        self.plain = QCheckBox("No hint", self)
        self.number = QSpinBox(self)
        self.number.setToolTip("From 10 to 1000")
        layout = QVBoxLayout(self)
        for widget in (self.box, self.plain, self.number):
            layout.addWidget(widget)
        self.tooltips = InstantTooltips(self)


@pytest.fixture
def panel(qtbot: QtBot) -> Panel:
    panel = Panel()
    qtbot.addWidget(panel)
    panel.show()
    qtbot.waitExposed(panel)
    return panel


def enter(widget: QWidget) -> None:
    QApplication.sendEvent(widget, QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(widget.mapToGlobal(QPoint(5, 5)))))


def leave(widget: QWidget) -> None:
    QApplication.sendEvent(widget, QEvent(QEvent.Type.Leave))


def test_shown_as_soon_as_the_mouse_is_on_it_and_hidden_as_soon_as_it_leaves(panel: Panel) -> None:
    enter(panel.box)
    assert panel.tooltips.label.isVisible() and panel.tooltips.label.text() == "Hotkey: L"
    assert panel.tooltips.shown_for() is panel.box
    leave(panel.box)
    assert not panel.tooltips.label.isVisible() and panel.tooltips.shown_for() is None


def test_nothing_for_a_widget_without_a_tooltip(panel: Panel) -> None:
    enter(panel.plain)
    assert not panel.tooltips.label.isVisible()


def test_the_text_is_read_when_shown(panel: Panel) -> None:
    panel.box.setToolTip("Клавиша: L")  # the language changed, say
    enter(panel.box)
    assert panel.tooltips.label.text() == "Клавиша: L"


def test_a_widget_inside_a_widget_with_a_tooltip(panel: Panel) -> None:
    editor = panel.number.findChild(QWidget)  # the spin box's text field
    assert editor is not None
    enter(panel.number)
    enter(editor)  # it has none of its own: the spin box's stays
    assert panel.tooltips.shown_for() is panel.number and panel.tooltips.label.isVisible()
    leave(editor)
    leave(panel.number)
    assert not panel.tooltips.label.isVisible()


def test_hidden_with_its_widget(panel: Panel) -> None:
    enter(panel.box)
    panel.hide()
    assert not panel.tooltips.label.isVisible()


def test_qts_own_late_tooltip_is_not_shown(panel: Panel) -> None:
    event = QHelpEvent(QEvent.Type.ToolTip, QPoint(5, 5), panel.box.mapToGlobal(QPoint(5, 5)))
    assert QApplication.sendEvent(panel.box, event)  # taken: Qt doesn't show its own
