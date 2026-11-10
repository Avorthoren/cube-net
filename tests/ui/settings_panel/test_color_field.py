# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pytestqt.qtbot import QtBot

from cube_net.ui.settings_panel.color_field import ColorField


def make(qtbot: QtBot) -> ColorField:
    field = ColorField("#0057B8")
    qtbot.addWidget(field)
    return field


def test_shows_the_digits_after_a_hash(qtbot: QtBot) -> None:
    field = make(qtbot)
    assert field.edit.text() == "0057B8"
    assert field.color() == "#0057B8"


def test_a_complete_colour_is_taken_at_once(qtbot: QtBot) -> None:
    field = make(qtbot)
    field.edit.clear()
    with qtbot.waitSignal(field.changed) as blocker:
        qtbot.keyClicks(field.edit, "a1b2c3")
    assert blocker.args == ["#A1B2C3"]
    assert field.color() == "#A1B2C3"


def test_only_hex_digits_and_at_most_six(qtbot: QtBot) -> None:
    field = make(qtbot)
    field.edit.clear()
    qtbot.keyClicks(field.edit, "#zz12345678")
    assert field.edit.text() == "123456"


def test_an_unfinished_colour_goes_back(qtbot: QtBot) -> None:
    field = make(qtbot)
    field.edit.clear()
    with qtbot.assertNotEmitted(field.changed):
        qtbot.keyClicks(field.edit, "12")
    field.edit.editingFinished.emit()
    assert field.edit.text() == "0057B8"


def test_set_color_tells_nobody(qtbot: QtBot) -> None:
    field = make(qtbot)
    with qtbot.assertNotEmitted(field.changed):
        field.set_color("#FFFFFF")
    assert field.edit.text() == "FFFFFF"
