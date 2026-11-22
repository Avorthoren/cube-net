# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from pytestqt.qtbot import QtBot

from cube_net.ui.path_label import PathLabel

LONG = Path("/home/someone/projects/private/a/folder/with/a/long/name/far/down/there/second.cubenet")


def test_all_of_it_where_there_is_room(qtbot: QtBot) -> None:
    label = PathLabel()
    qtbot.addWidget(label)
    label.resize(2000, 20)
    label.set_path(LONG)
    assert label.text() == str(LONG) and label.toolTip() == str(LONG)


def test_shortened_in_the_middle(qtbot: QtBot) -> None:
    label = PathLabel()
    qtbot.addWidget(label)
    label.show()
    qtbot.waitExposed(label)
    label.set_path(LONG)
    label.resize(200, 20)
    assert "…" in label.text()
    assert label.text().startswith("/home") and label.text().endswith("cubenet")
    assert label.path() == str(LONG) and label.toolTip() == str(LONG)
    label.resize(2000, 20)
    assert label.text() == str(LONG)  # room again: all of it


def test_nothing_without_a_file(qtbot: QtBot) -> None:
    label = PathLabel()
    qtbot.addWidget(label)
    label.set_path(LONG)
    label.set_path(None)
    assert label.text() == "" and label.toolTip() == ""
