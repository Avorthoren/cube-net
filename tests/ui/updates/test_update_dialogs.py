# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QPushButton
from pytestqt.qtbot import QtBot

from cube_net.ui.dialogs.message_window import MessageWindow
from cube_net.ui.dialogs.small_window import SmallWindow
from cube_net.ui.updates import update_dialogs
from cube_net.ui.updates.latest_release import LatestRelease, ReleaseFile, ReleaseNotes
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
    assert dialog.download_size.text() == "Download size: 78.4 MB"


def test_no_size_or_notes_when_there_are_none(qtbot: QtBot) -> None:
    release = LatestRelease("1.2.0", "", "https://example.com", {})
    dialog = make(qtbot, release)
    assert dialog.download_size.isHidden()
    assert dialog.notes.toPlainText() == "1.2.0\nThis release has no notes."


@pytest.mark.parametrize(("accepted", "choice"), [(True, UpdateChoice.DOWNLOAD), (False, UpdateChoice.LATER)])
def test_the_choice(qtbot: QtBot, accepted: bool, choice: UpdateChoice) -> None:
    dialog = make(qtbot)
    if accepted:
        dialog.accept()
    else:
        dialog.reject()  # also closing it
    assert dialog.choice() is choice


def wait_shown(qtbot: QtBot, window: SmallWindow) -> None:
    window.show()
    qtbot.waitExposed(window)
    qtbot.waitUntil(window.isActiveWindow)


def test_from_the_menu_the_download_button_is_selected(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    wait_shown(qtbot, dialog)
    assert QApplication.focusWidget() is dialog.download and dialog.download.isDefault()
    qtbot.keyClick(dialog.download, Qt.Key.Key_Return)
    assert dialog.choice() is UpdateChoice.DOWNLOAD


@pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Space])
def test_from_the_automatic_check_no_button_is_selected(qtbot: QtBot, key: Qt.Key) -> None:
    dialog = UpdateAvailableDialog(RELEASE, "1.0.0", automatic=True)
    qtbot.addWidget(dialog)
    wait_shown(qtbot, dialog)
    assert not isinstance(QApplication.focusWidget(), QPushButton)
    assert not any(button.isDefault() for button in dialog.findChildren(QPushButton))
    qtbot.keyClick(dialog, key)
    assert dialog.isVisible()  # nothing pressed
    qtbot.keyClick(dialog, Qt.Key.Key_Tab)
    if QApplication.focusWidget() is dialog.copy_button:  # it's a button too, but not one of the answers
        qtbot.keyClick(dialog.copy_button, Qt.Key.Key_Tab)
    focused = QApplication.focusWidget()
    assert focused in (dialog.download, dialog.later)
    qtbot.keyClick(focused, key)
    assert not dialog.isVisible()
    assert dialog.choice() is (UpdateChoice.DOWNLOAD if focused is dialog.download else UpdateChoice.LATER)


def test_from_the_automatic_check_escape_means_not_now(qtbot: QtBot) -> None:
    dialog = UpdateAvailableDialog(RELEASE, "1.0.0", automatic=True)
    qtbot.addWidget(dialog)
    dialog.accept()  # a result that Escape must replace
    wait_shown(qtbot, dialog)
    qtbot.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()
    assert dialog.choice() is UpdateChoice.LATER


def notes(version: str, text: str, date: str = "") -> ReleaseNotes:
    return ReleaseNotes(version, date, text)


HISTORY = (
    notes("1.3.0", "- Cuts from any point.", "2027-03-02"),
    notes("1.2.0", "- Themes.", "2027-02-10"),
    notes("1.1.0", "", "2027-01-20"),
    notes("1.0.0", "- First.", "2026-12-01"),
)


def several_versions_behind(qtbot: QtBot, history: tuple[ReleaseNotes, ...] = HISTORY) -> UpdateAvailableDialog:
    release = LatestRelease("1.3.0", history[0].notes, "https://example.com", {}, history[0].date, history)
    dialog = UpdateAvailableDialog(release, "1.0.0")
    qtbot.addWidget(dialog)
    return dialog


