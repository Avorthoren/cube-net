# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The icons of the button that starts and stops logging: a red dot (record) and a red square in a frame (stop), as
media players and recorders show them. Drawn here, so that they look the same on every system."""

from functools import cache

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap

# The icon's size, in logical pixels.
ICON_PX = 20

RECORD = QColor("#D93025")
FRAME = QColor("#5F6368")


@cache
def record_icon() -> QIcon:
    """Start: a red dot."""
    return _drawn(_dot)


@cache
def stop_icon() -> QIcon:
    """Stop: a red square inside a bigger one."""
    return _drawn(_square)


def _drawn(draw: object) -> QIcon:
    screen = QGuiApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen is not None else 1.0
    pixmap = QPixmap(round(ICON_PX * ratio), round(ICON_PX * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw(painter)  # type: ignore[operator]
    painter.end()
    return QIcon(pixmap)


def _dot(painter: QPainter) -> None:
    painter.setPen(QPen(RECORD.darker(130), 1))
    painter.setBrush(RECORD)
    painter.drawEllipse(QRectF(4, 4, ICON_PX - 8, ICON_PX - 8))


def _square(painter: QPainter) -> None:
    painter.setPen(QPen(FRAME, 1.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(2, 2, ICON_PX - 4, ICON_PX - 4), 3, 3)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(RECORD)
    painter.drawRect(QRectF(6.5, 6.5, ICON_PX - 13, ICON_PX - 13))
