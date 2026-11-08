from collections.abc import Callable
from fractions import Fraction as F

import pytest
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QWidget
from pytestqt.qtbot import QtBot

from cube_net.core.project_settings import DEFAULT_AREA_THRESHOLD, MAX_AREA_THRESHOLD, ProjectSettings
from cube_net.ui.project_settings_dialog import ProjectSettingsDialog, ask_project_settings


@pytest.fixture
def dialog(qtbot: QtBot) -> ProjectSettingsDialog:
    d = ProjectSettingsDialog(ProjectSettings())
    qtbot.addWidget(d)
    return d


def type_threshold(qtbot: QtBot, dialog: ProjectSettingsDialog, text: str) -> None:
    line = dialog.threshold.lineEdit()
    assert line is not None
    line.selectAll()
    qtbot.keyClicks(line, text)
    dialog.threshold.interpretText()


def test_it_shows_the_current_value(qtbot: QtBot) -> None:
    d = ProjectSettingsDialog(ProjectSettings(F(5432, 1000)))
    qtbot.addWidget(d)
    assert d.threshold.text() == "5.432"
    assert d.settings() == ProjectSettings(F(5432, 1000))


def test_the_default_comes_back_exact(dialog: ProjectSettingsDialog) -> None:
    assert dialog.threshold.text() == "7.100"
    assert dialog.settings().area_threshold == DEFAULT_AREA_THRESHOLD


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("6.789", F(6789, 1000)),
        ("7", F(7)),
        ("0.001", F(1, 1000)),
        ("12", MAX_AREA_THRESHOLD),
    ],
)
def test_typed_values_are_exact(qtbot: QtBot, dialog: ProjectSettingsDialog, text: str, expected: F) -> None:
    type_threshold(qtbot, dialog, text)
    assert dialog.settings().area_threshold == expected


@pytest.mark.parametrize("text", ["99", "12.5", "abc", "-5", "7.12345"])
def test_invalid_values_cannot_get_through(qtbot: QtBot, dialog: ProjectSettingsDialog, text: str) -> None:
    """Whatever is typed, what comes out is a valid setting (`ProjectSettings` would refuse anything else)."""
    type_threshold(qtbot, dialog, text)
    threshold = dialog.settings().area_threshold
    assert 0 < threshold <= MAX_AREA_THRESHOLD
    assert (threshold * 1000).denominator == 1


def test_every_value_it_can_show_is_exact(dialog: ProjectSettingsDialog) -> None:
    for thousandths in range(1, 12001, 37):
        dialog.threshold.setValue(thousandths / 1000)
        assert dialog.settings().area_threshold == F(thousandths, 1000)


def answering(act: Callable[[ProjectSettingsDialog], None]) -> None:
    def answer() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, ProjectSettingsDialog)
        act(box)

    QTimer.singleShot(0, answer)


def press(button: QDialogButtonBox.StandardButton) -> Callable[[ProjectSettingsDialog], None]:
    def click(dialog: ProjectSettingsDialog) -> None:
        found = dialog.buttons.button(button)
        assert found is not None
        found.click()

    return click


def test_ok_gives_the_new_settings(qtbot: QtBot) -> None:
    def act(dialog: ProjectSettingsDialog) -> None:
        type_threshold(qtbot, dialog, "6.5")
        press(QDialogButtonBox.StandardButton.Ok)(dialog)

    answering(act)
    assert ask_project_settings(None, ProjectSettings()) == ProjectSettings(F(13, 2))


def test_enter_is_ok(qtbot: QtBot) -> None:
    def act(dialog: ProjectSettingsDialog) -> None:
        type_threshold(qtbot, dialog, "6.5")
        line = dialog.threshold.lineEdit()
        assert line is not None
        qtbot.keyClick(line, Qt.Key.Key_Return)

    answering(act)
    assert ask_project_settings(None, ProjectSettings()) == ProjectSettings(F(13, 2))


def test_cancel_gives_nothing(qtbot: QtBot) -> None:
    def act(dialog: ProjectSettingsDialog) -> None:
        type_threshold(qtbot, dialog, "6.5")
        press(QDialogButtonBox.StandardButton.Cancel)(dialog)

    answering(act)
    assert ask_project_settings(None, ProjectSettings()) is None


def test_escape_gives_nothing(qtbot: QtBot) -> None:
    answering(lambda dialog: qtbot.keyClick(dialog, Qt.Key.Key_Escape))
    assert ask_project_settings(None, ProjectSettings()) is None


def test_it_does_not_stay_behind(qtbot: QtBot) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    answering(press(QDialogButtonBox.StandardButton.Cancel))
    ask_project_settings(parent, ProjectSettings())
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert parent.findChildren(ProjectSettingsDialog) == []
