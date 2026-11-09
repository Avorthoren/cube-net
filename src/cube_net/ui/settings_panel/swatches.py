"""Small squares that show a colour: a plain one, and one that looks like a piece of the grid."""

from PyQt6.QtCore import QPointF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

from cube_net.ui import palette

# The size of a swatch, in pixels (docs/idea.txt, settings).
SWATCH_PX = 20


class ColorSwatch(QWidget):
    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(QSize(SWATCH_PX, SWATCH_PX))
        self._color = QColor(color)

    def color(self) -> QColor:
        return QColor(self._color)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._color)
        painter.end()


class GridSwatch(ColorSwatch):
    """White, crossed through the middle by a vertical and a horizontal grid line of the grid's colour and width, with a
    thin black outline."""

    def __init__(self, color: str, width: float, parent: QWidget | None = None) -> None:
        super().__init__(color, parent)
        self._width = width

    def line_width(self) -> float:
        return self._width

    def set_line_width(self, width: float) -> None:
        self._width = width
        self.update()

    def paintEvent(self, event: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), palette.SHEET)
        if self._width > 0:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(self._color, self._width)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            middle = SWATCH_PX / 2
            painter.drawLine(QPointF(middle, 0), QPointF(middle, SWATCH_PX))
            painter.drawLine(QPointF(0, middle), QPointF(SWATCH_PX, middle))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(palette.SWATCH_OUTLINE, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()
