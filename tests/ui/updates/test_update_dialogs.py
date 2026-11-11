# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from cube_net.ui.updates import update_dialogs
from cube_net.ui.updates.latest_release import LatestRelease, ReleaseFile
from cube_net.ui.updates.update_dialogs import UpdateAvailableDialog, UpdateChoice, format_size

RELEASE = LatestRelease(
    "1.2.0",
    "- Ctrl+click deletes a point.",
    "https://example.com",
    {"CubeNet-1.2.0-linux-x86_64.AppImage": ReleaseFile(78_400_000, "https://example.com/CubeNet.AppImage")},
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


def test_the_button_says_what_it_does(qtbot: QtBot) -> None:
    dialog = UpdateAvailableDialog(RELEASE, "1.0.0", can_update=True)
    qtbot.addWidget(dialog)
    assert dialog.download.text() == "Download and update"


def test_the_progress_of_the_download(qtbot: QtBot) -> None:
    progress = update_dialogs.DownloadProgress("1.2.0")
    qtbot.addWidget(progress)
    assert progress.maximum() == 0  # its size not known yet
    progress.show_progress(39_200_000, 78_400_000)
    assert progress.value() == 500
    assert progress.labelText() == "Downloading Cube Net 1.2.0...\n39.2 MB of 78.4 MB"


def click_later(text: str) -> None:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    def click() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, QMessageBox)
        next(b for b in box.buttons() if b.text().replace("&", "") == text).click()

    QTimer.singleShot(0, click)


@pytest.mark.parametrize(("button", "wanted"), [("Open the download page", True), ("Close", False)])
def test_a_failed_update(qtbot: QtBot, button: str, wanted: bool) -> None:
    click_later(button)
    assert update_dialogs.tell_update_failed(None, "no network") is wanted


@pytest.mark.parametrize(("button", "wanted"), [("Start the new version", True), ("Close", False)])
def test_an_appimage_left_in_downloads(qtbot: QtBot, button: str, wanted: bool) -> None:
    from pathlib import Path

    click_later(button)
    downloaded, target = Path("/home/me/Downloads/CubeNet-1.2.0.AppImage"), Path("/opt/CubeNet-1.2.0.AppImage")
    assert update_dialogs.tell_appimage_downloaded(None, "1.2.0", downloaded, target) is wanted
