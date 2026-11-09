"""Help -> Check for updates: not there yet, and it says so, with a little traffic cone of road works."""

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QPolygonF
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from cube_net.ui.help.small_window import SmallWindow

# The cone's colours.
CONE = QColor("#F57C00")
STRIPE = QColor("#FFFFFF")
CONE_BASE = QColor("#5F6368")
CONE_OUTLINE = QColor("#3C4043")

# The size of the drawing, in pixels.
CONE_PX = 56


class Cone(QWidget):
    """A traffic cone: work in progress."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(QSize(CONE_PX, CONE_PX))

    def paintEvent(self, event: QPaintEvent | None) -> None:
        s = CONE_PX / 56  # drawn on a 56 x 56 grid
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(s, s)
        painter.setPen(QPen(CONE_OUTLINE, 1.2))
        painter.setBrush(CONE_BASE)
        painter.drawRoundedRect(QRectF(6, 47, 44, 6), 2, 2)
        painter.setBrush(CONE)
        painter.drawPolygon(QPolygonF([QPointF(24, 4), QPointF(32, 4), QPointF(44, 47), QPointF(12, 47)]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(STRIPE)
        for top, bottom in ((16, 22), (31, 37)):  # stripes where the cone is as wide as at those heights

            def x_at(y: float, left: bool) -> float:
                return (24 - 12 * (y - 4) / 43) if left else (32 + 12 * (y - 4) / 43)

            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(x_at(top, True), top),
                        QPointF(x_at(top, False), top),
                        QPointF(x_at(bottom, False), bottom),
                        QPointF(x_at(bottom, True), bottom),
                    ]
                )
            )
        painter.end()


class UpdatesDialog(SmallWindow):
    """Closed with Escape or its close button."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Check for updates", parent)
        self.cone = Cone(self)
        self.text = QLabel("Under development...", self)
        content = QHBoxLayout()
        content.setContentsMargins(24, 16, 32, 20)
        content.setSpacing(16)
        content.addWidget(self.cone)
        content.addWidget(self.text)
        self.body.addLayout(content)
        self.setFixedSize(self.sizeHint())
