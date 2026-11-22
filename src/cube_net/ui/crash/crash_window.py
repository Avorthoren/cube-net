# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The windows of the reports (`ReportWindow`): where the report is, that the author can be contacted with it, and
how (e-mail, a GitHub issue). The path and the e-mail can be selected and copied; Open folder shows the report in the
system's file manager and keeps the window.

- `CrashWindow`: an unexpected error, just before the application closes (Close application: also Enter, Escape and
  the title bar's close button).
- `ErrorReportWindow`: an action refused because it would have corrupted the project (a bug): the application goes on
  (OK).
"""

from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialogButtonBox, QPushButton, QWidget

from cube_net.ui.dialogs.message_window import MessageIcon, MessageWindow
from cube_net.ui.help.about_dialog import AUTHOR_EMAIL, ISSUES_URL
from cube_net.ui.i18n import tr

# The title (the application's name: it may be all that's left of it).
TITLE = "Cube Net"

# That the author can be contacted.
CONTACT_TEXT = "You can contact the author of this app, providing this report and some context about how this happened."

# The text's widest (px): a long path is on one line, as far as it fits.
MAX_TEXT_PX = 760


# An action refused by a safety net: it would have corrupted the project.
REFUSED_TEXT = (
    "Application encountered an unexpected error and refused your action, because it would corrupt the project."
)


def crash_text(path: Path | None) -> str:
    """The message (rich text): the report's path, on a line of its own, or that it couldn't be saved."""
    if path is None:
        return "<br>".join(
            [
                tr("An unexpected error occurred, and the application has to close."),
                tr("Crash report couldn't be saved."),
            ]
        )
    return "<br>".join(
        [
            tr("An unexpected error occurred, and the application has to close. Crash report saved to:"),
            escape(str(path)),
            tr(CONTACT_TEXT),
        ]
    )


def error_text(path: Path | None) -> str:
    """The message of a refused action (rich text): the report's path, on a line of its own, or that it couldn't be
    saved."""
    if path is None:
        return "<br>".join([tr(REFUSED_TEXT), tr("Error report couldn't be saved.")])
    return "<br>".join(
        [
            tr(
                "Application encountered an unexpected error and refused your action, because it would corrupt the "
                "project. Error report saved to:"
            ),
            escape(str(path)),
            tr(CONTACT_TEXT),
        ]
    )


def contacts_text() -> str:
    """The author's contacts (rich text): the e-mail, and a link to the GitHub issues."""
    issue = f'<a href="{ISSUES_URL}">{tr("GitHub issue")}</a>'
    return "<br>".join([tr("Contacts:"), AUTHOR_EMAIL, issue])


class ReportWindow(MessageWindow):
    def __init__(
        self, text: str, path: Path | None, icon: MessageIcon, close_text: str | None, parent: QWidget | None = None
    ) -> None:
        """`text`: the message (rich text); `path`: the report (None: it couldn't be saved; there are no contacts and no
        folder to open then); `close_text`: the closing button's text (None: Qt's OK)."""
        super().__init__(TITLE, text, contacts_text() if path is not None else "", icon, parent)
        self._path = path
        self.text_label.setTextFormat(Qt.TextFormat.RichText)
        widest = self.text_label.fontMetrics().horizontalAdvance(str(path)) + 2 if path is not None else 0
        self.text_label.setMaximumWidth(min(MAX_TEXT_PX, max(self.text_label.maximumWidth(), widest)))
        self.text_label.setMinimumWidth(min(MAX_TEXT_PX, max(self.text_label.minimumWidth(), widest)))
        self.details_label.setTextFormat(Qt.TextFormat.RichText)
        self.details_label.setOpenExternalLinks(True)
        self.details_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.open_folder_button: QPushButton | None = None
        if path is not None:
            self.open_folder_button = self.add(tr("Open folder"), QDialogButtonBox.ButtonRole.ActionRole)
        if close_text is None:
            self.close_button = self.add_standard(QDialogButtonBox.StandardButton.Ok)
        else:
            self.close_button = self.add(close_text, QDialogButtonBox.ButtonRole.AcceptRole)
        self.set_default(self.close_button)
        self.set_escape(self.close_button)

    def _on_clicked(self, button: object) -> None:
        if button is not None and button is self.open_folder_button:
            self.open_folder()  # the window stays
            return
        super()._on_clicked(button)

    def open_folder(self) -> bool:
        """Show the report's folder in the system's file manager; whether that worked."""
        return self._path is not None and QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._path.parent)))


class CrashWindow(ReportWindow):
    def __init__(self, path: Path | None, parent: QWidget | None = None) -> None:
        super().__init__(crash_text(path), path, MessageIcon.ERROR, tr("Close application"), parent)


class ErrorReportWindow(ReportWindow):
    def __init__(self, path: Path | None, parent: QWidget | None = None) -> None:
        super().__init__(error_text(path), path, MessageIcon.WARNING, None, parent)


def show_crash_window(path: Path | None) -> None:
    """Tell the user about the crash (`CrashWindow`), and wait until they close it."""
    CrashWindow(path).ask()


def show_error_report_window(path: Path | None, parent: QWidget | None = None) -> None:
    """Tell the user about the refused action (`ErrorReportWindow`), and wait until they close it."""
    ErrorReportWindow(path, parent).ask()
