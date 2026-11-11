# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from cube_net.ui.updates import update_dialogs
from cube_net.ui.updates.latest_release import LatestRelease
from cube_net.ui.updates.update_dialogs import UpdateAvailableDialog, UpdateChoice, format_size

RELEASE = LatestRelease(
    "1.2.0",
    "- Ctrl+click deletes a point.",
    "https://example.com",
    {"CubeNet-1.2.0-linux-x86_64.AppImage": 78_400_000},
)


def make(qtbot: QtBot, release: LatestRelease = RELEASE) -> UpdateAvailableDialog:
    dialog = UpdateAvailableDialog(release, "1.0.0")
    qtbot.addWidget(dialog)
    return dialog


def test_what_it_tells(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    assert dialog.heading.text() == "Cube Net 1.2.0 is available (you have 1.0.0)."
    assert "Ctrl+click deletes a point." in dialog.notes.toPlainText()
    assert dialog.download.text() == "Open the download page" and dialog.later.text() == "Not now"


def test_the_size_on_linux(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cube_net.ui.updates.latest_release.sys.platform", "linux")
    dialog = make(qtbot)
    assert dialog.size.text() == "Download size: 78.4 MB"


def test_no_size_or_notes_when_there_are_none(qtbot: QtBot) -> None:
    release = LatestRelease("1.2.0", "", "https://example.com", {})
    dialog = make(qtbot, release)
    assert dialog.size.isHidden()
    assert dialog.notes.toPlainText() == "This release has no notes."


@pytest.mark.parametrize(("accepted", "choice"), [(True, UpdateChoice.DOWNLOAD), (False, UpdateChoice.LATER)])
def test_the_choice(qtbot: QtBot, accepted: bool, choice: UpdateChoice) -> None:
    dialog = make(qtbot)
    if accepted:
        dialog.accept()
    else:
        dialog.reject()  # also closing it
    assert dialog.choice() is choice


def test_sizes() -> None:
    assert format_size(78_400_000) == "78.4 MB"


def test_the_other_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    said: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", lambda _parent, _title, text: said.append(text))
    monkeypatch.setattr(QMessageBox, "warning", lambda _parent, _title, text: said.append(text))
    update_dialogs.tell_up_to_date(None, "1.2.0")
    update_dialogs.tell_check_failed(None, "no network")
    assert said == [
        "No newer version found: you have the latest one (1.2.0).",
        "Couldn't check for updates: no network",
    ]
