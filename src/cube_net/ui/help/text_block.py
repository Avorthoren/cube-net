"""`TextBlock`: the text of Help -> Help between two animations: titles and paragraphs in one document, so that any of
it can be selected at once and copied (Ctrl+C), across paragraphs too.

It's as tall as its text (no scroll bar of its own): the mouse wheel scrolls the page around it. Its parts are
functions that give their HTML in the current language, so the block follows a change of language.
"""

import math
from collections.abc import Callable

from PyQt6.QtCore import QRectF, Qt, QUrl
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QTextDocument, QWheelEvent
from PyQt6.QtWidgets import QFrame, QTextBrowser, QWidget

from cube_net.ui.i18n import TRANSLATIONS

# The step numbers: a white number in a disc of this colour, this large (px).
ACCENT = "#1A73E8"
BADGE_PX = 32

# The scheme of the step numbers' pictures: "badge:3" is the disc with 3.
BADGE_SCHEME = "badge"


class TextBlock(QTextBrowser):
    def __init__(self, width: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._width = width
        self._parts: list[Callable[[], str]] = []
        self.setFixedWidth(width)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setOpenLinks(False)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.setStyleSheet("QTextBrowser { background: transparent; }")
        viewport = self.viewport()
        if viewport is not None:
            viewport.setAutoFillBackground(False)
        document = self.document()
        assert document is not None
        document.setDocumentMargin(0)
        TRANSLATIONS.changed.connect(self.refresh)

    def add(self, part: Callable[[], str]) -> None:
        """A part of the text: a function that gives its HTML (called again when the language changes)."""
        self._parts.append(part)
        self.refresh()

    def refresh(self) -> None:
        self.setHtml("".join(part() for part in self._parts))
        document = self.document()
        assert document is not None
        document.setTextWidth(self._width)
        self.setFixedHeight(math.ceil(document.size().height()))

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        """Not for the text (it has nowhere to scroll, and Ctrl+wheel would zoom it): for the page."""
        if event is not None:
            event.ignore()

    def loadResource(self, kind: int, name: QUrl) -> object:
        if kind == QTextDocument.ResourceType.ImageResource.value and name.scheme() == BADGE_SCHEME:
            return badge(int(name.path()))
        return super().loadResource(kind, name)


def badge(number: int) -> QImage:
    """The picture of a step number, twice as large as it's shown, for sharp edges on any screen."""
    size = BADGE_PX * 2
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(ACCENT))
    painter.drawEllipse(QRectF(0, 0, size, size))
    font = QFont()
    font.setBold(True)
    font.setPixelSize(round(size * 0.45))
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, str(number))
    painter.end()
    return image
