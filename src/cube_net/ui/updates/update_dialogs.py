# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the user is told about updates: a newer version (with its notes and the size of the download), the download's
progress, no newer version, or that something didn't work. All in the application's own small windows (only a close
button in the title bar)."""

from enum import Enum
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cube_net.ui.dialogs.message_window import MessageIcon, MessageWindow, tell
from cube_net.ui.dialogs.small_window import SmallWindow
from cube_net.ui.i18n import tr
from cube_net.ui.updates.latest_release import LatestRelease, ReleaseNotes

APP_NAME = "Cube Net"

# The width of the notes, and the least and the most of their height (px): they're as tall as they need to be between
# the two, and scroll when they need more.
NOTES_WIDTH_PX = 560
NOTES_MIN_HEIGHT_PX = 120
NOTES_MAX_HEIGHT_PX = 420

# How long the Copy button says "Copied" (ms).
COPIED_MS = 1500

# How wide the progress window is (px).
PROGRESS_WIDTH_PX = 400


class UpdateChoice(Enum):
    # Get the new version: download and install it (a copy that can't update itself: its page, where the package is).
    DOWNLOAD = "download"

    # Not now (from the automatic check: and not this version again, automatically).
    LATER = "later"


class UpdateAvailableDialog(SmallWindow):
    """A newer version: which, against which the app is, what's new since that one (the notes of every version in
    between, with a Copy button), the size of the download. Escape and the close button mean "Not now"."""

    def __init__(
        self,
        release: LatestRelease,
        current: str,
        can_update: bool = False,
        automatic: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """`can_update`: this copy can update itself (an installed package; one run from the source can't).
        `automatic`: offered by the automatic check, which the user didn't ask for: no button is selected then (a key
        pressed just as it appears doesn't answer it), otherwise the download one is."""
        super().__init__(tr("Update available"), parent)
        self.heading = QLabel(
            tr("{name} {new} is available (you have {current}).", name=APP_NAME, new=release.version, current=current)
        )
        font = QFont(self.heading.font())
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * 1.15)
        self.heading.setFont(font)
        self.heading.setWordWrap(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self.heading)
        changes = release.notes_since(current)
        self.notes = QTextBrowser(self)
        self.notes.setOpenExternalLinks(True)
        self.notes.setMarkdown(notes_markdown(changes))
        self.notes.setFocusPolicy(Qt.FocusPolicy.ClickFocus)  # Tab goes through the buttons
        self.notes.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._fit_notes()
        self._notes_text = notes_text(changes)
        self.copy_button = QToolButton(self)
        self.copy_button.setText(tr("Copy"))
        self.copy_button.setIcon(QIcon.fromTheme("edit-copy"))
        self.copy_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.copy_button.setToolTip(tr("Copy what's new (to translate it, say)"))
        self.copy_button.clicked.connect(self._copy_notes)
        self._copied = QTimer(self)  # how long the button says "Copied"
        self._copied.setSingleShot(True)
        self._copied.setInterval(COPIED_MS)
        self._copied.timeout.connect(lambda: self.copy_button.setText(tr("Copy")))
        above = QHBoxLayout()
        above.addWidget(QLabel(tr("What's new:")))
        above.addStretch()
        above.addWidget(self.copy_button)
        layout.addLayout(above)
        layout.addWidget(self.notes)
        size = release.package_size()
        self.download_size = QLabel(tr("Download size: {size}", size=format_size(size)) if size else "")
        self.download_size.setVisible(bool(size))
        layout.addWidget(self.download_size)
        buttons = QDialogButtonBox(self)
        self.download = QPushButton(tr("Download and update") if can_update else tr("Open the download page"))
        self.later = QPushButton(tr("Not now"))
        buttons.addButton(self.download, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(self.later, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.body.addLayout(layout)
        if automatic:
            self.select_no_button()
        else:
            self.download.setDefault(True)
            self.download.setFocus()

    def _fit_notes(self) -> None:
        """As tall as the notes need, between the least and the most."""
        frame = 2 * self.notes.frameWidth()
        shown = self.notes.document()
        assert shown is not None
        document = shown.clone(self)  # the browser lays out its own at its own width, which isn't known yet
        document.setTextWidth(NOTES_WIDTH_PX - frame)
        needed = int(document.size().height()) + frame + 2
        document.deleteLater()
        self.notes.setFixedSize(NOTES_WIDTH_PX, max(NOTES_MIN_HEIGHT_PX, min(NOTES_MAX_HEIGHT_PX, needed)))

    def notes_text(self) -> str:
        """What the Copy button copies."""
        return self._notes_text

    def _copy_notes(self) -> None:
        clipboard = QApplication.clipboard()
        assert clipboard is not None
        clipboard.setText(self._notes_text)
        self.copy_button.setText(tr("Copied"))
        self._copied.start()

    def choice(self) -> UpdateChoice:
        return UpdateChoice.DOWNLOAD if self.result() == SmallWindow.DialogCode.Accepted else UpdateChoice.LATER


def _heading(changes: ReleaseNotes) -> str:
    return f"{changes.version} ({changes.date})" if changes.date else changes.version


def notes_markdown(changes: list[ReleaseNotes]) -> str:
    """What's new in each version (the newest first), under its version and date."""
    return "\n\n".join(
        f"### {_heading(each)}\n\n{each.notes.strip() or tr('This release has no notes.')}" for each in changes
    )


def notes_text(changes: list[ReleaseNotes]) -> str:
    """The same as plain text, for the clipboard."""
    return "\n\n".join(
        f"{_heading(each)}\n{each.notes.strip() or tr('This release has no notes.')}" for each in changes
    )


def ask_update(
    parent: QWidget | None, release: LatestRelease, current: str, can_update: bool = False, automatic: bool = False
) -> UpdateChoice:
    """Offer `release` (closing the window means not now; `automatic`: see `UpdateAvailableDialog`)."""
    dialog = UpdateAvailableDialog(release, current, can_update, automatic, parent)
    dialog.exec()
    choice = dialog.choice()
    dialog.deleteLater()
    return choice


def tell_up_to_date(parent: QWidget | None, current: str) -> None:
    tell(
        parent,
        tr("Check for updates"),
        tr("No newer version found: you have the latest one ({current}).", current=current),
    )


def tell_check_failed(parent: QWidget | None, problem: str) -> None:
    tell(
        parent,
        tr("Check for updates"),
        tr("Couldn't check for updates: {problem}", problem=problem),
        icon=MessageIcon.WARNING,
    )


def format_size(size: int) -> str:
    """Bytes as megabytes, one decimal (the packages are tens of them)."""
    return tr("{megabytes} MB", megabytes=f"{size / 1_000_000:.1f}")


class DownloadProgress(SmallWindow):
    """The download's progress, with Cancel; the window waits for it (nothing changes in the project meanwhile).
    Only Cancel cancels it (not selected at first, so a stray Enter or Space doesn't): there's no close button, and
    Escape does nothing. When the download is over, `finish` closes it."""

    # The user wants the download stopped.
    canceled = pyqtSignal()

    def __init__(self, version: str, parent: QWidget | None = None) -> None:
        super().__init__(tr("Update"), parent)
        self._version = version
        self._finished = False
        self.label = QLabel(tr("Downloading {name} {version}...", name=APP_NAME, version=version))
        self.bar = QProgressBar(self)
        self.bar.setRange(0, 0)  # until its size is known
        self.bar.setTextVisible(False)
        buttons = QDialogButtonBox(self)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        assert cancel is not None
        self.cancel_button = cancel
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self.label)
        layout.addWidget(self.bar)
        layout.addWidget(buttons)
        self.body.addLayout(layout)
        self.setMinimumWidth(PROGRESS_WIDTH_PX)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.make_unclosable()
        self.select_no_button()

    def show_progress(self, done: int, total: int) -> None:
        if total > 0:
            self.bar.setRange(0, 1000)
            self.bar.setValue(min(1000, done * 1000 // total))
            amount = tr("{done} of {total}", done=format_size(done), total=format_size(total))
        else:
            amount = format_size(done)
        self.label.setText(tr("Downloading {name} {version}...", name=APP_NAME, version=self._version) + "\n" + amount)

    def value(self) -> int:
        return self.bar.value()

    def label_text(self) -> str:
        return self.label.text()

    def finish(self) -> None:
        """The download is over (done or failed): close, without cancelling anything."""
        self._finished = True
        self.close()

    def reject(self) -> None:
        if not self._finished:
            self.canceled.emit()
        super().reject()


def tell_update_failed(parent: QWidget | None, problem: str) -> bool:
    """The update didn't work; whether the user wants the release's page instead."""
    window = MessageWindow(
        tr("Update"), tr("Couldn't update: {problem}", problem=problem), "", MessageIcon.WARNING, parent
    )
    page = window.add(tr("Open the download page"), QDialogButtonBox.ButtonRole.AcceptRole)
    close = window.add_standard(QDialogButtonBox.StandardButton.Close)
    window.set_default(page)
    window.set_escape(close)
    return window.ask() is page


def tell_appimage_downloaded(parent: QWidget | None, version: str, downloaded: Path, target: Path) -> bool:
    """Linux: the new AppImage couldn't be put in place (its folder needs administrator rights); whether the user
    wants to start it from where it is now (this one quits then)."""
    details = (
        tr(
            "The new version is {downloaded}. Start it from there (the applications menu follows it), or put it in "
            "place yourself, in a terminal:",
            downloaded=downloaded,
        )
        + f"\n\nsudo install -m 0755 '{downloaded}' '{target}'"
    )
    window = MessageWindow(
        tr("Update"),
        tr("{name} {version} is downloaded, but it couldn't take the old one's place.", name=APP_NAME, version=version),
        details,
        MessageIcon.INFORMATION,
        parent,
    )
    start = window.add(tr("Start the new version"), QDialogButtonBox.ButtonRole.AcceptRole)
    close = window.add_standard(QDialogButtonBox.StandardButton.Close)
    window.set_default(start)
    window.set_escape(close)
    return window.ask() is start


def tell_macos_downloaded(parent: QWidget | None, version: str) -> None:
    """macOS: the new app couldn't replace the old one by itself; the .dmg is open in Finder for the user."""
    tell(
        parent,
        tr("Update"),
        tr(
            "{name} {version} is downloaded and open in Finder. To finish, drag {name} onto Applications there, "
            "replacing the old one, then start it again.",
            name=APP_NAME,
            version=version,
        ),
    )
