from collections.abc import Callable

from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.preferences_dialog import PreferencesDialog, ask_max_zoom


def answering(act: Callable[[PreferencesDialog], None]) -> None:
    def answer() -> None:
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, PreferencesDialog)
        act(dialog)

    QTimer.singleShot(0, answer)


def press(button: QDialogButtonBox.StandardButton) -> Callable[[PreferencesDialog], None]:
    def click(dialog: PreferencesDialog) -> None:
        found = dialog.buttons.button(button)
        assert found is not None
        found.click()

    return click


def type_value(qtbot: QtBot, dialog: PreferencesDialog, text: str) -> None:
    line = dialog.max_zoom.lineEdit()
    assert line is not None
    line.selectAll()
    qtbot.keyClicks(line, text)
    dialog.max_zoom.interpretText()


def test_it_shows_the_current_value(qtbot: QtBot) -> None:
    d = PreferencesDialog(1234)
    qtbot.addWidget(d)
    assert d.max_zoom.value() == 1234


def test_ok_gives_the_new_value(qtbot: QtBot) -> None:
    def act(dialog: PreferencesDialog) -> None:
        type_value(qtbot, dialog, "2500")
        press(QDialogButtonBox.StandardButton.Ok)(dialog)

    answering(act)
    assert ask_max_zoom(None, 1000) == 2500


def test_values_stay_in_range(qtbot: QtBot) -> None:
    d = PreferencesDialog(1000)
    qtbot.addWidget(d)
    for text in ("100", "99999"):
        type_value(qtbot, d, text)
        assert 500 <= d.max_zoom.value() <= 10000


def test_cancel_and_escape_give_nothing(qtbot: QtBot) -> None:
    answering(press(QDialogButtonBox.StandardButton.Cancel))
    assert ask_max_zoom(None, 1000) is None
    answering(lambda dialog: qtbot.keyClick(dialog, Qt.Key.Key_Escape))
    assert ask_max_zoom(None, 1000) is None


def test_it_does_not_stay_behind(qtbot: QtBot) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    answering(press(QDialogButtonBox.StandardButton.Cancel))
    ask_max_zoom(parent, 1000)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert parent.findChildren(PreferencesDialog) == []
