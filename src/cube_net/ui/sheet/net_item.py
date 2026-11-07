"""`NetItem`: paints the cube net (docs/idea.txt colouring rules; docs/plan.md, section 6.3).

Painted bottom to top:
1. Hatch: each region is white with coloured triangles in its face's own frame (so the pattern rotates with it).
2. Fold edges: two-colour dashes centred on the cube edge.
3. Cuts (the perimeter): dashes drawn fully inside their region; a highlighted cut is drawn wider.
4. Vertex circles on the perimeter, one equal sector per face of the vertex.
5. Optional debug labels (A_1, B_2, ...) next to all vertices, placed outside the net.
Hatch is drawn in sheet units; lines and circles have constant pixel sizes, so they are drawn in device pixels.
"""

import math

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QPolygonF, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.cube import DASH_LENGTH, dash_layout
from cube_net.core.labels import VertexLabel
from cube_net.core.net import HalfEdge, Net, NetVertex
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
        self._labels: dict[NetVertex, VertexLabel] | None = None
        self._highlight: HalfEdge | None = None

    def set_net(self, net: Net) -> None:
        self.prepareGeometryChange()
        self._net = net
        self._labels = None
        self._highlight = None
        self.update()

    def set_highlight(self, cut: HalfEdge | None) -> None:
        """Draw this cut highlighted (None: no highlight)."""
        if cut is not self._highlight:
            self._highlight = cut
            self.update()

    def highlight(self) -> HalfEdge | None:
        return self._highlight

    def set_labels(self, labels: dict[NetVertex, VertexLabel] | None) -> None:
        """Debug labels to draw next to vertices (None: no labels)."""
        self._labels = labels
        self.update()

    def labels(self) -> dict[NetVertex, VertexLabel] | None:
        return self._labels

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
        if self._highlight is not None:
            width = net_style.HIGHLIGHT_WIDTH_PX
            self._paint_dashed(painter, world, self._highlight, inset=width / 2 * units_per_px, width=width)
        self._paint_vertices(painter, world)
        if self._labels:
            self._paint_labels(painter, world, self._labels)
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

    def _paint_dashed(
        self, painter: QPainter, world: QTransform, he: HalfEdge, inset: float, width: float = net_style.EDGE_WIDTH_PX
    ) -> None:
        """Dashed line of `width` px along `he`, shifted by `inset` units to its left (into its region)."""
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
            pen = QPen(colours[parity], width)
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

    def _paint_labels(self, painter: QPainter, world: QTransform, labels: dict[NetVertex, VertexLabel]) -> None:
        name_font, index_font = QFont(), QFont()
        name_font.setPixelSize(net_style.LABEL_FONT_PX)
        index_font.setPixelSize(round(net_style.LABEL_FONT_PX * 0.75))
        name_metrics, index_metrics = QFontMetricsF(name_font), QFontMetricsF(index_font)
        painter.setPen(palette.LABEL)
        outward = self._outward_directions(world)
        for vertex, label in labels.items():
            index = str(label.index)
            width = name_metrics.horizontalAdvance(label.name) + index_metrics.horizontalAdvance(index)
            height = name_metrics.ascent()
            direction = outward.get(vertex, QPointF(math.sqrt(0.5), -math.sqrt(0.5)))  # default: up-right
            distance = net_style.VERTEX_RADIUS_PX + net_style.LABEL_GAP_PX + max(width, height) / 2
            center = world.map(to_qpointf(vertex.position)) + direction * distance
            baseline = QPointF(center.x() - width / 2, center.y() + height / 2)
            painter.setFont(name_font)
            painter.drawText(baseline, label.name)
            painter.setFont(index_font)
            subscript = baseline + QPointF(name_metrics.horizontalAdvance(label.name), index_metrics.ascent() / 3)
            painter.drawText(subscript, index)

    def _outward_directions(self, world: QTransform) -> dict[NetVertex, QPointF]:
        """Unit vectors in device pixels pointing away from the net at every perimeter vertex (bisector of the outer
        angle). The perimeter goes clockwise around the net, so the outside is on the left of each of its segments."""
        perimeter = self._net.perimeter()
        directions: dict[NetVertex, QPointF] = {}
        for incoming, outgoing in zip(perimeter[-1:] + perimeter[:-1], perimeter, strict=True):
            total = QPointF(0, 0)
            for he in (incoming, outgoing):
                a, b = world.map(to_qpointf(he.origin.position)), world.map(to_qpointf(he.destination.position))
                d = b - a
                length = math.hypot(d.x(), d.y())
                total += QPointF(d.y(), -d.x()) / length  # left in sheet = right in device (Y is flipped)
            length = math.hypot(total.x(), total.y())
            if length > 1e-9:
                directions[outgoing.origin] = total / length
        return directions
