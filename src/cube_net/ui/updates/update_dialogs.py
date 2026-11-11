# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the user is told about updates: a newer version (with its notes and the size of the download), no newer
version, or that the check didn't work."""

from enum import Enum

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
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
    # Get the new version (for now: its page, where the package is).
    DOWNLOAD = "download"

    # Not now (from the automatic check: and not this version again, automatically).
    LATER = "later"


class UpdateAvailableDialog(QDialog):
    """A newer version: which, against which the app is, its notes, the size of the download."""

    def __init__(self, release: LatestRelease, current: str, parent: QWidget | None = None) -> None:
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
        self.download = QPushButton(tr("Open the download page"))
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


def ask_update(parent: QWidget | None, release: LatestRelease, current: str) -> UpdateChoice:
    """Offer `release` (closing the window means not now)."""
    dialog = UpdateAvailableDialog(release, current, parent)
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
