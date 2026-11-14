# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QAction, QKeySequence
from pytestqt.qtbot import QtBot

from cube_net.ui.app_settings import AppSettings
from cube_net.ui.help.hotkeys import HOTKEYS, Hotkey, native, native_modifier
from cube_net.ui.key_release_shortcut import KeyReleaseShortcut
from cube_net.ui.main_window import MainWindow

PORTABLE = QKeySequence.SequenceFormat.PortableText


def listed_keys() -> set[str]:
    """The keys the help lists (alone, without the mouse), as portable text."""
    return {
        QKeySequence(hotkey.keys).toString(PORTABLE)
        for group in HOTKEYS
        for hotkey in group.hotkeys
        if not hotkey.mouse and not hotkey.held  # a held modifier works with the mouse: not a shortcut
    }


def the_applications_keys(qtbot: QtBot, tmp_path: Path) -> list[set[str]]:
    """Every shortcut of the main window: for each action, the keys that do it (any one of them is enough)."""
    window = MainWindow(settings=AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)))
    qtbot.addWidget(window)
    keys = [
        {shortcut.toString(PORTABLE) for shortcut in action.shortcuts()}
        for action in window.findChildren(QAction)
        if action.shortcuts()
    ]
    keys += [{QKeySequence(shortcut.key()).toString(PORTABLE)} for shortcut in window.findChildren(KeyReleaseShortcut)]
    return keys


def test_every_shortcut_of_the_application_is_in_the_help(qtbot: QtBot, tmp_path: Path) -> None:
    listed = listed_keys()
    missing = [keys for keys in the_applications_keys(qtbot, tmp_path) if not keys & listed]
    assert missing == []


def test_every_key_in_the_help_is_a_shortcut(qtbot: QtBot, tmp_path: Path) -> None:
    real = set().union(*the_applications_keys(qtbot, tmp_path)) | {"Esc"}  # Esc also closes the help window itself
    assert listed_keys() - real == set()


def test_a_key_can_do_two_things() -> None:
    escapes = [hotkey for group in HOTKEYS for hotkey in group.hotkeys if hotkey.keys == "Esc"]
    assert len({hotkey.action for hotkey in escapes}) == 2  # unlock a slope; close the help


def test_how_they_are_written() -> None:
    assert Hotkey("Ctrl+Shift+S", "", "Save").shown() == native("Ctrl+Shift+S")
    assert Hotkey("Shift", "drag a vertex", "x").shown() == f"{native_modifier('Shift')} + drag a vertex"
    assert Hotkey("", "right-click", "x").shown() == "right-click"
    assert native_modifier("Ctrl") in (native("Ctrl+A")[:-1].rstrip("+"),)
