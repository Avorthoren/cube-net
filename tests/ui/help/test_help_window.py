# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from itertools import pairwise

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel
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


def test_five_animations_and_the_text(qtbot: QtBot) -> None:
    window = make(qtbot)
    assert window.windowTitle() == "Cube Net Help"
    assert len(window.network_players) == 5 and len(window.template_players) == 4
    assert window.players == [*window.network_players, *window.template_players]
    all_text = texts(window)
    assert "surface area of the body" in all_text
    assert "Bounds" in window.blocks[-1].toPlainText()  # the button's own name
    assert len(window.blocks) == 5  # the text between the animations
    advanced = window.blocks[-2].toPlainText()
    assert "Advanced features" in advanced and "assigning desired coordinates" in advanced


def test_in_russian_too(qtbot: QtBot) -> None:
    window = make(qtbot)
    TRANSLATIONS.set_language(Language.RUSSIAN)
    assert window.windowTitle() == "Cube Net — справка"
    assert "Рамка" in window.blocks[-1].toPlainText()
    assert "Сделайте разрез" in window.blocks[0].toPlainText()
    assert "Расширенные возможности" in window.blocks[-2].toPlainText()


def test_escape_closes_it(qtbot: QtBot) -> None:
    window = make(qtbot)
    qtbot.keyClick(window, Qt.Key.Key_Escape)
    assert not window.isVisible()


def test_the_steps_animations_have_the_built_in_cubes_look(qtbot: QtBot) -> None:
    """Whatever is open (another style, another body, a template), Help's animations look the same."""
    from cube_net.ui.style import DEFAULT_CUBE_LOOK

    window = make(qtbot)
    steps = window.network_players[:-1]
    assert all(player.sheet.view.look() == DEFAULT_CUBE_LOOK for player in steps)
    assert all(player.sheet.coordinates_hint is None for player in steps)


def test_advanced_features_on_the_torus_with_the_coordinates_hint(qtbot: QtBot) -> None:
    from cube_net.ui.help.demo.torus import torus_project

    window = make(qtbot)
    sheet = window.network_players[-1].sheet
    project = torus_project()
    look = sheet.view.look()
    assert look is not None and (look.style, look.face_colors) == (project.settings.style, project.settings.face_colors)
    assert sheet.workspace.editor.net is project.state.net
    assert sheet.coordinates_hint is not None


def test_text_can_be_selected_across_paragraphs(qtbot: QtBot) -> None:
    window = make(qtbot)
    block = window.blocks[0]
    assert block.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
    block.selectAll()
    selected = block.textCursor().selectedText()
    assert "Cube Net" in selected and "surface area of the body" in selected and "Make a cut" in selected


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


def test_no_vertex_labels_in_the_network_animations(qtbot: QtBot) -> None:
    window = make(qtbot)
    items = [player.sheet.view.net_item() for player in window.network_players]
    assert items and all(item is not None and item.labels() is None for item in items)


def test_good_to_know_undo_the_rectangle_and_the_view(qtbot: QtBot) -> None:
    from cube_net.ui.help.help_window import HOTKEYS_TITLE, MORE_TITLE, UNDO_TEXT, VIEW_TEXT

    text = make(qtbot).blocks[-1].toPlainText()
    after_title = text[text.index(MORE_TITLE) + len(MORE_TITLE) :].lstrip()
    assert after_title.startswith("•") and after_title[1:].lstrip().startswith(UNDO_TEXT)
    assert text.index(UNDO_TEXT) < text.index("exact area value") < text.index(VIEW_TEXT)
    assert "right-click" not in text  # it's in Advanced features now
    assert "Hold Shift while cutting" not in text
    assert HOTKEYS_TITLE not in text  # the hotkeys have a tab of their own
    assert text.rstrip().endswith(VIEW_TEXT)  # Good to know is the Network tab's end


def test_the_hotkeys_by_group_on_their_tab(qtbot: QtBot) -> None:
    from cube_net.ui.help.help_tab import HelpTab
    from cube_net.ui.help.help_window import HOTKEYS_TITLE
    from cube_net.ui.help.hotkeys import HOTKEYS

    window = make(qtbot)
    [block] = window.hotkey_blocks
    assert window.pages[HelpTab.HOTKEYS].isAncestorOf(block)
    text = block.toPlainText()
    hotkeys = text[text.index(HOTKEYS_TITLE) :]
    for group in HOTKEYS:
        assert group.title in hotkeys
        for hotkey in group.hotkeys:
            assert hotkey.shown() in hotkeys and hotkey.action in hotkeys
    assert "Shift + drag a vertex" in hotkeys and "hold Shift" in hotkeys and "right-click" in hotkeys
    assert "Making a template" in hotkeys


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


def test_three_tabs_down_the_left_side(qtbot: QtBot) -> None:
    from PyQt6.QtWidgets import QTabWidget

    from cube_net.ui.help.help_tab import HelpTab

    window = make(qtbot)
    assert window.tabs.tabPosition() is QTabWidget.TabPosition.West
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ["Network", "Template", "Hotkeys"]
    assert list(window.pages) == list(HelpTab)
    assert window.tab() is HelpTab.NETWORK and window.pages[HelpTab.NETWORK] is window.scroll
    assert all(window.pages[tab].parentWidget() is not None for tab in HelpTab)


