from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from cube_net.ui.help.small_window import SmallWindow


def make(qtbot: QtBot) -> SmallWindow:
    window = SmallWindow("Something")
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def test_no_frame_from_the_window_manager(qtbot: QtBot) -> None:
    """Its title bar would have minimize and maximize buttons that do nothing (Ubuntu's GNOME on X11)."""
    flags = make(qtbot).windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert not flags & Qt.WindowType.WindowMinimizeButtonHint
    assert not flags & Qt.WindowType.WindowMaximizeButtonHint


def test_title_in_the_middle_and_close_at_the_right(qtbot: QtBot) -> None:
    window = make(qtbot)
    bar = window.title_bar
    assert bar.title.text() == "Something" == window.windowTitle()
    assert bar.close_button.geometry().right() > bar.title.geometry().right()
    middle = bar.title.geometry().center().x()
    assert abs(middle - bar.width() / 2) <= 2


def test_close_button_and_escape_close_it(qtbot: QtBot) -> None:
    window = make(qtbot)
    window.title_bar.close_button.click()
    assert not window.isVisible()
    window = make(qtbot)
    qtbot.keyClick(window, Qt.Key.Key_Escape)
    assert not window.isVisible()


def test_dragging_the_title_bar_asks_the_window_manager_to_move_it(qtbot: QtBot, monkeypatch: object) -> None:
    from PyQt6.QtGui import QWindow

    window = make(qtbot)
    moves: list[bool] = []
    monkeypatch.setattr(QWindow, "startSystemMove", lambda self: moves.append(True) or True)  # type: ignore[attr-defined]
    qtbot.mousePress(window.title_bar, Qt.MouseButton.LeftButton)
    assert moves == [True]
