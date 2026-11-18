# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QFocusEvent
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from cube_net.ui.decimal_box import DecimalBox


def make(qtbot: QtBot, value: float = 10.0) -> DecimalBox:
    box = DecimalBox(2, (0.01, 30.0), 1.0)
    qtbot.addWidget(box)
    box.setValue(value)
    box.show()
    qtbot.waitExposed(box)
    return box


def focus(box: DecimalBox, into: bool, reason: Qt.FocusReason = Qt.FocusReason.MouseFocusReason) -> None:
    QApplication.sendEvent(box, QFocusEvent(QEvent.Type.FocusIn if into else QEvent.Type.FocusOut, reason))


def text(box: DecimalBox) -> str:
    line = box.lineEdit()
    assert line is not None
    return line.text()


def test_all_its_decimals_without_the_focus(qtbot: QtBot) -> None:
    assert text(make(qtbot)) == "10.00"
    assert text(make(qtbot, 2.5)) == "2.50"


def test_no_trailing_zeros_while_it_has_the_focus(qtbot: QtBot) -> None:
    box = make(qtbot, 2.5)
    focus(box, True)
    assert text(box) == "2.5"
    box.setValue(10)
    assert text(box) == "10"
    box.stepUp()
    assert text(box) == "11"
    focus(box, False)
    assert text(box) == "11.00"


def test_what_is_typed_stays_as_it_is_and_is_padded_when_the_focus_leaves(qtbot: QtBot) -> None:
    box = make(qtbot)
    focus(box, True)
    line = box.lineEdit()
    assert line is not None
    line.selectAll()
    qtbot.keyClicks(line, "2.5")
    assert text(box) == "2.5" and box.value() == 2.5
    focus(box, False)
    assert text(box) == "2.50" and box.value() == 2.5


def test_a_tab_into_it_keeps_the_whole_number_selected(qtbot: QtBot) -> None:
    box = make(qtbot, 7.1)
    line = box.lineEdit()
    assert line is not None
    line.selectAll()
    focus(box, True, Qt.FocusReason.TabFocusReason)
    assert text(box) == "7.1" and line.selectedText() == "7.1"


def test_a_dot_never_a_comma(qtbot: QtBot) -> None:
    assert "," not in text(make(qtbot, 1.25))
