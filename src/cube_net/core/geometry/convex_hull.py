# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exact convex hull (Andrew's monotone chain)."""

from collections.abc import Iterable

from cube_net.core.geometry.predicates import orient
from cube_net.core.geometry.vec import Vec


def convex_hull(points: Iterable[Vec]) -> list[Vec]:
    """Vertices of the convex hull, counter-clockwise, without collinear points; starts at the lowest-leftmost point.

    Fewer than 3 distinct points give those points (1 or 2, in sorted order).
    """
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def half(chain_points: list[Vec]) -> list[Vec]:
        chain: list[Vec] = []
        for p in chain_points:
            while len(chain) >= 2 and orient(chain[-2], chain[-1], p) <= 0:
                chain.pop()
            chain.append(p)
        return chain

    lower = half(pts)
    upper = half(list(reversed(pts)))
    hull = lower[:-1] + upper[:-1]
    return hull
