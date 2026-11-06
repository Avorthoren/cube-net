"""`NetItem`: paints the cube net (docs/idea.txt colouring rules; docs/plan.md, section 6.3).

Painted bottom to top:
1. Hatch: each region is white with coloured triangles in its face's own frame (so the pattern rotates with it).
2. Fold edges: two-colour dashes centred on the cube edge.
3. Cuts (the perimeter): dashes drawn fully inside their region.
4. Vertex circles on the perimeter, one equal sector per face of the vertex.
Hatch is drawn in sheet units; lines and circles have constant pixel sizes, so they are drawn in device pixels.
"""

import math

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QPolygonF, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.cube import DASH_LENGTH, dash_layout
from cube_net.core.net import HalfEdge, Net
from cube_net.core.sheet import SHEET_MARGIN
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf, to_qtransform
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.dashing import dash_pieces


def hatch_path() -> QPainterPath:
    """The coloured triangles of the hatch in a face's local unit square: in every 1/10 x 1/5 cell, the triangle above
    the diagonal from its bottom-left to its upper-right corner."""
    path = QPainterPath()
    w, h = 1 / net_style.HATCH_COLUMNS, 1 / net_style.HATCH_ROWS
    for i in range(net_style.HATCH_COLUMNS):
        for j in range(net_style.HATCH_ROWS):
            x0, y0 = i * w, j * h
            path.addPolygon(QPolygonF([QPointF(x0, y0), QPointF(x0 + w, y0 + h), QPointF(x0, y0 + h)]))
            path.closeSubpath()
    return path


class NetItem(QGraphicsItem):
    def __init__(self, net: Net) -> None:
        super().__init__()
        self._net = net
        self._hatch = hatch_path()

    def set_net(self, net: Net) -> None:
        self.prepareGeometryChange()
        self._net = net
        self.update()

    def boundingRect(self) -> QRectF:
        # The sheet margin is always large enough for pixel-sized decorations at the allowed zoom levels.
        box = self._net.bounding_box().expanded(SHEET_MARGIN)
        return QRectF(float(box.lo.x), float(box.lo.y), float(box.width), float(box.height))

    def paint(
        self, painter: QPainter | None, option: QStyleOptionGraphicsItem | None, widget: QWidget | None = None
    ) -> None:
        if painter is None:
            return
        world = painter.worldTransform()
        self._paint_hatch(painter)
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        units_per_px = 1 / math.hypot(world.m11(), world.m12())
        for he in self._net.fold_edges():
            self._paint_dashed(painter, world, he, inset=0.0)
        for he in self._net.boundary_edges():
            self._paint_dashed(painter, world, he, inset=net_style.EDGE_WIDTH_PX / 2 * units_per_px)
        self._paint_vertices(painter, world)
        painter.restore()

    # --- layers -----------------------------------------------------------------------------------------------------

    def _paint_hatch(self, painter: QPainter) -> None:
        for region in self._net.regions:
            outline = QPainterPath()
            outline.addPolygon(QPolygonF([to_qpointf(p) for p in self._net.region_polygon(region)]))
            outline.closeSubpath()
            painter.save()
            painter.setClipPath(outline, Qt.ClipOperation.IntersectClip)
            painter.fillPath(outline, palette.WHITE)
            painter.setTransform(to_qtransform(region.placement), combine=True)
            painter.fillPath(self._hatch, palette.FACE_COLORS[region.face])
            painter.restore()

    def _paint_dashed(self, painter: QPainter, world: QTransform, he: HalfEdge, inset: float) -> None:
        """Dashed line along `he`, shifted by `inset` units to its left (into its region)."""
        a, b = to_qpointf(he.origin.position), to_qpointf(he.destination.position)
        d = b - a
        length = math.hypot(d.x(), d.y())
        normal = QPointF(-d.y(), d.x()) / length
        a, b = world.map(a + normal * inset), world.map(b + normal * inset)
        layout = dash_layout(he.origin.point, he.destination.point)
        if layout.start != he.origin.point:
            a, b = b, a
        line = QLineF(a, b)
        colours = [palette.FACE_COLORS[f] if f is not None else palette.WHITE for f in layout.faces]
        for s0, s1, parity in dash_pieces(length, float(layout.offset), float(DASH_LENGTH)):
            pen = QPen(colours[parity], net_style.EDGE_WIDTH_PX)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            painter.drawLine(QLineF(line.pointAt(s0 / length), line.pointAt(s1 / length)))

    def _paint_vertices(self, painter: QPainter, world: QTransform) -> None:
        r = net_style.VERTEX_RADIUS_PX
        painter.setPen(QPen(palette.VERTEX_OUTLINE, 1))
        for vertex in {v.id: v for v in self._net.boundary_vertices()}.values():
            center = world.map(to_qpointf(vertex.position))
            rect = QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r)
            faces = sorted(vertex.point.faces)
            span = 360 / len(faces)
            for i, face in enumerate(faces):
                painter.setBrush(palette.FACE_COLORS[face])
                painter.drawPie(rect, round((90 + i * span) * 16), round(span * 16))
