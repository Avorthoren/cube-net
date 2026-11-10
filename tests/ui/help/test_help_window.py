from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

from cube_net.ui.help.help_window import HelpWindow
from cube_net.ui.i18n import TRANSLATIONS, Language


def make(qtbot: QtBot) -> HelpWindow:
    window = HelpWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def texts(window: HelpWindow) -> str:
    """Everything it says, with its markup."""
    labels = [label.text() for label in window.findChildren(QLabel)]
    return "\n".join([*labels, *(block.toHtml() for block in window.blocks)])


def test_four_animations_and_the_text(qtbot: QtBot) -> None:
    window = make(qtbot)
    assert window.windowTitle() == "Cube Net Help"
    assert len(window.players) == 4
    all_text = texts(window)
    assert "6 square units" in all_text
    assert "Bounds" in window.blocks[-1].toPlainText()  # the button's own name
    assert len(window.blocks) == 4  # the text between the animations


def test_in_russian_too(qtbot: QtBot) -> None:
    window = make(qtbot)
    TRANSLATIONS.set_language(Language.RUSSIAN)
    assert window.windowTitle() == "Cube Net — справка"
    assert "Рамка" in window.blocks[-1].toPlainText()
    assert "Сделайте разрез" in window.blocks[0].toPlainText()


def test_escape_closes_it(qtbot: QtBot) -> None:
    window = make(qtbot)
    qtbot.keyClick(window, Qt.Key.Key_Escape)
    assert not window.isVisible()


def test_restyle_reaches_every_animation(qtbot: QtBot) -> None:
    window = make(qtbot)
    seen: list[object] = []
    for player in window.players:
        player.sheet.restyle = lambda p=player: seen.append(p)  # type: ignore[method-assign]
    window.restyle()
    assert seen == window.players


def test_text_can_be_selected_across_paragraphs(qtbot: QtBot) -> None:
    window = make(qtbot)
    block = window.blocks[0]
    assert block.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
    block.selectAll()
    selected = block.textCursor().selectedText()
    assert "Cube Net" in selected and "6 square units" in selected and "Make a cut" in selected


def test_the_wheel_is_left_to_the_page_over_text_and_animations(qtbot: QtBot) -> None:
    """A real wheel event that a widget leaves alone goes on to the widgets around it, up to the page's scroll area
    (Qt passes on only real ones, so a test can only check that it's left alone)."""
    from PyQt6.QtCore import QPoint, QPointF
    from PyQt6.QtGui import QWheelEvent
    from PyQt6.QtWidgets import QApplication

    window = make(qtbot)
    player = window.players[0]
    scale = player.sheet.view.scale_factor()
    for widget in (window.blocks[0].viewport(), player.sheet.view.viewport(), player.sheet, player):
        assert widget is not None
        pos = QPointF(widget.width() / 2, widget.height() / 2)
        event = QWheelEvent(
            pos,
            QPointF(widget.mapToGlobal(pos)),
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.sendEvent(widget, event)
        assert not event.isAccepted(), widget
    assert player.sheet.view.scale_factor() == scale  # no zooming there


def test_labels_follow_the_setting(qtbot: QtBot) -> None:
    window = HelpWindow(labels=True)
    qtbot.addWidget(window)
    item = window.players[0].sheet.view.net_item()
    assert item is not None and item.labels() is not None
    window.set_labels_shown(False)
    assert item.labels() is None
