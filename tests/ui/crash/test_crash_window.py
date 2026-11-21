# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

import pytest
from PyQt6.QtCore import QUrl
from pytestqt.qtbot import QtBot

from cube_net.ui.crash import crash_window
from cube_net.ui.crash.crash_window import CrashWindow
from cube_net.ui.help.about_dialog import AUTHOR_EMAIL, ISSUES_URL
from cube_net.ui.i18n import TRANSLATIONS, Language

PATH = Path("/home/me/.local/share/cube_net/Cube Net/sessions/crash-report-20261121-120000-005-42.log")


def make(qtbot: QtBot, path: Path | None = PATH) -> CrashWindow:
    window = CrashWindow(path)
    qtbot.addWidget(window)
    return window


def test_where_the_report_is_on_a_line_of_its_own_then_the_contacts(qtbot: QtBot) -> None:
    window = make(qtbot)
    lines = window.text().split("<br>")
    assert lines == [
        "An unexpected error occurred, and the application has to close. Crash report saved to:",
        str(PATH),
        "You can contact the author of this app, providing this report and some context about how this happened.",
    ]
    contacts = window.informativeText().split("<br>")
    assert contacts == ["Contacts:", AUTHOR_EMAIL, f'<a href="{ISSUES_URL}">GitHub issue</a>']
    assert ISSUES_URL == "https://github.com/Avorthoren/cube-net/issues"
    assert window.details_label.openExternalLinks()


def test_close_application_is_the_default_and_escape(qtbot: QtBot) -> None:
    window = make(qtbot)
    assert {b.text() for b in window.buttons()} == {"Open folder", "Close application"}  # in the system's order
    assert window.defaultButton() is window.close_button and window.escape_button() is window.close_button


def test_open_folder_keeps_the_window(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[QUrl] = []
    monkeypatch.setattr(crash_window.QDesktopServices, "openUrl", lambda url: opened.append(url) or True)
    window = make(qtbot)
    window.show()
    assert window.open_folder_button is not None
    window.open_folder_button.click()
    assert opened == [QUrl.fromLocalFile(str(PATH.parent))]
    assert window.isVisible() and window.clicked() is None


def test_when_the_report_could_not_be_saved(qtbot: QtBot) -> None:
    window = make(qtbot, None)
    assert "Crash report couldn't be saved." in window.text()
    assert window.open_folder_button is None and window.informativeText() == ""
    assert [b.text() for b in window.buttons()] == ["Close application"]


def test_in_russian_too(qtbot: QtBot) -> None:
    TRANSLATIONS.set_language(Language.RUSSIAN)
    window = make(qtbot)
    assert "Отчёт о сбое сохранён в:" in window.text() and "Контакты:" in window.informativeText()
    assert {b.text() for b in window.buttons()} == {"Открыть папку", "Закрыть приложение"}
