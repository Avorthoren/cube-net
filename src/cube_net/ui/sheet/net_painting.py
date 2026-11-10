# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Painting helpers shared by the net and the cut line: two-colour dashed lines, vertex circles, debug labels.

They paint in device pixels: the painter must have no transform; `world` maps sheet units to device pixels.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen, QTransform

from cube_net.core.cube import Face, SurfacePoint, dash_layout
from cube_net.core.geometry import Vec
from cube_net.core.labels import VertexLabel
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.dashing import dash_pieces


@dataclass(frozen=True, slots=True)
class DashedSegment:
    """All that takes exact arithmetic to find out about a dashed line, ready to be painted again and again."""

    # Where the dash pattern starts and ends on the sheet, in floats.
    start: QPointF
    end: QPointF

    # The unit vector to the left of the line as `a` -> `b` were given, on the sheet.
    normal: QPointF

    length: float

    # (start, end, parity) along the line, in sheet units; see `dash_pieces`.
    pieces: list[tuple[float, float, int]]

    # The colour of the dashes of each parity.
    colours: tuple[QColor, QColor]


def prepare_dashed(a: Vec, b: Vec, a_point: SurfacePoint, b_point: SurfacePoint) -> DashedSegment | None:
    """The dashed line a-b (sheet positions of cube points `a_point`, `b_point`). Colours and dash positions follow
    `dash_layout`, so every image of a cube segment looks the same. None if a and b are the same point on the sheet."""
    qa, qb = to_qpointf(a), to_qpointf(b)
    d = qb - qa
    length = math.hypot(d.x(), d.y())
    if length == 0:
        return None
    layout = dash_layout(a_point, b_point)
    colours = [palette.FACE_COLORS[f] if f is not None else palette.WHITE for f in layout.faces]
    start, end = (qa, qb) if layout.start == a_point else (qb, qa)
    pieces = dash_pieces(length, float(layout.offset), 1 / (2 * net_style.DASHES_PER_EDGE))
    return DashedSegment(start, end, QPointF(-d.y(), d.x()) / length, length, pieces, (colours[0], colours[1]))


def paint_prepared(
    painter: QPainter, world: QTransform, segment: DashedSegment, inset: float, width: float | None = None
) -> None:
    """Paint the line `width` px wide (the edge width by default), shifted by `inset` units to its left. All dashes of
    a colour go in one call."""
    width = net_style.EDGE_WIDTH_PX if width is None else width
    shift = segment.normal * inset
    start, end = world.map(segment.start + shift), world.map(segment.end + shift)
    x, y = start.x(), start.y()
    ux, uy = (end.x() - x) / segment.length, (end.y() - y) / segment.length
    groups: tuple[list[QLineF], list[QLineF]] = ([], [])
    for s0, s1, parity in segment.pieces:
        groups[parity].append(QLineF(x + ux * s0, y + uy * s0, x + ux * s1, y + uy * s1))
    for colour, group in zip(segment.colours, groups, strict=True):
        if group:
            pen = QPen(colour, width)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            painter.drawLines(group)


def paint_dashed(
    painter: QPainter,
    world: QTransform,
    a: Vec,
    b: Vec,
    a_point: SurfacePoint,
    b_point: SurfacePoint,
    inset: float = 0.0,
    width: float | None = None,
) -> None:
    """A dashed line painted just once: see `prepare_dashed` and `paint_prepared`."""
    segment = prepare_dashed(a, b, a_point, b_point)
    if segment is not None:
        paint_prepared(painter, world, segment, inset, width)


def paint_vertex(painter: QPainter, center: QPointF, faces: Iterable[Face], radius: float) -> None:
    """A vertex circle at device position `center`: one equal sector per face, starting at the top."""
    rect = QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)
    ordered = sorted(faces)
    painter.setPen(QPen(palette.VERTEX_OUTLINE, 1))
    if len(ordered) == 1:  # a whole circle: a 360-degree pie would draw a radius line from the center
        painter.setBrush(palette.FACE_COLORS[ordered[0]])
        painter.drawEllipse(rect)
        return
    span = 360 / len(ordered)
    for i, face in enumerate(ordered):
        painter.setBrush(palette.FACE_COLORS[face])
        painter.drawPie(rect, round((90 + i * span) * 16), round(span * 16))


# Labels go up-right of their vertex unless a better direction is known.
UP_RIGHT = QPointF(math.sqrt(0.5), -math.sqrt(0.5))


def paint_labels(painter: QPainter, labels: Iterable[tuple[QPointF, QPointF, VertexLabel]]) -> None:
    """Debug labels like A₁: (device center of the vertex, unit direction to put the label in, label)."""
    name_font, index_font = QFont(), QFont()
    name_font.setPixelSize(net_style.LABEL_FONT_PX)
    index_font.setPixelSize(round(net_style.LABEL_FONT_PX * 0.75))
    name_metrics, index_metrics = QFontMetricsF(name_font), QFontMetricsF(index_font)
    painter.setPen(palette.LABEL)
    for center, direction, label in labels:
        index = str(label.index)
        width = name_metrics.horizontalAdvance(label.name) + index_metrics.horizontalAdvance(index)
        height = name_metrics.ascent()
        distance = net_style.VERTEX_RADIUS_PX + net_style.LABEL_GAP_PX + max(width, height) / 2
        middle = center + direction * distance
        baseline = QPointF(middle.x() - width / 2, middle.y() + height / 2)
        box = QRectF(baseline.x() - 1, middle.y() - height / 2 - 1, width + 2, height + index_metrics.descent() + 3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette.LABEL_BACKGROUND)
        painter.drawRect(box)
        painter.setPen(palette.LABEL)
        painter.setFont(name_font)
        painter.drawText(baseline, label.name)
        painter.setFont(index_font)
        subscript = baseline + QPointF(name_metrics.horizontalAdvance(label.name), index_metrics.ascent() / 3)
        painter.drawText(subscript, index)
