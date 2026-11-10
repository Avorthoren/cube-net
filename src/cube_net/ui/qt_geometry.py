# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Conversions between core geometry (exact) and Qt geometry (floats). For drawing only."""

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QTransform

from cube_net.core.geometry import Rigid90, Vec

_COS_SIN = ((1, 0), (0, 1), (-1, 0), (0, -1))


def to_qpointf(v: Vec) -> QPointF:
    return QPointF(float(v.x), float(v.y))


def to_qtransform(m: Rigid90) -> QTransform:
    """The same map as `m`: rotation by k*90 degrees counter-clockwise, then translation."""
    c, s = _COS_SIN[m.k]
    # QTransform maps (x, y) to (m11*x + m21*y + dx, m12*x + m22*y + dy).
    return QTransform(c, s, -s, c, float(m.t.x), float(m.t.y))