def test_the_notes_of_every_version_since_the_users(qtbot: QtBot) -> None:
    dialog = several_versions_behind(qtbot)
    shown = dialog.notes.toPlainText()
    assert shown == (
        "1.3.0 (2027-03-02)\nCuts from any point.\n"
        "1.2.0 (2027-02-10)\nThemes.\n"
        "1.1.0 (2027-01-20)\nThis release has no notes."
    )


def test_copy_copies_all_the_notes_as_text(qtbot: QtBot) -> None:
    dialog = several_versions_behind(qtbot)
    clipboard = QApplication.clipboard()
    assert clipboard is not None
    dialog.copy_button.click()
    assert (
        clipboard.text()
        == dialog.notes_text()
        == (
            "1.3.0 (2027-03-02)\n- Cuts from any point.\n\n"
            "1.2.0 (2027-02-10)\n- Themes.\n\n"
            "1.1.0 (2027-01-20)\nThis release has no notes."
        )
    )
    assert dialog.copy_button.text() == "Copied"
    qtbot.waitUntil(lambda: dialog.copy_button.text() == "Copy", timeout=update_dialogs.COPIED_MS + 2000)


def test_short_notes_fit_without_scrolling(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    wait_shown(qtbot, dialog)
    assert dialog.notes.height() < update_dialogs.NOTES_MAX_HEIGHT_PX
    scroll_bar = dialog.notes.verticalScrollBar()
    assert scroll_bar is not None and scroll_bar.maximum() == 0


def test_long_notes_scroll(qtbot: QtBot) -> None:
    lines = "\n".join(f"- Change number {number}." for number in range(10))
    history = tuple(notes(f"1.{minor}.0", lines) for minor in range(3, 0, -1))
    dialog = several_versions_behind(qtbot, history)
    wait_shown(qtbot, dialog)
    assert dialog.notes.height() == update_dialogs.NOTES_MAX_HEIGHT_PX
    scroll_bar = dialog.notes.verticalScrollBar()
    assert scroll_bar is not None and scroll_bar.maximum() > 0


def test_sizes() -> None:
    assert format_size(78_400_000) == "78.4 MB"


def test_the_other_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    said: list[str] = []
    monkeypatch.setattr(update_dialogs, "tell", lambda _parent, _title, text, **_: said.append(text))
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
    assert progress.bar.maximum() == 0  # its size not known yet
    progress.show_progress(39_200_000, 78_400_000)
    assert progress.value() == 500
    assert progress.label_text() == "Downloading Cube Net 1.2.0...\n39.2 MB of 78.4 MB"


def test_the_download_can_only_be_cancelled_with_its_button(qtbot: QtBot) -> None:
    progress = update_dialogs.DownloadProgress("1.2.0")
    qtbot.addWidget(progress)
    canceled: list[bool] = []
    progress.canceled.connect(lambda: canceled.append(True))
    wait_shown(qtbot, progress)
    assert progress.title_bar.close_button.isHidden()
    assert QApplication.focusWidget() is not progress.cancel_button and not progress.cancel_button.isDefault()
    for key in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Space):
        qtbot.keyClick(progress, key)
    assert progress.isVisible() and canceled == []
    qtbot.keyClick(progress, Qt.Key.Key_Tab)
    assert QApplication.focusWidget() is progress.cancel_button
    qtbot.keyClick(progress.cancel_button, Qt.Key.Key_Space)
    assert canceled == [True] and not progress.isVisible()


def test_a_finished_download_closes_its_window_without_cancelling(qtbot: QtBot) -> None:
    progress = update_dialogs.DownloadProgress("1.2.0")
    qtbot.addWidget(progress)
    canceled: list[bool] = []
    progress.canceled.connect(lambda: canceled.append(True))
    wait_shown(qtbot, progress)
    progress.finish()
    assert not progress.isVisible() and canceled == []


def click_later(text: str) -> None:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    def click() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, MessageWindow)
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
