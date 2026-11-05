from pytestqt.qtbot import QtBot

from cube_net.ui.main_window import APP_TITLE, MainWindow


def test_main_window_opens(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    assert window.windowTitle() == APP_TITLE
    assert window.statusBar() is not None
