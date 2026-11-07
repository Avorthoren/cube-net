"""`RulerItem`: draws the ruler (docs/idea.txt, "ruler" instrument).

For points P1..Pn and the mouse position M: lines P1-P2, ..., Pn-M; coordinates next to every point and next to the
mouse; the length of every line next to its middle. Everything has a constant pixel size, so it's drawn in device
pixels on top of the net.
"""

import math
from collections.abc import Sequence
from itertools import pairwise

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QFont, QFontMetricsF, QPainter, QPen, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.geometry import Vec
from cube_net.core.ruler import distance
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import ruler_style


def format_point(p: Vec) -> str:
    return f"({float(p.x):.3f}, {float(p.y):.3f})"


def format_distance(a: Vec, b: Vec) -> str:
    return f"{distance(a, b):.3f}"


class RulerItem(QGraphicsItem):
    def __init__(self) -> None:
        super().__init__()
        self.setZValue(100)  # above the net
        self._rect = QRectF()
        self._margin = 0.0
        self._points: tuple[Vec, ...] = ()
        self._cursor: Vec | None = None

    def set_rect(self, rect: QRectF, margin: float) -> None:
        """The area the ruler can be used in (the sheet), and how far (in units) its labels may stick out of it."""
        self.prepareGeometryChange()
        self._rect = QRectF(rect)
        self._margin = margin

    def set_state(self, points: Sequence[Vec], cursor: Vec | None) -> None:
        """The measured points and the mouse position (None: the mouse is not over the sheet)."""
        self._points = tuple(points)
        self._cursor = cursor
        self.update()

    def boundingRect(self) -> QRectF:
        m = self._margin
        return self._rect.adjusted(-m, -m, m, m)

    def paint(
        self, painter: QPainter | None, option: QStyleOptionGraphicsItem | None, widget: QWidget | None = None
    ) -> None:
        if painter is None or not self._points:
            return
        world = painter.worldTransform()
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        chain = list(self._points) + ([self._cursor] if self._cursor is not None else [])

        pen = QPen(palette.RULER, ruler_style.LINE_WIDTH_PX)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        for a, b in pairwise(chain):
            painter.drawLine(world.map(to_qpointf(a)), world.map(to_qpointf(b)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette.RULER)
        r = ruler_style.POINT_RADIUS_PX
        for p in self._points:
            painter.drawEllipse(world.map(to_qpointf(p)), r, r)

        font = QFont()
        font.setPixelSize(ruler_style.FONT_PX)
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        for p in self._points:
            anchor = world.map(to_qpointf(p)) + QPointF(
                ruler_style.POINT_LABEL_OFFSET_PX, -ruler_style.POINT_LABEL_OFFSET_PX
            )
            self._label(painter, metrics, format_point(p), anchor, below=False)
        if self._cursor is not None:
            offset = ruler_style.CURSOR_LABEL_OFFSET_PX
            anchor = world.map(to_qpointf(self._cursor)) + QPointF(offset, offset)
            self._label(painter, metrics, format_point(self._cursor), anchor, below=True)
        for a, b in pairwise(chain):
            self._distance_label(painter, metrics, world, a, b)
        painter.restore()

    def _distance_label(self, painter: QPainter, metrics: QFontMetricsF, world: QTransform, a: Vec, b: Vec) -> None:
        pa, pb = world.map(to_qpointf(a)), world.map(to_qpointf(b))
        d = pb - pa
        length = math.hypot(d.x(), d.y())
        if length < 1:
            return
        normal = QPointF(d.y(), -d.x()) / length
        if normal.y() > 0:  # always put it above the line (on screen)
            normal = -normal
        center = (pa + pb) / 2 + normal * ruler_style.DISTANCE_LABEL_OFFSET_PX
        text = format_distance(a, b)
        anchor = center - QPointF(metrics.horizontalAdvance(text) / 2, -metrics.ascent() / 2)
        self._label(painter, metrics, text, anchor, below=False, baseline=True)

    @staticmethod
    def _label(
        painter: QPainter, metrics: QFontMetricsF, text: str, anchor: QPointF, below: bool, baseline: bool = False
    ) -> None:
        """Text with a translucent box. `anchor` is the box's bottom-left corner (top-left if `below`), or the text's
        baseline start if `baseline`."""
        pad = ruler_style.LABEL_PADDING_PX
        width, ascent, descent = metrics.horizontalAdvance(text), metrics.ascent(), metrics.descent()
        if baseline:
            origin = anchor
        elif below:
            origin = anchor + QPointF(pad, pad + ascent)
        else:
            origin = anchor + QPointF(pad, -pad - descent)
        box = QRectF(origin.x() - pad, origin.y() - ascent - pad, width + 2 * pad, ascent + descent + 2 * pad)
        shift = _shift_into(box, _device_rect(painter))  # keep labels visible near the edges of the view
        box.translate(shift)
        origin += shift
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette.RULER_LABEL_BACKGROUND)
        painter.drawRect(box)
        painter.setPen(palette.RULER_TEXT)
        painter.drawText(origin, text)


def _device_rect(painter: QPainter) -> QRectF:
    device = painter.device()
    if device is None:
        return QRectF()
    return QRectF(0, 0, device.width() / device.devicePixelRatioF(), device.height() / device.devicePixelRatioF())


def _shift_into(box: QRectF, area: QRectF) -> QPointF:
    """The smallest move that puts `box` inside `area` (no move if `area` is empty or smaller than the box)."""
    if area.isEmpty() or box.width() > area.width() or box.height() > area.height():
        return QPointF(0, 0)
    dx = max(area.left() - box.left(), 0.0) + min(area.right() - box.right(), 0.0)
    dy = max(area.top() - box.top(), 0.0) + min(area.bottom() - box.bottom(), 0.0)
    return QPointF(dx, dy)
