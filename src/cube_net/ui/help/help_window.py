# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Help -> Help: a big window that explains how the application works, with animations of the real tools.

Its tabs (`HelpTab`: Network, Template, Hotkeys) are down the left side, their titles turned; each tab's page scrolls on
its own, and the tabs stay where they are. Every page starts with the application's name and the language list.

The text is in a column of easy-to-read width, in blocks between the animations (`TextBlock`: selectable across
paragraphs). The animations (`demo`) are drawn in the built-in Cube's look (`DEFAULT_CUBE_LOOK`), whatever the open
document's style and colours are, and never with the vertex labels. Escape closes the window.
"""

from collections.abc import Callable, Sequence
from fractions import Fraction as F
from html import escape

from PyQt6.QtCore import QEvent, QObject, QPoint, QSize, QSizeF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QShowEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from cube_net.core.geometry import Box, Vec
from cube_net.core.project import Project
from cube_net.ui.help.about_dialog import APP_NAME
from cube_net.ui.help.demo import advanced, scenes
from cube_net.ui.help.demo.demo_sheet import AROUND_THE_NET
from cube_net.ui.help.demo.player import DemoPlayer
from cube_net.ui.help.demo.steps import Step
from cube_net.ui.help.demo.torus import torus_project
from cube_net.ui.help.help_tab import HelpTab
from cube_net.ui.help.hotkeys import HOTKEYS, HotkeyGroup
from cube_net.ui.help.text_block import ACCENT, BADGE_PX, BADGE_SCHEME, TextBlock
from cube_net.ui.i18n import TRANSLATIONS, bind, tr
from cube_net.ui.language_box import LanguageBox
from cube_net.ui.no_wheel import ignore_wheel

# The page and its text.
PAGE = "#FFFFFF"
TEXT = "#202124"
QUIET_TEXT = "#5F6368"

# The sizes of the text, against the usual one.
NAME_SIZE = 2.2
SUBTITLE_SIZE = 1.3
TITLE_SIZE = 1.45
PARAGRAPH_SIZE = 1.1

# The widths of the column of text and of the window around it (px).
COLUMN_PX = 880
WINDOW_PX = 1000

# The animations: the two of the first steps, and the pair side by side, which shows the rearranged halves too.
WIDE = QSize(640, 440)
HALF = QSize(428, 400)
AROUND_BOTH_RESULTS = Box(Vec(F(48, 5), F(43, 5)), Vec(F(77, 5), F(72, 5)))

INTRO = (
    "This application lets you build networks of solid bodies: polygons without self-intersections that, when folded, "
    "can cover the whole surface of that body without overlaps. So the area of such a polygon is always equal to the "
    "surface area of the body."
)
IDEA = (
    "If a network is cut into two pieces, they can be rearranged and glued together again along a pair of edges that "
    "meet on the body. That's exactly what the application is for:"
)
CUT_TITLE = "Make a cut"
CUT_TEXT = (
    "Click on any edge or vertex of the perimeter to start a cut: one or more segments joined end to end. A cut starts "
    "and ends on the perimeter, and all its other points must lie strictly inside the net, so it ends as soon as you "
    "click on the perimeter again."
)
ADJUST_TITLE = "Adjust it"
ADJUST_TEXT = (
    "Adjust the cut if needed: drag any of its vertices, click the circle in the middle of a segment to add a vertex "
    "there, or hold Ctrl and click a vertex to delete it."
)
GLUE_TITLE = "Glue the halves together"
GLUE_TEXT = (
    "Then click on a suitable edge of the perimeter to glue the other half of the net there. An edge is suitable if "
    "its counterpart, the edge it meets on the cube's surface when the net is folded, is in the other half: while you "
    "hover such an edge, its counterpart blinks. If the halves don't overlap after rearrangement, the cut can be "
    "approved; if they do, the button cancels it."
)
GOOD_CAPTION = "No overlaps: approved"
BAD_CAPTION = "Overlaps: cancelled"
ADVANCED_TITLE = "Advanced features"
ADVANCED_EXACT_TEXT = (
    "You can set specific coordinates for vertices or slopes for lines when creating or dragging vertices: try "
    "right-click."
)
ADVANCED_OUTSIDE_TEXT = (
    "Cut should always start on the boundary, but other vertices of the cut line can even be outside the net: as soon "
    "as net is divided into two pieces - cut line ends."
)
ADVANCED_ORIGIN_TEXT = (
    "You can also move the origin by assigning desired coordinates to any vertex. Although, axes orientation and the "
    "scale is constant."
)
MORE_TITLE = "Good to know"
UNDO_TEXT = "Undo and redo work for up to 1000 actions: use Ctrl+Z and Ctrl+Y."
BOUNDS_TEXT = (
    "The application keeps track of the minimum-area bounding rectangle of the net. To see the rectangle itself, "
    "press the {bounds} button on the instrument panel. You can see the exact area value by hovering the mouse "
    "over its approximate value."
)
VIEW_TEXT = "Zoom with the mouse wheel; drag the sheet to move it."
HOTKEYS_TITLE = "Hotkeys"

# The tabs' titles (the Hotkeys tab's is `HOTKEYS_TITLE`).
NETWORK_TAB = "Network"
TEMPLATE_TAB = "Template"

# The first paragraph's number in the Network page's first block of text (after the name and "How it works").
FIRST_PARAGRAPH = 2

# Room between the application's name at the top and the language list after it (px).
LANGUAGE_GAP_PX = 20

# The size of a group's title in the hotkeys, against the usual text's.
GROUP_SIZE = 1.15

# The width of the column of keys in the hotkeys (px).
KEYS_COLUMN_PX = 260


class HelpWindow(QWidget):
    # The user chose another language in the list at the top (a `Language`): it's the application's setting.
    language_changed = pyqtSignal(object)

    # The user went to another tab (a `HelpTab`).
    tab_changed = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None, tab: HelpTab = HelpTab.NETWORK) -> None:
        """`tab`: the one shown at first (the one the user looked at last)."""
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.Window)
        bind(self, self.setWindowTitle, "{name} Help", name=APP_NAME)
        self.players: list[DemoPlayer] = []
        # The Network tab's blocks of text (`TextBlock`), in order, and the Hotkeys tab's.
        self.blocks: list[TextBlock] = []
        self.hotkey_blocks: list[TextBlock] = []
        # Every tab's language list, and the block of the name it's placed after.
        self.languages: list[LanguageBox] = []
        self._language_places: list[tuple[LanguageBox, TextBlock]] = []
        self._blocks = self.blocks
        self._block: TextBlock | None = None
        self._column_widget = QWidget()
        self._column = QVBoxLayout(self._column_widget)
        self.tabs = QTabWidget(self)
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)  # down the left side, its texts turned
        self.tabs.setDocumentMode(True)
        # Each tab's page scrolls under the tabs, which stay where they are.
        self.pages: dict[HelpTab, QScrollArea] = {}

        self._start_page(self.blocks)
        self._paragraph(INTRO)
        self._paragraph(IDEA)
        self._title(CUT_TITLE, 1)
        self._paragraph(CUT_TEXT)
        self._players([self._player(scenes.CUT, [], WIDE)])
        self._title(ADJUST_TITLE, 2)
        self._paragraph(ADJUST_TEXT)
        self._players([self._player(scenes.ADJUST, [scenes.CUT], WIDE)])
        self._title(GLUE_TITLE, 3)
        self._paragraph(GLUE_TEXT)
        before = [scenes.CUT, scenes.ADJUST]
        good = self._player(scenes.GLUE_GOOD, before, HALF, AROUND_BOTH_RESULTS)
        bad = self._player(scenes.GLUE_BAD, before, HALF, AROUND_BOTH_RESULTS)
        self._players([good, bad], [self._caption(GOOD_CAPTION), self._caption(BAD_CAPTION)])
        self._title(ADVANCED_TITLE, 4)
        self._paragraph(ADVANCED_EXACT_TEXT)
        self._paragraph(ADVANCED_OUTSIDE_TEXT)
        self._paragraph(ADVANCED_ORIGIN_TEXT)
        self._players([self._player(advanced.ADVANCED, [], advanced.SIZE, advanced.SHOWN, torus_project(), True)])
        self._title(MORE_TITLE)
        self._paragraph(UNDO_TEXT, bullet=True)
        self._paragraph(BOUNDS_TEXT, lambda: {"bounds": f"<b>{tr('Bounds')}</b>"}, bullet=True)
        self._paragraph(VIEW_TEXT, bullet=True)
        self.scroll = self._finish_page(NETWORK_TAB, HelpTab.NETWORK)
        self.language = self.languages[0]
        # The tabs follow the first paragraph wherever the page's layout puts it (it's laid out after the window is
        # shown, and again when the fonts or the texts change).
        self._tabs_top: int | None = None
        self.blocks[0].installEventFilter(self)
        first_layout = self.blocks[0].document().documentLayout()  # type: ignore[union-attr]
        first_layout.documentSizeChanged.connect(self._on_first_text_resized)  # type: ignore[union-attr]
        self._start_page([])  # its content is to come
        self._finish_page(TEMPLATE_TAB, HelpTab.TEMPLATE)
        self._start_page(self.hotkey_blocks)
        self._title(HOTKEYS_TITLE)
        for group in HOTKEYS:
            self._hotkeys(group)
        self._finish_page(HOTKEYS_TITLE, HelpTab.HOTKEYS)
        TRANSLATIONS.changed.connect(self._place_languages)  # after the texts' own refresh: it's connected before

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)
        self.show_tab(tab)
        self.tabs.currentChanged.connect(lambda _index: self.tab_changed.emit(self.tab()))
        self.restore_default_size()

    def showEvent(self, a0: QShowEvent | None) -> None:
        super().showEvent(a0)
        self.align_tabs()
        QTimer.singleShot(0, self.align_tabs)  # once the page is laid out for the window's size

    def _on_first_text_resized(self, _size: QSizeF) -> None:
        self.align_tabs()  # (a method, not a lambda: Qt disconnects it when the window is gone)

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        """The first block of text moved or changed its size: the tabs follow its first paragraph."""
        if a1 is not None and a1.type() in (QEvent.Type.Move, QEvent.Type.Resize):
            self.align_tabs()
        return False

    def align_tabs(self) -> None:
        """The tabs start where the Network page's first paragraph does (its first line's top, under the name and "How
        it works"), as far as the page is from the window's top when it isn't scrolled."""
        top = self.first_paragraph_top()
        if top is not None and top != self._tabs_top:
            self._tabs_top = top
            self.tabs.setStyleSheet(f"QTabWidget::tab-bar {{ top: {top}px; }}")

    def first_paragraph_top(self) -> int | None:
        """Where the Network page's first paragraph's first line starts, from the page's top (px); None while its text
        is being set anew (not laid out)."""
        block = self.blocks[0]
        document = block.document()
        layout = document.documentLayout() if document is not None else None
        paragraph = document.findBlockByNumber(FIRST_PARAGRAPH) if document is not None else None
        lines = paragraph.layout() if paragraph is not None and paragraph.isValid() else None
        viewport = block.viewport()
        page = self.scroll.widget()
        if layout is None or lines is None or lines.lineCount() == 0 or viewport is None or page is None:
            return None
        top = layout.blockBoundingRect(paragraph).top() + lines.lineAt(0).y()
        return viewport.mapTo(page, QPoint(0, round(top))).y()

    def tab(self) -> HelpTab:
        """The tab shown."""
        return list(self.pages)[self.tabs.currentIndex()]

    def show_tab(self, tab: HelpTab) -> None:
        self.tabs.setCurrentIndex(list(self.pages).index(tab))

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is not None and event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    # --- the tabs ----------------------------------------------------------------------------------------------------

    def _start_page(self, blocks: list[TextBlock]) -> None:
        """A new tab's page is written from now on, its blocks of text into `blocks`: it starts with the application's
        name and the language list."""
        self._blocks = blocks
        self._block = None
        self._column_widget = column = QWidget()  # kept: nothing else holds it until its page does
        column.setFixedWidth(COLUMN_PX)
        self._column = QVBoxLayout(column)
        self._column.setContentsMargins(0, 28, 0, 40)
        self._column.setSpacing(14)
        self._heading()
        self._language_box()

    def _finish_page(self, title: str, tab: HelpTab) -> QScrollArea:
        """The page written since `_start_page`: centred, scrolled, in its tab (`title`: the tab's)."""
        column = self._column_widget
        self._column.addStretch(1)  # a short page stays at the top
        page = QWidget()
        page.setObjectName("page")
        page.setStyleSheet(f"#page {{ background: {PAGE}; }} QLabel {{ color: {TEXT}; }}")
        centred = QHBoxLayout(page)
        centred.addStretch(1)
        centred.addWidget(column)
        centred.addStretch(1)
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        index = self.tabs.addTab(scroll, "")
        bind(self.tabs, lambda text, i=index: self.tabs.setTabText(i, text), title)
        self.pages[tab] = scroll
        return scroll

    # --- the parts of the page ---------------------------------------------------------------------------------------

    def _text(self) -> TextBlock:
        """The block of text being written: a new one after an animation."""
        if self._block is None:
            self._block = TextBlock(COLUMN_PX)
            self._blocks.append(self._block)
            self._column.addWidget(self._block)
        return self._block

    def _heading(self) -> None:
        def html() -> str:
            name = _span(APP_NAME, NAME_SIZE, bold=True)
            subtitle = _span(tr("How it works"), SUBTITLE_SIZE, colour=QUIET_TEXT)
            return f'<p style="margin: 0 0 4px 0;">{name}</p><p style="margin: 0 0 16px 0;">{subtitle}</p>'

        self._text().add(html)

    def _language_box(self) -> None:
        """The language list, right after the application's name, where it's seen at once (over the text, which stays
        one document to select in): the same setting as Settings -> Preferences. Every tab has its own."""
        block = self._text()
        language = LanguageBox(TRANSLATIONS.language, block)
        bind(language, language.setToolTip, "Language")
        language.chosen.connect(self.language_changed)
        ignore_wheel([language], self)  # the wheel scrolls the page wherever the mouse is
        self.languages.append(language)
        self._language_places.append((language, block))
        _place_language(language, block)

    def _place_languages(self) -> None:
        for language, block in self._language_places:
            _place_language(language, block)
        self.align_tabs()  # the texts above the first paragraph may be of another height now

    def _paragraph(self, text: str, values: Callable[[], dict[str, str]] | None = None, bullet: bool = False) -> None:
        """A paragraph (an item of a list, if `bullet`); `values` gives what goes into its {placeholders}, in the
        current language."""

        def html() -> str:
            translated = tr(text)
            if values is not None:
                translated = translated.format(**values())
            return _paragraph_html(translated, bullet)

        self._text().add(html)

    def _title(self, text: str, number: int | None = None) -> None:
        """The title of a part of the page, with its step number if it's one of the steps."""

        def html() -> str:
            title = _span(tr(text), TITLE_SIZE, bold=True)
            if number is None:
                return f'<p style="margin: 22px 0 8px 0;">{title}</p>'
            picture = f'<img src="{BADGE_SCHEME}:{number}" width="{BADGE_PX}" height="{BADGE_PX}">'
            return (
                '<table cellspacing="0" cellpadding="0" style="margin: 22px 0 8px 0;"><tr>'
                f'<td valign="middle">{picture}</td>'
                f'<td valign="middle" style="padding-left: 12px;">{title}</td>'
                "</tr></table>"
            )

        self._text().add(html)

    def _hotkeys(self, group: HotkeyGroup) -> None:
        """A group of hotkeys: its title, and a table of what to press and what it does."""

        def html() -> str:
            title = _span(tr(group.title), GROUP_SIZE, bold=True, colour=ACCENT)
            size = _points(PARAGRAPH_SIZE)
            keys_cell = f'width="{KEYS_COLUMN_PX}" style="padding: 3px 12px 3px 0; {size}"'
            action_cell = f'style="padding: 3px 0; {size}"'
            rows = "".join(
                f"<tr><td {keys_cell}><b>{escape(hotkey.shown())}</b></td>"
                f"<td {action_cell}>{escape(tr(hotkey.action))}</td></tr>"
                for hotkey in group.hotkeys
            )
            return (
                f'<p style="margin: 14px 0 4px 0;">{title}</p>'
                f'<table cellspacing="0" cellpadding="0" style="margin: 0 0 6px 0; color: {TEXT};">{rows}</table>'
            )

        self._text().add(html)

    def _caption(self, text: str) -> QLabel:
        caption = QLabel()
        bind(caption, caption.setText, text)
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.setStyleSheet(f"color: {QUIET_TEXT};")
        selectable = Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        caption.setTextInteractionFlags(selectable)
        return caption

    def _player(
        self,
        steps: Sequence[Step],
        before: Sequence[Sequence[Step]],
        size: QSize,
        shown: Box = AROUND_THE_NET,
        project: Project | None = None,
        coordinates: bool = False,
    ) -> DemoPlayer:
        """An animation (`DemoPlayer`): of the default net, or of `project`'s, with the coordinates hint if wanted."""
        player = DemoPlayer(steps, before, size, shown, project=project, coordinates=coordinates)
        self.players.append(player)
        return player

    def _players(self, players: list[DemoPlayer], captions: list[QLabel] | None = None) -> None:
        self._block = None  # the text after them is a block of its own
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)
        for i, player in enumerate(players):
            grid.addWidget(player, 0, i, Qt.AlignmentFlag.AlignHCenter)
            if captions is not None:
                grid.addWidget(captions[i], 1, i)
        self._column.addSpacing(4)
        self._column.addLayout(grid)
        self._column.addSpacing(4)

    def restore_default_size(self) -> None:
        """The size it's made for: the column's width with room around it, most of the screen's height. It opens with
        it every time (`MainWindow.show_help`), whatever the user resized it to before."""
        screen = self.screen()
        height = 900 if screen is None else int(screen.availableGeometry().height() * 0.85)
        bar = self.tabs.tabBar()
        self.resize(WINDOW_PX + (bar.sizeHint().width() if bar is not None else 0), height)  # the page, and the tabs


