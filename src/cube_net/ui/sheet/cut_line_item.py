"""`CutLineItem`: draws the cut line being created (docs/idea.txt, CUTTING state).

Segments and points follow the usual colouring rules (two-colour dashes, sector circles), with a halo that marks them
as new. Points the user can't edit themselves are drawn as small dots (half the vertex radius) instead: the
counterpart images of the endpoints (docs/idea.txt: z_3, black, on the counterpart cuts) and the points where the line
crosses cube edges (grey; they become vertices of the new cuts). Once the line is applied they look like any other
vertex.
While cutting, a thin line goes from the last point to the mouse. While editing, a hollow circle marks the middle of
every segment. A rejected segment flashes black. While a point is being dragged, a part of the line may be off the net;
such a part has no faces to take colours from and is shown without them until the point is released. Optionally,
debug labels name the new points and images.
"""

import math
from collections.abc import Sequence
from itertools import pairwise

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.cutting import CutPoint, counterpart_image, crossings, endpoint_point, pieces
from cube_net.core.geometry import Vec
from cube_net.core.labels import VertexLabel
from cube_net.core.net import HalfEdge, Net
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.net_painting import UP_RIGHT, paint_dashed, paint_labels, paint_vertex


class CutLineItem(QGraphicsItem):
    def __init__(self, net: Net) -> None:
        super().__init__()
        self.setZValue(30)  # above the net, below the bounding rectangle and the ruler
        self._net = net
        self._area = QRectF()
        self._points: tuple[CutPoint, ...] = ()
        self._rubber: tuple[Vec, Vec] | None = None
        self._flash: tuple[tuple[Vec, Vec], ...] | None = None
        self._show_midpoints = False
        self._labels: tuple[tuple[Vec, VertexLabel], ...] = ()

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

    def set_labels(self, labels: Sequence[tuple[Vec, VertexLabel]]) -> None:
        """Debug labels: (position, label) of new points and images (empty: no labels)."""
        self._labels = tuple(labels)
        self.update()

    def labels(self) -> tuple[tuple[Vec, VertexLabel], ...]:
        return self._labels

    def images(self) -> list[Vec]:
        """Positions of the counterpart images of the endpoints."""
        images = (counterpart_image(self._net, p) for p in self._points if p.on_perimeter)
        return [image.position for image in images if image is not None]

    def crossings(self) -> list[Vec]:
        """Where the placed segments cross cube edges (between the line's own points)."""
        result: list[Vec] = []
        for a, b in pairwise(p.position for p in self._points):
            result += self._segment_crossings(a, b)
        return result

    def _segment_crossings(self, a: Vec, b: Vec) -> list[Vec]:
        try:
            return crossings(self._net, [a, b])
        except ValueError:  # off the net while a point is being dragged
            return []

    def set_rubber_band(self, segment: tuple[Vec, Vec] | None) -> None:
        if segment != self._rubber:
            self._rubber = segment
            self.update()

    def set_flash(self, segments: tuple[tuple[Vec, Vec], ...] | None) -> None:
        self._flash = segments
        self.update()

    def set_show_midpoints(self, show: bool) -> None:
        if show != self._show_midpoints:
            self._show_midpoints = show
            self.update()

    def midpoints(self) -> list[Vec]:
        """The middles of the segments, if they are shown."""
        if not self._show_midpoints:
            return []
        return [(a + b) / 2 for a, b in pairwise(p.position for p in self._points)]

    def points(self) -> tuple[CutPoint, ...]:
        return self._points

    def rubber_band(self) -> tuple[Vec, Vec] | None:
        return self._rubber

    def flash(self) -> tuple[tuple[Vec, Vec], ...] | None:
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
            self._paint_point(painter, world, point)
        for point in self._points:
            image = counterpart_image(self._net, point)
            if image is not None:
                self._paint_dot(painter, world, image.position, palette.COUNTERPART_IMAGE)
        for crossing in self.crossings():
            self._paint_dot(painter, world, crossing, palette.DERIVED_POINT)
        for midpoint in self.midpoints():
            self._paint_midpoint(painter, world, midpoint)
        if self._labels:
            outward = self._outward_directions(world)
            paint_labels(
                painter,
                ((world.map(to_qpointf(p)), outward.get(p, UP_RIGHT), label) for p, label in self._labels),
            )
        for segment in self._flash or ():
            self._paint_line(painter, world, segment, palette.REJECTED, net_style.EDGE_WIDTH_PX)
        painter.restore()

    def _paint_segment(self, painter: QPainter, world: QTransform, a: Vec, b: Vec) -> None:
        halo = net_style.EDGE_WIDTH_PX + 2 * net_style.CUT_LINE_HALO_PX
        self._paint_line(painter, world, (a, b), palette.CUT_LINE_HALO, halo)
        try:
            parts = pieces(self._net, a, b)
        except ValueError:  # off the net while a point is being dragged
            self._paint_line(painter, world, (a, b), palette.RUBBER_BAND, net_style.RUBBER_BAND_PX)
            return
        for piece in parts:
            paint_dashed(painter, world, piece.start, piece.end, piece.start_point, piece.end_point)

    def _outward_directions(self, world: QTransform) -> dict[Vec, QPointF]:
        """For points on the perimeter (endpoints and images): the unit device direction away from the net, so their
        labels don't cover it. The region is on the left of its cut, so "away" is the cut's right side."""
        cuts: dict[Vec, HalfEdge] = {}
        for point in self._points:
            if point.edge is not None:
                cuts[point.position] = point.edge
            image = counterpart_image(self._net, point)
            if image is not None:
                cuts[image.position] = image.edge
        directions = self._away_from_segments(world)
        for position, cut in cuts.items():
            d = to_qpointf(cut.destination.position) - to_qpointf(cut.origin.position)
            outward = QPointF(d.y(), -d.x())
            a, b = world.map(to_qpointf(position)), world.map(to_qpointf(position) + outward)
            device = b - a
            length = math.hypot(device.x(), device.y())
            if length > 0:
                directions[position] = device / length
        return directions

    def _away_from_segments(self, world: QTransform) -> dict[Vec, QPointF]:
        """For points inside the net: the unit device direction opposite to their one or two segments (the bisector
        of the wider angle), so their labels don't lie on the line."""
        directions: dict[Vec, QPointF] = {}
        positions = [p.position for p in self._points]
        for i, p in enumerate(positions):
            neighbours = [positions[j] for j in (i - 1, i + 1) if 0 <= j < len(positions)]
            center = world.map(to_qpointf(p))
            total = QPointF(0, 0)
            for q in neighbours:
                d = world.map(to_qpointf(q)) - center
                length = math.hypot(d.x(), d.y())
                if length > 0:
                    total -= d / length
            length = math.hypot(total.x(), total.y())
            if length > 1e-6:
                directions[p] = total / length
            elif neighbours:  # a straight line through the point: go sideways
                directions[p] = _sideways(center, world.map(to_qpointf(neighbours[0])))
        for a, b in pairwise(positions):  # crossings lie on a straight segment: go sideways too
            for crossing in self._segment_crossings(a, b):
                directions[crossing] = _sideways(world.map(to_qpointf(a)), world.map(to_qpointf(b)))
        return directions

    def _paint_point(self, painter: QPainter, world: QTransform, point: CutPoint) -> None:
        try:
            faces = endpoint_point(self._net, point).faces
        except ValueError:  # off the net while being dragged
            self._paint_dot(painter, world, point.position, palette.DERIVED_POINT)
            return
        self._paint_circle(painter, world, point.position, faces)

    @staticmethod
    def _paint_midpoint(painter: QPainter, world: QTransform, p: Vec) -> None:
        r = net_style.VERTEX_RADIUS_PX * net_style.MIDPOINT_RADIUS_FACTOR
        painter.setPen(QPen(palette.VERTEX_OUTLINE, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(world.map(to_qpointf(p)), r, r)

    @staticmethod
    def _paint_dot(painter: QPainter, world: QTransform, p: Vec, colour: QColor) -> None:
        """A small dot for a point the user can't edit (it follows the line)."""
        r = net_style.VERTEX_RADIUS_PX * net_style.DERIVED_POINT_RADIUS_FACTOR
        painter.setPen(QPen(palette.VERTEX_OUTLINE, 1))
        painter.setBrush(colour)
        painter.drawEllipse(world.map(to_qpointf(p)), r, r)

    @staticmethod
    def _paint_circle(painter: QPainter, world: QTransform, p: Vec, faces: frozenset[int]) -> None:
        center = world.map(to_qpointf(p))
        r = net_style.VERTEX_RADIUS_PX
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette.CUT_LINE_HALO)
        halo = r + net_style.CUT_LINE_HALO_PX
        painter.drawEllipse(center, halo, halo)
        paint_vertex(painter, center, faces, r)

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


def _sideways(a: QPointF, b: QPointF) -> QPointF:
    """A unit vector perpendicular to a-b (device pixels); up-right if a == b."""
    d = b - a
    length = math.hypot(d.x(), d.y())
    return QPointF(d.y(), -d.x()) / length if length > 0 else UP_RIGHT
