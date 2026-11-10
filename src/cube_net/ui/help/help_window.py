# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Help -> Help: a big window that explains how the application works, with animations of the real tools.

The text is in a column of easy-to-read width, in blocks between the animations (`TextBlock`: selectable across
paragraphs). The animations (`demo`) are drawn in the style chosen in the settings, with the vertex labels if they're
switched on, and follow both when they change. Escape closes the window.
"""

from collections.abc import Callable, Sequence
from fractions import Fraction as F

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from cube_net.core.geometry import Box, Vec
from cube_net.ui.help.about_dialog import APP_NAME
from cube_net.ui.help.demo import scenes
from cube_net.ui.help.demo.demo_sheet import AROUND_THE_NET
from cube_net.ui.help.demo.player import DemoPlayer
from cube_net.ui.help.demo.steps import Step
from cube_net.ui.help.text_block import BADGE_PX, BADGE_SCHEME, TextBlock
from cube_net.ui.i18n import bind, tr

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
    "This application lets you build cube nets: simple polygons (without self-intersections) that, when folded, cover "
    "the whole surface of the unit cube without overlaps. So the area of such a polygon is always equal to the surface "
    "area of the unit cube: 6 square units."
)
IDEA = (
    "If a cube net is cut into two pieces, they can be rearranged and glued together again along a pair of edges that "
    "meet on the cube. That's exactly what the application is for:"
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
MORE_TITLE = "Good to know"
UNDO_TEXT = "Undo and redo work for up to 1000 actions: use Ctrl+Z and Ctrl+Y."
BOUNDS_TEXT = (
    "The application keeps track of the minimum-area bounding rectangle of the net. To see the rectangle itself, "
    "press the {bounds} button on the instrument panel."
)
SHIFT_TEXT = "Hold Shift while cutting or dragging a vertex to make the segment horizontal or vertical."
VIEW_TEXT = "Zoom with the mouse wheel; drag the sheet to move it."


class HelpWindow(QWidget):
    def __init__(self, parent: QWidget | None = None, labels: bool = False) -> None:
        """`labels`: whether the animations show the vertex labels (an app setting)."""
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.Window)
        bind(self, self.setWindowTitle, "{name} Help", name=APP_NAME)
        self._labels = labels
        self.players: list[DemoPlayer] = []
        self.blocks: list[TextBlock] = []
        self._block: TextBlock | None = None

        column = QWidget()
        column.setFixedWidth(COLUMN_PX)
        self._column = QVBoxLayout(column)
        self._column.setContentsMargins(0, 28, 0, 40)
        self._column.setSpacing(14)
        self._heading()
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
        self._title(MORE_TITLE)
        self._paragraph(UNDO_TEXT, bullet=True)
        self._paragraph(BOUNDS_TEXT, lambda: {"bounds": f"<b>{tr('Bounds')}</b>"}, bullet=True)
        self._paragraph(SHIFT_TEXT, bullet=True)
        self._paragraph(VIEW_TEXT, bullet=True)

        page = QWidget()
        page.setObjectName("page")
        page.setStyleSheet(f"#page {{ background: {PAGE}; }} QLabel {{ color: {TEXT}; }}")
        centred = QHBoxLayout(page)
        centred.addStretch(1)
        centred.addWidget(column)
        centred.addStretch(1)
        self.scroll = QScrollArea(self)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)
        self._resize_to_screen()

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is not None and event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def restyle(self) -> None:
        """The style changed in the settings: the animations follow it."""
        for player in self.players:
            player.restyle()

    def set_labels_shown(self, shown: bool) -> None:
        """The vertex labels were switched on or off in the settings: the animations follow."""
        self._labels = shown
        for player in self.players:
            player.set_labels_shown(shown)

    # --- the parts of the page ---------------------------------------------------------------------------------------

    def _text(self) -> TextBlock:
        """The block of text being written: a new one after an animation."""
        if self._block is None:
            self._block = TextBlock(COLUMN_PX)
            self.blocks.append(self._block)
            self._column.addWidget(self._block)
        return self._block

    def _heading(self) -> None:
        def html() -> str:
            name = _span(APP_NAME, NAME_SIZE, bold=True)
            subtitle = _span(tr("How it works"), SUBTITLE_SIZE, colour=QUIET_TEXT)
            return f'<p style="margin: 0 0 4px 0;">{name}</p><p style="margin: 0 0 16px 0;">{subtitle}</p>'

        self._text().add(html)

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

    def _caption(self, text: str) -> QLabel:
        caption = QLabel()
        bind(caption, caption.setText, text)
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.setStyleSheet(f"color: {QUIET_TEXT};")
        selectable = Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        caption.setTextInteractionFlags(selectable)
        return caption

    def _player(
        self, steps: Sequence[Step], before: Sequence[Sequence[Step]], size: QSize, shown: Box = AROUND_THE_NET
    ) -> DemoPlayer:
        player = DemoPlayer(steps, before, size, shown, self._labels)
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

    def _resize_to_screen(self) -> None:
        screen = self.screen()
        height = 900 if screen is None else int(screen.availableGeometry().height() * 0.85)
        self.resize(WINDOW_PX, height)


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
