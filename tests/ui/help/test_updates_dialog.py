from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from pytestqt.qtbot import QtBot

from cube_net.ui.help.updates_dialog import CONE, UpdatesDialog


def make(qtbot: QtBot) -> UpdatesDialog:
    dialog = UpdatesDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    return dialog


def test_says_under_development(qtbot: QtBot) -> None:
    assert make(qtbot).text.text() == "Under development..."


def test_draws_a_cone(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    image = dialog.cone.grab().toImage()
    colours = {image.pixelColor(x, y).name() for x in range(image.width()) for y in range(image.height())}
    assert CONE.name() in colours
    assert QColor("#FFFFFF").name() in colours  # its stripes


def test_escape_closes_it(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    qtbot.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()


def test_its_own_title_bar_and_no_other(qtbot: QtBot) -> None:
    dialog = make(qtbot)
    assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert dialog.title_bar.title.text() == "Check for updates"
    dialog.title_bar.close_button.click()
    assert not dialog.isVisible()
