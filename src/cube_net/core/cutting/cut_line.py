# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`CutLine`: the cut line being drawn (docs/idea.txt, "how to allow user to make new cuts")."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise

from cube_net.core.geometry import Vec
from cube_net.core.net import HalfEdge, NetVertex


@dataclass(frozen=True, slots=True)
class CutPoint:
    position: Vec

    # The cut (inner half-edge of a perimeter segment) the point lies on: set for the first and the last point,
    # None for points inside the net.
    edge: HalfEdge | None = None

    # Set if the point is exactly a vertex of the perimeter (chosen by clicking inside its circle); `edge` is then a
    # cut that starts at that vertex.
    vertex: NetVertex | None = None

    # Set if the point was placed on a fold line (exactly on it): only for points inside the net.
    fold: HalfEdge | None = None

    @property
    def on_perimeter(self) -> bool:
        return self.edge is not None


@dataclass(slots=True)
class CutLine:
    """A polyline from a point on the perimeter, through points inside the net, to another point on the perimeter."""

    points: list[CutPoint] = field(default_factory=list)

    @property
    def last(self) -> CutPoint:
        return self.points[-1]

    @property
    def closed(self) -> bool:
        """True once the line has reached the perimeter again (no more points can be appended)."""
        return len(self.points) >= 2 and self.points[-1].on_perimeter

    @property
    def inner_count(self) -> int:
        """Number of points after the first one (docs/idea.txt limits it to 50)."""
        return max(len(self.points) - 1, 0)

    def segments(self) -> list[tuple[Vec, Vec]]:
        return list(pairwise(p.position for p in self.points))
