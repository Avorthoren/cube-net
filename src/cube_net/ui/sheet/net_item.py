# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`NetItem`: paints the cube net (docs/idea.txt colouring rules; docs/plan.md, section 6.3).

Painted bottom to top:
1. Hatch: each region is white with coloured triangles in its face's own frame (so the pattern rotates with it).
2. Fold edges: two-colour dashes centred on the cube edge.
3. Cuts (the perimeter): dashes drawn fully inside their region; a highlighted cut or fold edge is drawn wider. In
   CUT_EDITING, while the user hovers the perimeter, the cuts are drawn as the line divides them, and the parts that
   can't be chosen for gluing are thin and black. The counterpart of a hovered cut that can be chosen blinks: one cut
   can be left out.
4. Vertex circles on the perimeter, one equal sector per face of the vertex; a highlighted vertex gets a ring.
5. Optional debug labels (A_1, B_2, ...) next to all vertices, placed outside the net.
Hatch is drawn in sheet units; lines and circles have constant pixel sizes, so they are drawn in device pixels.

A net never changes once it's made, so what takes exact arithmetic is worked out once for it, not in every paint.
"""

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.cube import Face
from cube_net.core.cutting import SplitNet
from cube_net.core.labels import VertexLabel
from cube_net.core.net import HalfEdge, Net, NetVertex, Region
from cube_net.core.sheet import SHEET_MARGIN
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf, to_qtransform
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.net_painting import (
    UP_RIGHT,
    DashedSegment,
    paint_labels,
    paint_prepared,
    paint_vertex,
    prepare_dashed,
)


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
        self._highlight_vertex: NetVertex | None = None
        self._highlight_fold: HalfEdge | None = None
        self._glue: tuple[HalfEdge, ...] = ()
        self._overlapping: frozenset[HalfEdge] = frozenset()
        self._divided: SplitNet | None = None
        self._hidden_cut: HalfEdge | None = None
        self._dashes: dict[HalfEdge, DashedSegment | None] = {}
        self._polygons: dict[Region, QPolygonF] = {}
        self._centers: list[tuple[QPointF, frozenset[Face]]] | None = None
        self._outward: dict[NetVertex, QPointF] | None = None

    def set_net(self, net: Net) -> None:
        self.prepareGeometryChange()
        self._net = net
        self._labels = None
        self._highlight = None
        self._highlight_vertex = None
        self._highlight_fold = None
        self._glue = ()
        self._overlapping = frozenset()
        self._divided = None
        self._hidden_cut = None
        self._dashes = {}
        self._polygons = {}
        self._centers = None
        self._outward = None
        self.update()

    def restyle(self) -> None:
        """The style changed (colours, sizes, tiling, dashes): forget what was worked out with the old one."""
        self._hatch = hatch_path()
        self._dashes = {}
        self.update()

    def set_highlight(self, cut: HalfEdge | None) -> None:
        """Draw this cut highlighted (None: no highlight)."""
        if cut is not self._highlight:
            self._highlight = cut
            self.update()

    def highlight(self) -> HalfEdge | None:
        return self._highlight

    def set_glue(self, cuts: tuple[HalfEdge, ...]) -> None:
        """The cuts about to be glued, shown highlighted in CUT_APPROVING (empty: none)."""
        self._glue = cuts
        self.update()

    def glue(self) -> tuple[HalfEdge, ...]:
        return self._glue

    def set_overlapping(self, cuts: frozenset[HalfEdge]) -> None:
        """The cuts that take part in an overlap, shown in black (empty: none)."""
        self._overlapping = cuts
        self.update()

    def overlapping(self) -> frozenset[HalfEdge]:
        return self._overlapping

    def set_divided(self, split: SplitNet | None) -> None:
        """Draw the cuts as divided by the cut line, those that can't be chosen thin and black (None: as usual)."""
        if split is not self._divided:
            self._divided = split
            self._dashes = {}  # the divided cuts are other half-edges
            self.update()

    def divided(self) -> SplitNet | None:
        return self._divided

    def set_hidden_cut(self, cut: HalfEdge | None) -> None:
        """Leave this cut out, as if it weren't there; its vertices stay (None: all of them are drawn)."""
        if cut is not self._hidden_cut:
            self._hidden_cut = cut
            self.update()

    def hidden_cut(self) -> HalfEdge | None:
        return self._hidden_cut

    def set_highlight_fold(self, fold: HalfEdge | None) -> None:
        """Draw this fold edge highlighted (None: no highlight)."""
        if fold is not self._highlight_fold:
            self._highlight_fold = fold
            self.update()

    def highlight_fold(self) -> HalfEdge | None:
        return self._highlight_fold

    def set_highlight_vertex(self, vertex: NetVertex | None) -> None:
        """Draw this perimeter vertex highlighted (None: no highlight)."""
        if vertex is not self._highlight_vertex:
            self._highlight_vertex = vertex
            self.update()

    def highlight_vertex(self) -> NetVertex | None:
        return self._highlight_vertex

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
        useless = self._divided.same_half_cuts if self._divided is not None else frozenset()
        for he in self._cuts_to_paint():
            if he is self._hidden_cut:
                continue
            if he in useless:
                self._paint_solid(painter, world, he, palette.USELESS_CUT, net_style.USELESS_CUT_PX, units_per_px)
            else:
                self._paint_dashed(painter, world, he, inset=net_style.EDGE_WIDTH_PX / 2 * units_per_px)
        for he in self._glue:
            width = net_style.HIGHLIGHT_WIDTH_PX
            self._paint_dashed(painter, world, he, inset=width / 2 * units_per_px, width=width)
        if self._highlight is not None and self._highlight not in useless:
            width = net_style.HIGHLIGHT_WIDTH_PX
            self._paint_dashed(painter, world, self._highlight, inset=width / 2 * units_per_px, width=width)
        if self._highlight_fold is not None:  # as wide as a highlighted cut, but centered like every fold edge
            self._paint_dashed(painter, world, self._highlight_fold, inset=0.0, width=net_style.HIGHLIGHT_WIDTH_PX)
        for he in self._overlapping:
            self._paint_solid(painter, world, he, palette.REJECTED, net_style.EDGE_WIDTH_PX, units_per_px)
        self._paint_vertices(painter, world)
        if self._highlight_vertex is not None:
            center = world.map(to_qpointf(self._highlight_vertex.position))
            r = net_style.VERTEX_RADIUS_PX + net_style.VERTEX_HIGHLIGHT_PX / 2
            painter.setPen(QPen(palette.VERTEX_HIGHLIGHT, net_style.VERTEX_HIGHLIGHT_PX))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, r, r)
        if self._labels:
            self._paint_labels(painter, world, self._labels)
        painter.restore()

    # --- layers -----------------------------------------------------------------------------------------------------

    def _paint_hatch(self, painter: QPainter) -> None:
        for region in self._net.regions:
            outline = QPainterPath()
            outline.addPolygon(self._polygon(region))
            outline.closeSubpath()
            painter.save()
            painter.setClipPath(outline, Qt.ClipOperation.IntersectClip)
            painter.fillPath(outline, palette.WHITE)
            painter.setTransform(to_qtransform(region.placement), combine=True)
            painter.fillPath(self._hatch, palette.FACE_COLORS[region.face])
            painter.restore()

    def _polygon(self, region: Region) -> QPolygonF:
        polygon = self._polygons.get(region)
        if polygon is None:
            polygon = QPolygonF([to_qpointf(p) for p in self._net.region_polygon(region)])
            self._polygons[region] = polygon
        return polygon

    def _paint_dashed(
        self, painter: QPainter, world: QTransform, he: HalfEdge, inset: float, width: float | None = None
    ) -> None:
        """Dashed line of `width` px along `he`, shifted by `inset` units to its left (into its region)."""
        if he in self._dashes:
            segment = self._dashes[he]
        else:
            a, b = he.origin, he.destination
            segment = self._dashes[he] = prepare_dashed(a.position, b.position, a.point, b.point)
        if segment is not None:
            paint_prepared(painter, world, segment, inset, width)

    def _cuts_to_paint(self) -> list[HalfEdge]:
        if self._divided is None:
            return self._net.boundary_edges()
        return [he for he in self._divided.net.boundary_edges() if he not in self._divided.line_edges]

    @staticmethod
    def _paint_solid(
        painter: QPainter, world: QTransform, he: HalfEdge, colour: QColor, width: float, units_per_px: float
    ) -> None:
        """A cut in one solid colour, where the cut is drawn: inside its region."""
        a, b = to_qpointf(he.origin.position), to_qpointf(he.destination.position)
        d = b - a
        normal = QPointF(-d.y(), d.x()) / math.hypot(d.x(), d.y())
        inset = normal * (width / 2 * units_per_px)
        pen = QPen(colour, width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawLine(world.map(a + inset), world.map(b + inset))

    def _paint_vertices(self, painter: QPainter, world: QTransform) -> None:
        if self._centers is None:
            vertices = {v.id: v for v in self._net.boundary_vertices()}.values()
            self._centers = [(to_qpointf(v.position), v.point.faces) for v in vertices]
        for center, faces in self._centers:
            paint_vertex(painter, world.map(center), faces, net_style.VERTEX_RADIUS_PX)

    def _paint_labels(self, painter: QPainter, world: QTransform, labels: dict[NetVertex, VertexLabel]) -> None:
        if self._outward is None:  # the view only zooms and moves: directions in pixels stay the same
            self._outward = self._outward_directions(world)
        outward = self._outward
        paint_labels(
            painter,
            ((world.map(to_qpointf(v.position)), outward.get(v, UP_RIGHT), label) for v, label in labels.items()),
        )

    def _outward_directions(self, world: QTransform) -> dict[NetVertex, QPointF]:
        """Unit vectors in device pixels pointing away from the net at every perimeter vertex (bisector of the outer
        angle). The perimeter goes clockwise around the net, so the outside is on the left of each of its segments."""
        directions: dict[NetVertex, QPointF] = {}
        for perimeter in self._net.perimeters():
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