def test_the_tabs_stay_where_they_are_while_a_page_scrolls(qtbot: QtBot) -> None:
    window = make(qtbot)
    bar = window.tabs.tabBar()
    assert bar is not None
    before = bar.mapTo(window, bar.rect().topLeft())
    window.scroll.verticalScrollBar().setValue(window.scroll.verticalScrollBar().maximum())
    assert bar.mapTo(window, bar.rect().topLeft()) == before
    assert not window.scroll.isAncestorOf(bar)


def test_every_tab_has_the_language_list(qtbot: QtBot) -> None:
    from cube_net.ui.help.help_tab import HelpTab

    window = make(qtbot)
    assert len(window.languages) == len(HelpTab) and window.language is window.languages[0]
    assert all(window.pages[tab].isAncestorOf(box) for tab, box in zip(HelpTab, window.languages, strict=True))
    chosen: list[object] = []
    window.language_changed.connect(chosen.append)
    window.languages[2].setCurrentIndex(list(Language).index(Language.RUSSIAN))
    assert chosen == [Language.RUSSIAN]


def template_text(window: HelpWindow) -> str:
    return "\n".join(block.toPlainText() for block in window.template_blocks)


def test_the_template_tab_tells_how_a_template_is_made_in_six_steps(qtbot: QtBot) -> None:
    from cube_net.core.geometry import MAX_NUMBER_DIGITS
    from cube_net.ui.help.help_tab import HelpTab
    from cube_net.ui.help.help_window import CHECK_FLAT, CHECKS_TITLE, REINDEX_TEXT, TEMPLATES_INTRO

    window = make(qtbot)
    page = window.pages[HelpTab.TEMPLATE]
    assert all(page.isAncestorOf(block) for block in window.template_blocks)
    assert all(page.isAncestorOf(player) for player in window.template_players)
    text = template_text(window)
    assert TEMPLATES_INTRO in text and f"up to {MAX_NUMBER_DIGITS} decimal digits" in text
    titles = [
        "Draw outer boundary loop",
        "Add fold-lines and inner loops",
        "Adjust it",
        "Define vertices and faces",
        "Validate it",
        "Advanced features",
        CHECKS_TITLE,
    ]
    assert [text.index(title) for title in titles] == sorted(text.index(title) for title in titles)
    assert text.index(CHECKS_TITLE) < text.index(CHECK_FLAT) < text.index(REINDEX_TEXT.split(":")[0])
    html = "".join(block.toHtml() for block in window.template_blocks)
    assert (
        "A1" in text and "vertical-align:sub" in html
    )  # the names' indices subscripts, as the application writes them


def test_the_example_of_a_template_that_isnt_a_body_names_its_points_with_indices(qtbot: QtBot) -> None:
    window = make(qtbot)
    assert "P2, N2, L2, I2 and P3" in template_text(window)  # (the plain text: the subscripts flattened)
    html = "".join(block.toHtml() for block in window.template_blocks)
    assert "P2, N2" not in html  # each index a subscript


def test_the_template_tab_in_russian(qtbot: QtBot) -> None:
    window = make(qtbot)
    TRANSLATIONS.set_language(Language.RUSSIAN)
    text = template_text(window)
    assert "Нарисуйте внешний контур границы" in text and "Точные шаги проверки" in text


def test_the_networks_links_go_to_their_sections_on_the_network_tab(qtbot: QtBot) -> None:
    from PyQt6.QtCore import QUrl

    from cube_net.ui.help.help_tab import HelpTab
    from cube_net.ui.help.help_window import ADJUST_SECTION, ADVANCED_SECTION, SECTION_SCHEME

    window = make(qtbot)
    links = [block for block in window.template_blocks if f'href="{SECTION_SCHEME}:' in block.toHtml()]
    assert len(links) == 2
    bar = window.pages[HelpTab.NETWORK].verticalScrollBar()
    assert bar is not None
    scrolled = []
    for section in (ADJUST_SECTION, ADVANCED_SECTION):
        window.show_tab(HelpTab.TEMPLATE)
        bar.setValue(0)
        window._follow_link(QUrl(f"{SECTION_SCHEME}:{section}"))
        assert window.tabs.currentWidget() is window.pages[HelpTab.NETWORK]
        scrolled.append(bar.value())
    assert 0 < scrolled[0] < scrolled[1]


def test_the_template_animations_show_the_template_with_its_labels(qtbot: QtBot) -> None:
    from cube_net.ui.template.template_tool import TemplateTool

    window = make(qtbot)
    assert all(isinstance(player.sheet.tool, TemplateTool) for player in window.template_players)


