# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`TemplateItem`: paints a template being made (docs/template_idea.txt).

Painted bottom to top:
1. Faces (once the loop is closed): white, with the hatch in their colour. The hatch is the same everywhere, tied to
   the grid: as if the whole sheet were hatched and only the faces showed it (`Faces tiling` is per unit).
2. Fold lines, dashed; the loop, solid; the line following the mouse (from the loop's open end, or from a fold's start),
   dashed and thin; rejected segments, black for a moment.
3. Vertex circles; a highlighted one (what a click would use) gets a ring. The middle circles of the loop's sides, where
   a click inserts a vertex (while the loop is closed).
4. Every label (always shown in a template), outside the loop.
Hatch is drawn in sheet units; lines and circles have constant pixel sizes, so they are drawn in device pixels.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from cube_net.core.geometry import Vec
from cube_net.core.labels import VertexLabel
from cube_net.core.sheet import TEMPLATE_SHEET_HEIGHT, TEMPLATE_SHEET_WIDTH
from cube_net.core.template import Template
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.hatch import cells_around, tiled_hatch
from cube_net.ui.sheet.net_painting import UP_RIGHT, paint_labels
from cube_net.ui.template.corners import middle_angle, owned_arcs, shared

type Segment = tuple[Vec, Vec]


class TemplateItem(QGraphicsItem):
    def __init__(self, template: Template) -> None:
        super().__init__()
        self._template = template
        # What the tool shows on top of the template (see the setters).
        self._moved: tuple[int, Vec] | None = None
        self._rubber: Segment | None = None
        self._flash: tuple[Segment, ...] = ()
        self._highlight_vertex: Vec | None = None
        # The parts of its circle the highlighted vertex owns, where several are at its point (None: all of it).
        self._highlight_arcs: list[tuple[float, float]] | None = None
        self._highlight_fold: Segment | None = None
        self._midpoints_shown = False
        self._pressed_midpoint: int | None = None
        self._hatches: dict[tuple[int, int, int, int], QPainterPath] = {}

    # --- what to show -------------------------------------------------------------------------------------------------

    def set_template(self, template: Template) -> None:
        self._template = template
        self._moved = None
        self.update()

    def template(self) -> Template:
        """The template as shown (with a dragged vertex where it is)."""
        if self._moved is None:
            return self._template
        vertex_id, position = self._moved
        return self._template.with_vertex_moved(vertex_id, position)

    def set_moved(self, moved: tuple[int, Vec] | None) -> None:
        """A vertex being dragged, shown where it is now (None: none)."""
        self._moved = moved
        self.update()

    def set_rubber(self, segment: Segment | None) -> None:
        self._rubber = segment
        self.update()

    def rubber(self) -> Segment | None:
        return self._rubber

    def midpoints_shown(self) -> bool:
        return self._midpoints_shown

    def set_flash(self, segments: Sequence[Segment]) -> None:
        self._flash = tuple(segments)
        self.update()

    def flash(self) -> tuple[Segment, ...]:
        return self._flash

    def set_highlight_vertex(self, position: Vec | None, arcs: list[tuple[float, float]] | None = None) -> None:
        """Ring the vertex at `position` (None: none); only along `arcs` (radians, counter-clockwise), if given."""
        self._highlight_vertex, self._highlight_arcs = position, arcs
        self.update()

    def highlight_vertex(self) -> Vec | None:
        return self._highlight_vertex

    def highlight_arcs(self) -> list[tuple[float, float]] | None:
        return self._highlight_arcs

    def set_highlight_fold(self, segment: Segment | None) -> None:
        self._highlight_fold = segment
        self.update()

    def set_midpoints_shown(self, shown: bool, pressed: int | None = None) -> None:
        self._midpoints_shown, self._pressed_midpoint = shown, pressed
        self.update()

    def restyle(self) -> None:
        """The style changed: the hatch is made again."""
        self._hatches.clear()
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, TEMPLATE_SHEET_WIDTH, TEMPLATE_SHEET_HEIGHT)

    # --- painting -----------------------------------------------------------------------------------------------------

    def paint(
        self, painter: QPainter | None, option: QStyleOptionGraphicsItem | None, widget: QWidget | None = None
    ) -> None:
        if painter is None:
            return
        template = self.template()
        world = painter.worldTransform()
        self._paint_faces(painter, template)
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for fold in template.folds:
            segment = (template.position(fold.start), template.position(fold.end))
            self._line(painter, world, segment, palette.TEMPLATE_FOLD, net_style.EDGE_WIDTH_PX / 2, dashed=True)
        if self._highlight_fold is not None:
            self._line(painter, world, self._highlight_fold, palette.TEMPLATE_FOLD, net_style.HIGHLIGHT_WIDTH_PX)
        for a, b in template.loop_sides():
            segment = (template.position(a), template.position(b))
            if template.closed:  # inside the net, on its own side of the line (as cuts are drawn in a project)
                self._inner_line(painter, world, segment)
            else:
                self._line(painter, world, segment, palette.TEMPLATE_LOOP)
        if self._rubber is not None:
            self._line(painter, world, self._rubber, palette.RUBBER_BAND, net_style.RUBBER_BAND_PX, dashed=True)
        for segment in self._flash:
            self._line(painter, world, segment, palette.REJECTED, net_style.EDGE_WIDTH_PX)
        self._paint_vertices(painter, world, template)
        if self._midpoints_shown:
            self._paint_midpoints(painter, world, template)
        self._paint_labels(painter, world, template)
        painter.restore()

    def _paint_faces(self, painter: QPainter, template: Template) -> None:
        for face in template.faces:
            polygon = template.face_polygon(face)
            outline = QPainterPath()
            outline.addPolygon(QPolygonF([to_qpointf(p) for p in polygon]))
            outline.closeSubpath()
            painter.save()
            painter.setClipPath(outline, Qt.ClipOperation.IntersectClip)
            painter.fillPath(outline, palette.WHITE)
            if face.color != palette.WHITE.name().upper():  # white on white: nothing to see
                cells = cells_around(polygon)
                hatch = self._hatches.get(cells)
                if hatch is None:
                    hatch = self._hatches[cells] = tiled_hatch(*cells)
                painter.fillPath(hatch, QColor(face.color))
            painter.restore()

    @staticmethod
    def _line(
        painter: QPainter,
        world: QTransform,
        segment: Segment,
        colour: QColor,
        width: float | None = None,
        *,
        dashed: bool = False,
    ) -> None:
        pen = QPen(colour, net_style.EDGE_WIDTH_PX if width is None else width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        a, b = segment
        painter.drawLine(world.map(to_qpointf(a)), world.map(to_qpointf(b)))

    @staticmethod
    def _inner_line(painter: QPainter, world: QTransform, segment: Segment) -> None:
        """A side of the closed loop, drawn just inside the net (on its left: the loop goes counter-clockwise)."""
        a, b = (world.map(to_qpointf(p)) for p in segment)
        d = b - a
        length = math.hypot(d.x(), d.y())
        if length == 0:
            return
        width = net_style.EDGE_WIDTH_PX
        inset = QPointF(d.y(), -d.x()) / length * (width / 2)  # left in the sheet is right on screen (y is flipped)
        pen = QPen(palette.TEMPLATE_LOOP, width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawLine(a + inset, b + inset)

    def _paint_vertices(self, painter: QPainter, world: QTransform, template: Template) -> None:
        r = net_style.VERTEX_RADIUS_PX
        painter.setPen(QPen(palette.VERTEX_OUTLINE, 1))
        painter.setBrush(palette.WHITE)
        for v in template.vertices:
            painter.drawEllipse(world.map(to_qpointf(v.position)), r, r)
        if self._highlight_vertex is not None:
            ring = r + net_style.VERTEX_HIGHLIGHT_PX / 2
            painter.setPen(QPen(palette.VERTEX_HIGHLIGHT, net_style.VERTEX_HIGHLIGHT_PX))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            center = world.map(to_qpointf(self._highlight_vertex))
            if self._highlight_arcs is None:
                painter.drawEllipse(center, ring, ring)
            else:  # the sheet's y goes up, as Qt's angles do on screen
                rect = QRectF(center.x() - ring, center.y() - ring, 2 * ring, 2 * ring)
                for start, end in self._highlight_arcs:
                    painter.drawArc(rect, round(math.degrees(start) * 16), round(math.degrees(end - start) * 16))

    def _paint_midpoints(self, painter: QPainter, world: QTransform, template: Template) -> None:
        r = net_style.midpoint_radius()
        for i, (a, b) in enumerate(template.loop_sides()):
            pressed = i == self._pressed_midpoint
            painter.setPen(QPen(palette.PRESSED_MIDPOINT if pressed else palette.VERTEX_OUTLINE, 1))
            painter.setBrush(palette.PRESSED_MIDPOINT if pressed else Qt.BrushStyle.NoBrush)
            middle = (template.position(a) + template.position(b)) / 2
            painter.drawEllipse(world.map(to_qpointf(middle)), r, r)

    def _paint_labels(self, painter: QPainter, world: QTransform, template: Template) -> None:
        directions = _outward(world, template)
        for v in template.vertices:  # several at one point: each along the middle of its own part of it
            if shared(template, v.id):
                angle = middle_angle(owned_arcs(template, v.id))
                if angle is not None:
                    directions[v.id] = QPointF(math.cos(angle), -math.sin(angle))  # the sheet's y goes up
        paint_labels(
            painter,
            (
                (
                    world.map(to_qpointf(v.position)),
                    directions.get(v.id, UP_RIGHT),
                    VertexLabel(v.label.name, v.label.index),
                )
                for v in template.vertices
                if v.label is not None
            ),
        )


def _outward(world: QTransform, template: Template) -> dict[int, QPointF]:
    """Unit vectors in device pixels pointing out of a closed loop at its vertices (bisectors of the outer angles). The
    loop goes counter-clockwise, so the outside is on the right of each side."""
    if not template.closed:
        return {}
    directions: dict[int, QPointF] = {}
    sides = template.loop_sides()
    for incoming, outgoing in zip(sides[-1:] + sides[:-1], sides, strict=True):
        total = QPointF(0, 0)
        for a, b in (incoming, outgoing):
            d = world.map(to_qpointf(template.position(b))) - world.map(to_qpointf(template.position(a)))
            length = math.hypot(d.x(), d.y())
            total += QPointF(-d.y(), d.x()) / length  # right in sheet = left in device (Y is flipped)
        length = math.hypot(total.x(), total.y())
        if length > 1e-9:
            directions[outgoing[0]] = total / length
    return directions
