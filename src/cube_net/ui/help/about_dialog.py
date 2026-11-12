# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Help -> About: the application's name, version and build, and who made it for what."""

import platform

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from cube_net import __version__, __version_date__
from cube_net.ui.dialogs.small_window import SmallWindow
from cube_net.ui.i18n import tr

APP_NAME = "Cube Net"

# The build's lines are quieter than the rest, but still easy to read.
BUILD_TEXT = "#5F6368"

# The puzzle the application was made for.
PUZZLE_URL = "https://ru.braigam.com/?path=comments&puzzle=680"

# The credits, with "this puzzle" where the link goes.
CREDITS = "by UNDEFEAT in attempts to solve {puzzle}"

# Who holds the copyright, and since when.
COPYRIGHT = "Copyright © 2026 Viktor Podust <undefeatvip@gmail.com>"

# The license (the GNU GPL v3 or any later version), with its name where the link to it goes.
LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.html"
LICENSE_NAME = "GNU GPL v3 or later"
LICENSE_TEXT = "Free software under the {license}, with ABSOLUTELY NO WARRANTY"

# Where the source code is (the GPL's promise to whoever has the program).
SOURCE_URL = "https://github.com/Avorthoren/cube-net"
SOURCE_TEXT = "Source code: {source}"


def build_info() -> str:
    """What the application runs on: Python, Qt and the system."""
    return (
        f"Python {platform.python_version()}, Qt {QT_VERSION_STR} (PyQt {PYQT_VERSION_STR})\n"
        f"{platform.system()} {platform.release()} ({platform.machine()})"
    )


class AboutDialog(SmallWindow):
    """Closed with Escape or its close button. All its text can be selected and copied, or copied at once."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("About {name}", name=APP_NAME), parent)
        self.name = QLabel(APP_NAME, self)
        font = QFont(self.name.font())
        font.setPointSizeF(font.pointSizeF() * 1.8)
        font.setBold(True)
        self.name.setFont(font)
        self.version = QLabel(tr("Version {version}, {date}", version=__version__, date=__version_date__), self)
        self.build = QLabel(build_info(), self)
        self.build.setStyleSheet(f"color: {BUILD_TEXT};")
        link = f'<a href="{PUZZLE_URL}">{tr("this puzzle")}</a>'
        self.credits = QLabel(tr(CREDITS, puzzle=link), self)
        self.credits.setTextFormat(Qt.TextFormat.RichText)
        self.credits.setOpenExternalLinks(True)  # the link opens in the browser
        selectable = Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        for label in (self.name, self.version, self.build):
            label.setTextInteractionFlags(selectable)  # so that the user can copy any of it
        # The link stays a link (with "Copy link location" in its context menu), and the text around it selectable.
        self.credits.setTextInteractionFlags(selectable | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        # The notices of the GPL: who holds the copyright, that there's no warranty, the license and the source.
        self.copyright = QLabel(tr(COPYRIGHT), self)
        self.copyright.setTextFormat(Qt.TextFormat.PlainText)  # the e-mail's <> aren't a tag
        self.copyright.setTextInteractionFlags(selectable)
        license_link = f'<a href="{LICENSE_URL}">{tr(LICENSE_NAME)}</a>'
        self.license = _link_label(tr(LICENSE_TEXT, license=license_link), self)
        source_link = f'<a href="{SOURCE_URL}">{SOURCE_URL.removeprefix("https://")}</a>'
        self.source = _link_label(tr(SOURCE_TEXT, source=source_link), self)
        self.copy_button = QPushButton(tr("Copy and close"), self)
        self.copy_button.setAutoDefault(False)  # Enter in the text doesn't press it
        self.copy_button.clicked.connect(self._copy_and_close)
        content = QVBoxLayout()
        content.setContentsMargins(24, 16, 24, 16)
        content.setSpacing(6)
        for label in (self.name, self.version, self.build, self.credits):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content.addWidget(label)
        content.insertSpacing(3, 10)
        content.addSpacing(10)
        for label in (self.copyright, self.license, self.source):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content.addWidget(label)
        content.addSpacing(10)
        content.addWidget(self.copy_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.body.addLayout(content)
        self.setFixedSize(self.sizeHint())

    def text(self) -> str:
        """All of it as plain text, a line per line, with the links themselves instead of "this puzzle" and the
        license's name (that one with the link after it)."""
        return "\n".join(
            [
                APP_NAME,
                self.version.text(),
                *build_info().split("\n"),
                tr(CREDITS, puzzle=PUZZLE_URL),
                tr(COPYRIGHT),
                tr(LICENSE_TEXT, license=f"{tr(LICENSE_NAME)} ({LICENSE_URL})"),
                tr(SOURCE_TEXT, source=SOURCE_URL),
            ]
        )

    def _copy_and_close(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.text())
        self.accept()


def _link_label(text: str, parent: QWidget) -> QLabel:
    """Rich text with a link that opens in the browser (and keeps "Copy link location"); the rest selectable."""
    label = QLabel(text, parent)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setOpenExternalLinks(True)
    label.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard
        | Qt.TextInteractionFlag.LinksAccessibleByMouse
    )
    return label
