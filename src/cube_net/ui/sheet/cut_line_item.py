"""`CutLineItem`: draws the cut line being created (docs/idea.txt, CUTTING state).

Segments and points follow the usual colouring rules (two-colour dashes, sector circles), with a halo that marks them
as new. While cutting, a thin line goes from the last point to the mouse. A rejected segment flashes black.
"""

from collections.abc import Sequence
from itertools import pairwise

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.cutting import CutPoint, pieces, surface_point_at
from cube_net.core.geometry import Vec
from cube_net.core.net import Net
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.net_painting import paint_dashed, paint_vertex


class CutLineItem(QGraphicsItem):
    def __init__(self, net: Net) -> None:
        super().__init__()
        self.setZValue(30)  # above the net, below the bounding rectangle and the ruler
        self._net = net
        self._area = QRectF()
        self._points: tuple[CutPoint, ...] = ()
        self._rubber: tuple[Vec, Vec] | None = None
        self._flash: tuple[Vec, Vec] | None = None

    # --- state ------------------------------------------------------------------------------------------------------

    def set_area(self, rect: QRectF) -> None:
        """Everything the item can paint on (the sheet plus room for pixel-sized decorations)."""
        self.prepareGeometryChange()
        self._area = QRectF(rect)

    def set_net(self, net: Net) -> None:
        self._net = net
        self.update()

    def set_points(self, points: Sequence[CutPoint]) -> None:
        self._points = tuple(points)
        self.update()

    def set_rubber_band(self, segment: tuple[Vec, Vec] | None) -> None:
        if segment != self._rubber:
            self._rubber = segment
            self.update()

    def set_flash(self, segment: tuple[Vec, Vec] | None) -> None:
        self._flash = segment
        self.update()

    def points(self) -> tuple[CutPoint, ...]:
        return self._points

    def rubber_band(self) -> tuple[Vec, Vec] | None:
        return self._rubber

    def flash(self) -> tuple[Vec, Vec] | None:
        return self._flash

    # --- painting ---------------------------------------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(self._area)

    def paint(
        self, painter: QPainter | None, option: QStyleOptionGraphicsItem | None, widget: QWidget | None = None
    ) -> None:
        if painter is None or not (self._points or self._flash):
            return
        world = painter.worldTransform()
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._rubber is not None:
            self._paint_line(painter, world, self._rubber, palette.RUBBER_BAND, net_style.RUBBER_BAND_PX, dashed=True)
        for a, b in pairwise(p.position for p in self._points):
            self._paint_segment(painter, world, a, b)
        for point in self._points:
            self._paint_point(painter, world, point.position)
        if self._flash is not None:
            self._paint_line(painter, world, self._flash, palette.REJECTED, net_style.EDGE_WIDTH_PX)
        painter.restore()

    def _paint_segment(self, painter: QPainter, world: QTransform, a: Vec, b: Vec) -> None:
        halo = net_style.EDGE_WIDTH_PX + 2 * net_style.CUT_LINE_HALO_PX
        self._paint_line(painter, world, (a, b), palette.CUT_LINE_HALO, halo)
        for piece in pieces(self._net, a, b):
            paint_dashed(painter, world, piece.start, piece.end, piece.start_point, piece.end_point)

    def _paint_point(self, painter: QPainter, world: QTransform, p: Vec) -> None:
        center = world.map(to_qpointf(p))
        r = net_style.VERTEX_RADIUS_PX
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette.CUT_LINE_HALO)
        halo = r + net_style.CUT_LINE_HALO_PX
        painter.drawEllipse(center, halo, halo)
        paint_vertex(painter, center, surface_point_at(self._net, p).faces, r)

    @staticmethod
    def _paint_line(
        painter: QPainter,
        world: QTransform,
        segment: tuple[Vec, Vec],
        colour: QColor,
        width: float,
        dashed: bool = False,
    ) -> None:
        pen = QPen(colour, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(world.map(to_qpointf(segment[0])), world.map(to_qpointf(segment[1])))