def test_opens_with_the_tab_asked_and_tells_when_another_is_chosen(qtbot: QtBot) -> None:
    from cube_net.ui.help.help_tab import HelpTab

    window = HelpWindow(tab=HelpTab.HOTKEYS)
    qtbot.addWidget(window)
    assert window.tab() is HelpTab.HOTKEYS
    shown: list[object] = []
    window.tab_changed.connect(shown.append)
    window.show_tab(HelpTab.TEMPLATE)
    assert shown == [HelpTab.TEMPLATE] and window.tab() is HelpTab.TEMPLATE


def test_the_tabs_in_russian(qtbot: QtBot) -> None:
    window = make(qtbot)
    TRANSLATIONS.set_language(Language.RUSSIAN)
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ["Развёртка", "Шаблон", "Горячие клавиши"]


def test_the_tabs_start_where_the_first_paragraph_does(qtbot: QtBot) -> None:
    from PyQt6.QtCore import QPoint

    window = make(qtbot)
    bar = window.tabs.tabBar()
    assert bar is not None
    top = window.first_paragraph_top()
    heading = window.blocks[0].document()
    assert heading is not None and top is not None
    assert top > 0 and bar.mapTo(window, QPoint(0, 0)).y() == top  # under "How it works"
    assert "How it works" in heading.findBlockByNumber(1).text()
    assert heading.findBlockByNumber(2).text().startswith("This application lets you build")


def test_the_tabs_follow_the_first_paragraph_when_the_page_is_laid_out_again(qtbot: QtBot) -> None:
    from PyQt6.QtCore import QPoint

    window = make(qtbot)
    bar = window.tabs.tabBar()
    column = window.blocks[0].parentWidget()
    assert bar is not None and column is not None and column.layout() is not None
    before = window.first_paragraph_top()
    assert before is not None
    column.layout().setContentsMargins(0, 28 + 40, 0, 40)  # type: ignore[union-attr]
    qtbot.waitUntil(lambda: window.first_paragraph_top() == before + 40)
    qtbot.waitUntil(lambda: bar.mapTo(window, QPoint(0, 0)).y() == before + 40)


def test_the_column_is_at_the_same_place_on_every_tab_scrolling_or_not(qtbot: QtBot) -> None:
    from PyQt6.QtCore import QPoint

    from cube_net.ui.help.help_tab import HelpTab

    window = make(qtbot)

    def lefts() -> set[int]:
        found = set()
        for tab, language in zip(HelpTab, window.languages, strict=True):
            window.show_tab(tab)
            QApplication.processEvents()
            column = language.parentWidget()
            assert column is not None
            found.add(column.mapTo(window, QPoint(0, 0)).x())
        return found

    assert window.pages[HelpTab.NETWORK].verticalScrollBar().isVisible()  # type: ignore[union-attr]
    assert not window.pages[HelpTab.TEMPLATE].verticalScrollBar().isVisible()  # type: ignore[union-attr]
    assert len(lefts()) == 1


def test_what_templates_are_for_is_one_paragraph_of_two_lines(qtbot: QtBot) -> None:
    from cube_net.ui.help.help_window import TEMPLATES_INTRO, TEMPLATES_USE

    document = make(qtbot).template_blocks[0].document()
    assert document is not None
    paragraph = document.find(TEMPLATES_INTRO).block()
    use = TEMPLATES_USE.format(create="Create\u00a0network")  # (kept on one line)
    assert paragraph.text() == f"{TEMPLATES_INTRO}\u2028{use}"  # (a line break inside one paragraph)


def test_every_line_of_a_paragraph_as_high_as_the_others_whatever_font_draws_its_characters(qtbot: QtBot) -> None:
    """An arrow ("→") comes from another font with taller lines, and would push its line apart from the others."""
    from cube_net.ui.help.help_window import TEMPLATES_INTRO, VERTICES_TEXT

    window = make(qtbot)
    pitches = set()
    for block in window.template_blocks:
        document = block.document()
        assert document is not None
        for text in (TEMPLATES_INTRO, VERTICES_TEXT.split("(")[0]):
            found = document.find(text)
            if found.isNull():
                continue
            lines = found.block().layout()
            assert lines is not None and lines.lineCount() >= 2
            ys = [lines.lineAt(i).y() for i in range(lines.lineCount())]
            pitches |= {round(b - a, 3) for a, b in pairwise(ys)}
    assert len(pitches) == 1


def test_bold_names_of_buttons_are_kept_on_one_line(qtbot: QtBot) -> None:
    window = make(qtbot)
    text = "".join(block.toHtml() for block in window.template_blocks)  # (plain text has plain spaces)
    assert "Assign\u00a0label" in text and "Assign label" not in text


def test_only_the_animations_that_click_its_buttons_have_the_instrument_panel(qtbot: QtBot) -> None:
    from cube_net.ui.help.demo.steps import DRAW_HOLE, VALIDATE

    window = make(qtbot)
    panels = [player.sheet.panel for player in window.template_players]
    assert [None if panel is None else list(panel.buttons) for panel in panels] == [
        None,
        [DRAW_HOLE, VALIDATE],
        None,
        [DRAW_HOLE, VALIDATE],
    ]
    assert all(player.sheet.panel is None for player in window.network_players)
