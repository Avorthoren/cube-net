# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from cube_net import __version__, __version_date__
from cube_net.ui.help.about_dialog import PUZZLE_URL, AboutDialog, build_info


def make(qtbot: QtBot) -> AboutDialog:
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    return dialog


def test_name_version_build(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    assert dialog.name.text() == "Cube Net"
    # The package's version and date, whatever they are (a release sets them).
    assert dialog.version.text() == f"Version {__version__}, {__version_date__}"
    assert "Python" in dialog.build.text() and "Qt" in dialog.build.text()
    assert dialog.build.text() == build_info()


def test_credits_with_a_link_to_the_puzzle(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    text = dialog.credits.text()
    assert text.startswith("by UNDEFEAT in attempts to solve ")
    assert f'<a href="{PUZZLE_URL}">this puzzle</a>' in text
    assert PUZZLE_URL == "https://ru.braigam.com/?path=comments&puzzle=680"
    assert dialog.credits.openExternalLinks()


def test_escape_closes_it(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    qtbot.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()


def test_its_own_title_bar_and_no_other(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint  # no buttons from the window manager
    assert dialog.title_bar.title.text() == "About Cube Net"
    dialog.title_bar.close_button.click()
    assert not dialog.isVisible()


def test_all_text_can_be_selected(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    for label in (dialog.name, dialog.version, dialog.build, dialog.credits, dialog.copyright, dialog.license):
        assert label.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse


def test_the_link_is_still_a_link(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    assert dialog.credits.textInteractionFlags() & Qt.TextInteractionFlag.LinksAccessibleByMouse
    assert dialog.credits.openExternalLinks()


def test_selected_text_can_be_copied(qtbot: QtBot) -> None:
    from PyQt6.QtWidgets import QApplication

    dialog = make(qtbot)
    dialog.version.setSelection(0, len(dialog.version.text()))
    assert dialog.version.selectedText() == f"Version {__version__}, {__version_date__}"
    dialog.version.setFocus()
    qtbot.keyClick(dialog.version, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    clipboard = QApplication.clipboard()
    assert clipboard is not None and clipboard.text() == f"Version {__version__}, {__version_date__}"


class TestCopyAndClose:
    def test_the_button_is_at_the_bottom(self, qtbot: QtBot) -> None:
        dialog = make(qtbot)
        assert dialog.copy_button.text() == "Copy and close"
        assert dialog.copy_button.geometry().top() > dialog.credits.geometry().bottom()

    def test_copies_every_line_with_the_link_itself(self, qtbot: QtBot) -> None:
        from PyQt6.QtWidgets import QApplication

        from cube_net.ui.help.about_dialog import build_info

        dialog = make(qtbot)
        dialog.copy_button.click()
        clipboard = QApplication.clipboard()
        assert clipboard is not None
        assert clipboard.text().split("\n") == [
            "Cube Net",
            f"Version {__version__}, {__version_date__}",
            *build_info().split("\n"),
            f"by UNDEFEAT in attempts to solve {PUZZLE_URL}",
            "Copyright © 2026 Viktor Podust",
            "Free software under the GNU GPL v3 or later (https://www.gnu.org/licenses/gpl-3.0.html), with ABSOLUTELY "
            "NO WARRANTY",
            "Source code: https://github.com/Avorthoren/cube-net",
        ]
        assert "this puzzle" not in clipboard.text()

    def test_and_closes(self, qtbot: QtBot) -> None:
        dialog = make(qtbot)
        dialog.copy_button.click()
        assert not dialog.isVisible()


def test_the_notices_of_the_gpl(qtbot: QtBot) -> None:
    from cube_net.ui.help.about_dialog import LICENSE_URL, SOURCE_URL

    dialog = make(qtbot)
    assert dialog.copyright.text() == "Copyright © 2026 Viktor Podust"
    assert "ABSOLUTELY NO WARRANTY" in dialog.license.text()
    assert f'<a href="{LICENSE_URL}">GNU GPL v3 or later</a>' in dialog.license.text()
    assert f'<a href="{SOURCE_URL}">github.com/Avorthoren/cube-net</a>' in dialog.source.text()
    for label in (dialog.license, dialog.source):
        assert label.openExternalLinks()
        assert label.textInteractionFlags() & Qt.TextInteractionFlag.LinksAccessibleByMouse
    assert dialog.copy_button.geometry().top() > dialog.source.geometry().bottom()
