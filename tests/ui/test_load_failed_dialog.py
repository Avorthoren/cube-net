from collections.abc import Callable

from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.load_failed_dialog import AfterLoadFailed, ask_after_load_failed


def answering(act: Callable[[QMessageBox], None]) -> None:
    """Once the question is up, do this to it."""

    def answer() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, QMessageBox)
        act(box)

    QTimer.singleShot(0, answer)


def click_button(text: str) -> Callable[[QMessageBox], None]:
    def click(box: QMessageBox) -> None:
        next(button for button in box.buttons() if button.text() == text).click()

    return click


def test_new_project(qtbot: QtBot) -> None:
    answering(click_button("New project"))
    assert ask_after_load_failed(None, "Oops.") is AfterLoadFailed.NEW_PROJECT


def test_open_another(qtbot: QtBot) -> None:
    answering(click_button("Open..."))
    assert ask_after_load_failed(None, "Oops.") is AfterLoadFailed.OPEN_ANOTHER


def test_closing_it_means_a_new_project(qtbot: QtBot) -> None:
    answering(lambda box: box.close())
    assert ask_after_load_failed(None, "Oops.") is AfterLoadFailed.NEW_PROJECT


def test_escape_means_a_new_project(qtbot: QtBot) -> None:
    answering(lambda box: qtbot.keyClick(box, Qt.Key.Key_Escape))
    assert ask_after_load_failed(None, "Oops.") is AfterLoadFailed.NEW_PROJECT


def test_it_tells_why(qtbot: QtBot) -> None:
    seen: list[str] = []

    def look(box: QMessageBox) -> None:
        seen.append(box.text())
        click_button("New project")(box)

    answering(look)
    ask_after_load_failed(None, "Can't open cube.cubenet: it is damaged.")
    assert seen == ["Can't open cube.cubenet: it is damaged."]


def test_it_does_not_stay_behind(qtbot: QtBot) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    answering(click_button("New project"))
    ask_after_load_failed(parent, "Oops.")
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert parent.findChildren(QMessageBox) == []
