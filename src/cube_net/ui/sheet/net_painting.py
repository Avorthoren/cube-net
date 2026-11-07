"""Painting helpers shared by the net and the cut line: two-colour dashed lines, vertex circles, debug labels.

They paint in device pixels: the painter must have no transform; `world` maps sheet units to device pixels.
"""

import math
from collections.abc import Iterable

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import QFont, QFontMetricsF, QPainter, QPen, QTransform

from cube_net.core.cube import DASH_LENGTH, Face, SurfacePoint, dash_layout
from cube_net.core.geometry import Vec
from cube_net.core.labels import VertexLabel
from cube_net.ui import palette
from cube_net.ui.qt_geometry import to_qpointf
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.dashing import dash_pieces


def paint_dashed(
    painter: QPainter,
    world: QTransform,
    a: Vec,
    b: Vec,
    a_point: SurfacePoint,
    b_point: SurfacePoint,
    inset: float = 0.0,
    width: float = net_style.EDGE_WIDTH_PX,
) -> None:
    """The dashed line a-b (sheet positions of cube points `a_point`, `b_point`), `width` px wide, shifted by `inset`
    units to the left of a->b. Colours and dash positions follow `dash_layout`, so every image of a cube segment looks
    the same."""
    qa, qb = to_qpointf(a), to_qpointf(b)
    d = qb - qa
    length = math.hypot(d.x(), d.y())
    if length == 0:
        return
    normal = QPointF(-d.y(), d.x()) / length
    pa, pb = world.map(qa + normal * inset), world.map(qb + normal * inset)
    layout = dash_layout(a_point, b_point)
    if layout.start != a_point:
        pa, pb = pb, pa
    line = QLineF(pa, pb)
    colours = [palette.FACE_COLORS[f] if f is not None else palette.WHITE for f in layout.faces]
    for s0, s1, parity in dash_pieces(length, float(layout.offset), float(DASH_LENGTH)):
        pen = QPen(colours[parity], width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawLine(QLineF(line.pointAt(s0 / length), line.pointAt(s1 / length)))


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
