# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the user is told about updates: a newer version (with its notes and the size of the download), no newer
version, or that the check didn't work."""

from enum import Enum
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from cube_net.ui.i18n import tr
from cube_net.ui.updates.latest_release import LatestRelease

APP_NAME = "Cube Net"

# The size of the window with the notes (px).
NOTES_SIZE = (520, 220)


class UpdateChoice(Enum):
    # Get the new version: download and install it (a copy that can't update itself: its page, where the package is).
    DOWNLOAD = "download"

    # Not now (from the automatic check: and not this version again, automatically).
    LATER = "later"


class UpdateAvailableDialog(QDialog):
    """A newer version: which, against which the app is, its notes, the size of the download."""

    def __init__(
        self, release: LatestRelease, current: str, can_update: bool = False, parent: QWidget | None = None
    ) -> None:
        """`can_update`: this copy can update itself (an installed package; one run from the source can't)."""
        super().__init__(parent)
        self.setWindowTitle(tr("Update available"))
        self.heading = QLabel(
            tr("{name} {new} is available (you have {current}).", name=APP_NAME, new=release.version, current=current)
        )
        font = QFont(self.heading.font())
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * 1.15)
        self.heading.setFont(font)
        self.heading.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.heading)
        self.notes = QTextBrowser(self)
        self.notes.setOpenExternalLinks(True)
        self.notes.setMarkdown(release.notes or tr("This release has no notes."))
        self.notes.setMinimumSize(*NOTES_SIZE)
        notes_title = QLabel(tr("What's new:"))
        layout.addWidget(notes_title)
        layout.addWidget(self.notes, 1)
        size = release.package_size()
        self.size = QLabel(tr("Download size: {size}", size=format_size(size)) if size else "")
        self.size.setVisible(bool(size))
        layout.addWidget(self.size)
        buttons = QDialogButtonBox(self)
        self.download = QPushButton(tr("Download and update") if can_update else tr("Open the download page"))
        self.download.setDefault(True)
        self.later = QPushButton(tr("Not now"))
        buttons.addButton(self.download, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(self.later, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setWindowModality(Qt.WindowModality.WindowModal)

    def choice(self) -> UpdateChoice:
        return UpdateChoice.DOWNLOAD if self.result() == QDialog.DialogCode.Accepted else UpdateChoice.LATER


def ask_update(parent: QWidget | None, release: LatestRelease, current: str, can_update: bool = False) -> UpdateChoice:
    """Offer `release` (closing the window means not now)."""
    dialog = UpdateAvailableDialog(release, current, can_update, parent)
    dialog.exec()
    choice = dialog.choice()
    dialog.deleteLater()
    return choice


def tell_up_to_date(parent: QWidget | None, current: str) -> None:
    QMessageBox.information(
        parent,
        tr("Check for updates"),
        tr("No newer version found: you have the latest one ({current}).", current=current),
    )


def tell_check_failed(parent: QWidget | None, problem: str) -> None:
    QMessageBox.warning(parent, tr("Check for updates"), tr("Couldn't check for updates: {problem}", problem=problem))


def format_size(size: int) -> str:
    """Bytes as megabytes, one decimal (the packages are tens of them)."""
    return tr("{megabytes} MB", megabytes=f"{size / 1_000_000:.1f}")


class DownloadProgress(QProgressDialog):
    """The download's progress, with Cancel; the window waits for it (nothing changes in the project meanwhile)."""

    def __init__(self, version: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Update"))
        self._version = version
        self.setLabelText(tr("Downloading {name} {version}...", name=APP_NAME, version=version))
        self.setCancelButtonText(tr("Cancel"))
        self.setRange(0, 0)  # until its size is known
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setMinimumDuration(0)
        self.setWindowModality(Qt.WindowModality.WindowModal)

    def show_progress(self, done: int, total: int) -> None:
        if total > 0:
            self.setRange(0, 1000)
            self.setValue(min(1000, done * 1000 // total))
            amount = tr("{done} of {total}", done=format_size(done), total=format_size(total))
        else:
            amount = format_size(done)
        self.setLabelText(tr("Downloading {name} {version}...", name=APP_NAME, version=self._version) + "\n" + amount)


def tell_update_failed(parent: QWidget | None, problem: str) -> bool:
    """The update didn't work; whether the user wants the release's page instead."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("Update"))
    box.setText(tr("Couldn't update: {problem}", problem=problem))
    page = box.addButton(tr("Open the download page"), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(QMessageBox.StandardButton.Close)
    box.exec()
    wanted = box.clickedButton() is page
    box.deleteLater()
    return wanted


def tell_appimage_downloaded(parent: QWidget | None, version: str, downloaded: Path, target: Path) -> bool:
    """Linux: the new AppImage couldn't be put in place (its folder needs administrator rights); whether the user
    wants to start it from where it is now (this one quits then)."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(tr("Update"))
    box.setText(
        tr("{name} {version} is downloaded, but it couldn't take the old one's place.", name=APP_NAME, version=version)
    )
    box.setInformativeText(
        tr(
            "The new version is {downloaded}. Start it from there (the applications menu follows it), or put it in "
            "place yourself, in a terminal:",
            downloaded=downloaded,
        )
        + f"\n\nsudo install -m 0755 '{downloaded}' '{target}'"
    )
    box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    start = box.addButton(tr("Start the new version"), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(QMessageBox.StandardButton.Close)
    box.exec()
    wanted = box.clickedButton() is start
    box.deleteLater()
    return wanted


def tell_macos_downloaded(parent: QWidget | None, version: str) -> None:
    """macOS: the new app couldn't replace the old one by itself; the .dmg is open in Finder for the user."""
    QMessageBox.information(
        parent,
        tr("Update"),
        tr(
            "{name} {version} is downloaded and open in Finder. To finish, drag {name} onto Applications there, "
            "replacing the old one, then start it again.",
            name=APP_NAME,
            version=version,
        ),
    )
