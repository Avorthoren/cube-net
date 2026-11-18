# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a cut line really cuts (docs/template_plan.md, §8.2: the cut rule of nets with holes).

The line's points may lie outside the net, or in a hole; only its parts on the net cut. Those are its *pieces*: each
goes from a point of the perimeter (where the line enters the net: the first point, a point clicked on the perimeter,
or where a segment crosses a cut) through the net to another (where it leaves it). The line divides the net once a
piece joins two places of the perimeter that are already joined around the net (the same perimeter cycle, or cycles
that earlier pieces have joined: cutting from the outside into a hole only opens a ring). So the line ends with the
first piece that divides the net, in exactly two.

A crossing of a cut is a point of that cut (rounded along it like any point put on a cut, `project_onto`), so a piece
starts or ends on the perimeter exactly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from cube_net.core.cutting.cut_line import CutLine, CutPoint
from cube_net.core.cutting.perimeter import on_the_perimeter, segment_crossings
from cube_net.core.geometry import Vec
from cube_net.core.net import Net


@dataclass(frozen=True, slots=True)
class Stop:
    """A point of the line or a crossing of a cut by one of its segments, in order along the line."""

    point: CutPoint

    # The segment (from point `segment` to the next one) it's on; for a point of the line, its index (the last point:
    # the number of segments).
    segment: int

    # Is it one of the line's own points (not a crossing)?
    own: bool


@dataclass(frozen=True, slots=True)
class RealCut:
    stops: tuple[Stop, ...]

    # For each part of the line between two stops (k: from stop k to stop k + 1), does it lie on the net?
    inside: tuple[bool, ...]

    # The finished pieces, in order along the line: each from the perimeter to the perimeter (the stops' indices).
    pieces: tuple[tuple[int, int], ...]

    # The piece that divides the net, if one does (the line ends with it).
    dividing: int | None

    def piece_line(self, k: int) -> CutLine:
        """Piece k as a line of its own, from the perimeter to the perimeter."""
        start, end = self.pieces[k]
        return CutLine([s.point for s in self.stops[start : end + 1]])

    def piece_lines(self) -> list[CutLine]:
        """The finished pieces up to the dividing one."""
        last = len(self.pieces) - 1 if self.dividing is None else self.dividing
        return [self.piece_line(k) for k in range(last + 1)]

    @property
    def divides_at_end(self) -> bool:
        """Does the line divide the net exactly at its last stop, its own last point (a finished line)?"""
        return self.dividing is not None and self.pieces[self.dividing][1] == len(self.stops) - 1


def real_cut(net: Net, points: Sequence[CutPoint]) -> RealCut | None:
    """What the line through `points` cuts; None if it can't be one (a segment touching the perimeter wrongly, see
    `segment_crossings`). Whether the line keeps the other rules (it doesn't touch itself, its first part goes into
    the net, it enters and leaves the net at its points on the perimeter) is `rules.py`'s."""
    stops: list[Stop] = []
    for i, point in enumerate(points):
        stops.append(Stop(point, i, True))
        if i + 1 < len(points):
            crossings = segment_crossings(net, point.position, points[i + 1].position)
            if crossings is None:
                return None
            stops.extend(Stop(c, i, False) for c in crossings)
    inside = tuple(_on_net(net, (a.point.position + b.point.position) / 2) for a, b in pairwise(stops))
    pieces: list[tuple[int, int]] = []
    start: int | None = None
    for k, part_inside in enumerate(inside):
        if part_inside and start is None:
            start = k
        elif not part_inside and start is not None:
            pieces.append((start, k))
            start = None
    if start is not None and stops[-1].point.on_perimeter:
        pieces.append((start, len(stops) - 1))
    return RealCut(tuple(stops), inside, tuple(pieces), _dividing(net, stops, pieces))


def _on_net(net: Net, p: Vec) -> bool:
    return net.contains(p) and on_the_perimeter(net, p) is None


def _dividing(net: Net, stops: list[Stop], pieces: list[tuple[int, int]]) -> int | None:
    """The first piece whose ends are already joined around the net (the perimeter cycles, joined by earlier pieces)."""
    cycles = net.perimeters()
    group = list(range(len(cycles)))

    def find(k: int) -> int:
        while group[k] != k:
            k = group[k]
        return k

    def cycle_of(point: CutPoint) -> int:
        assert point.edge is not None
        return next(i for i, cycle in enumerate(cycles) if point.edge.twin in cycle)

    for k, (start, end) in enumerate(pieces):
        a, b = find(cycle_of(stops[start].point)), find(cycle_of(stops[end].point))
        if a == b:
            return k
        group[b] = a
    return None
