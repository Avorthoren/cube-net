from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from cube_net import __version__
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
    assert __version__ == "1.0"
    assert dialog.version.text() == "Version 1.0, 10.11.2026"
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
    for label in (dialog.name, dialog.version, dialog.build, dialog.credits):
        assert label.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse


def test_the_link_is_still_a_link(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    assert dialog.credits.textInteractionFlags() & Qt.TextInteractionFlag.LinksAccessibleByMouse
    assert dialog.credits.openExternalLinks()


def test_selected_text_can_be_copied(qtbot: QtBot) -> None:
    from PyQt6.QtWidgets import QApplication

    dialog = make(qtbot)
    dialog.version.setSelection(0, len(dialog.version.text()))
    assert dialog.version.selectedText() == "Version 1.0, 10.11.2026"
    dialog.version.setFocus()
    qtbot.keyClick(dialog.version, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    clipboard = QApplication.clipboard()
    assert clipboard is not None and clipboard.text() == "Version 1.0, 10.11.2026"


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
            "Version 1.0, 10.11.2026",
            *build_info().split("\n"),
            f"by UNDEFEAT in attempts to solve {PUZZLE_URL}",
        ]
        assert "this puzzle" not in clipboard.text()

    def test_and_closes(self, qtbot: QtBot) -> None:
        dialog = make(qtbot)
        dialog.copy_button.click()
        assert not dialog.isVisible()
