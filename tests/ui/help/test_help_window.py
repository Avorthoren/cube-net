# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

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


def test_every_animation_has_the_built_in_cubes_look(qtbot: QtBot) -> None:
    """Whatever is open (another style, another body, a template), Help's animations look the same."""
    from cube_net.ui.style import DEFAULT_CUBE_LOOK

    window = make(qtbot)
    assert window.players and all(player.sheet.view.look() == DEFAULT_CUBE_LOOK for player in window.players)


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


def test_no_vertex_labels_in_the_animations(qtbot: QtBot) -> None:
    window = make(qtbot)
    items = [player.sheet.view.net_item() for player in window.players]
    assert items and all(item is not None and item.labels() is None for item in items)


def test_good_to_know_starts_with_the_right_click_then_the_origin(qtbot: QtBot) -> None:
    from cube_net.ui.help.help_window import EXACT_TEXT, HOTKEYS_TITLE, MORE_TITLE, ORIGIN_TEXT, UNDO_TEXT

    text = make(qtbot).blocks[-1].toPlainText()
    after_title = text[text.index(MORE_TITLE) + len(MORE_TITLE) :].lstrip()
    assert after_title.lstrip("•  ").startswith(EXACT_TEXT)
    assert text.index(EXACT_TEXT) < text.index(ORIGIN_TEXT) < text.index(UNDO_TEXT)  # the origin's is the second
    assert "Hold Shift while cutting" not in text  # it's with the hotkeys now
    assert text.index(MORE_TITLE) < text.index(HOTKEYS_TITLE)  # the hotkeys come after it


def test_the_hotkeys_by_group(qtbot: QtBot) -> None:
    from cube_net.ui.help.help_window import HOTKEYS_TITLE
    from cube_net.ui.help.hotkeys import HOTKEYS

    text = make(qtbot).blocks[-1].toPlainText()
    for group in HOTKEYS:
        assert group.title in text
        for hotkey in group.hotkeys:
            assert hotkey.shown() in text and hotkey.action in text
    hotkeys = text[text.index(HOTKEYS_TITLE) :]
    assert "Shift + drag a vertex" in hotkeys and "hold Shift" in hotkeys
    assert "right-click" not in hotkeys  # Good to know tells about it


def test_the_language_list_by_the_name(qtbot: QtBot) -> None:
    window = make(qtbot)
    box = window.language
    assert box.currentData() is TRANSLATIONS.language and box.toolTip() == "Language"
    from cube_net.ui.help.help_window import LANGUAGE_GAP_PX

    block = window.blocks[0]
    document = block.document()
    assert document is not None
    name = document.firstBlock().layout()
    assert box.parent() is block and name is not None
    end = name.lineAt(0).naturalTextWidth()
    assert box.x() == round(end + LANGUAGE_GAP_PX)  # right after "Cube Net", where it's seen
    assert box.geometry().top() < 40  # on the name's line, above "How it works"
    chosen: list[Language] = []
    window.language_changed.connect(chosen.append)
    box.setCurrentIndex(list(Language).index(Language.RUSSIAN))
    assert chosen == [Language.RUSSIAN]


def test_the_wheel_over_the_language_list_scrolls_the_page(qtbot: QtBot) -> None:
    from PyQt6.QtCore import QPoint, QPointF
    from PyQt6.QtGui import QWheelEvent
    from PyQt6.QtWidgets import QApplication

    window = make(qtbot)
    box = window.language
    before = box.currentIndex()
    bar = window.scroll.verticalScrollBar()
    assert bar is not None
    pos = QPointF(box.width() / 2, box.height() / 2)
    down = QWheelEvent(
        pos,
        box.mapToGlobal(pos),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(box, down)
    assert box.currentIndex() == before and bar.value() > 0