def _points(size: float) -> str:
    """`size` times the application's usual text size, for a style (rich text knows no sizes in per cent)."""
    return f"font-size: {QApplication.font().pointSizeF() * size:.1f}pt;"


def _span(text: str, size: float, bold: bool = False, colour: str = TEXT) -> str:
    """`text` at `size` times the usual size."""
    weight = "font-weight: bold; " if bold else ""
    return f'<span style="{_points(size)} {weight}color: {colour};">{text}</span>'


def _paragraph_html(text: str, bullet: bool) -> str:
    """A paragraph with roomy lines; an item of a list has a bullet before it, and its lines start after the bullet."""
    style = f"line-height: 145%; margin: 0 0 12px 0; color: {TEXT};"
    size = _points(PARAGRAPH_SIZE)
    if bullet:
        style = f"line-height: 145%; margin: 0 0 6px 22px; text-indent: -22px; color: {TEXT};"
        text = f"&#8226;&nbsp;&nbsp;&nbsp;{text}"
    return f'<p style="{style} {size}">{text}</p>'


def _place_language(language: LanguageBox, block: TextBlock) -> None:
    """`LANGUAGE_GAP_PX` after the name's end (the first line of `block`), its middle on the middle of the name's
    line."""
    document = block.document()
    assert document is not None
    layout = document.documentLayout()
    first = document.firstBlock()
    lines = first.layout()
    assert layout is not None and lines is not None
    line = lines.lineAt(0)
    top = layout.blockBoundingRect(first).top() + line.y()
    size = language.sizeHint()
    language.resize(size)
    x = line.x() + line.naturalTextWidth() + LANGUAGE_GAP_PX
    language.move(round(x), round(top + line.height() / 2 - size.height() / 2))
