# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Points an action would make with numbers too long (`MAX_NUMBER_DIGITS`): the action is refused instead, and the
user told which point it is (`TooLong`).

An action can make several points: the line's own point it adds or moves (a `VERTEX`), and the points it derives from
the line: where it crosses a cut (`CROSSING`), its end where it divides the net (`END`), where it crosses a fold
(`FOLD_CROSSING`). A rearrangement moves the vertices of one half (`GLUED`); moving the origin makes `ORIGIN`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from cube_net.core.cutting.cut_line import CutPoint
from cube_net.core.cutting.pieces import crossings
from cube_net.core.cutting.real_cut import RealCut
from cube_net.core.geometry import LongNumber, Vec, long_number, on_segment
from cube_net.core.net import HalfEdge, Net, NetVertex


class TooLongKind(Enum):
    VERTEX = "vertex"
    CROSSING = "crossing"
    END = "end"
    FOLD_CROSSING = "fold crossing"
    GLUED = "glued"
    ORIGIN = "origin"


@dataclass(frozen=True, slots=True)
class TooLong:
    """A point an action would make whose number is too long."""

    kind: TooLongKind
    position: Vec
    number: LongNumber

    # The cut (CROSSING, END) or the fold (FOLD_CROSSING) it's on.
    edge: HalfEdge | None = None

    # The vertex of the rearranged net (GLUED), and that net (it's not kept: the action is refused).
    vertex: NetVertex | None = None
    net: Net | None = None


def point_too_long(
    kind: TooLongKind, p: Vec, edge: HalfEdge | None = None, vertex: NetVertex | None = None, net: Net | None = None
) -> TooLong | None:
    number = long_number(p)
    return None if number is None else TooLong(kind, p, number, edge, vertex, net)


def line_too_long(
    net: Net, points: Sequence[CutPoint], real: RealCut | None, made: Sequence[int], end: int | None = None
) -> TooLong | None:
    """The first point too long among the line's points `made` by the action (`end`: the one that's the end the line
    was cut short to, where it divides the net), and the points derived from the line (`real`: what it cuts)."""
    for i in made:
        point = points[i]
        if i == end:
            found = point_too_long(TooLongKind.END, point.position, point.edge)
        else:
            found = point_too_long(TooLongKind.VERTEX, point.position)
        if found is not None:
            return found
    if real is None:
        return None
    for stop in real.stops:
        if not stop.own and (found := point_too_long(TooLongKind.CROSSING, stop.point.position, stop.point.edge)):
            return found
    for k, inside in enumerate(real.inside):
        if not inside:
            continue
        for p in crossings(net, [real.stops[k].point.position, real.stops[k + 1].point.position]):
            if (found := point_too_long(TooLongKind.FOLD_CROSSING, p, _fold_at(net, p))) is not None:
                return found
    return None


def net_too_long(net: Net) -> TooLong | None:
    """The first vertex of the net (a rearranged one) whose number is too long."""
    for vertex in net.vertices:
        if (found := point_too_long(TooLongKind.GLUED, vertex.position, vertex=vertex, net=net)) is not None:
            return found
    return None


def _fold_at(net: Net, p: Vec) -> HalfEdge | None:
    """The fold (or the seam) `p` is on."""
    edges = [*net.fold_edges(), *net.inner_seams()]
    return next((f for f in edges if on_segment(p, f.origin.position, f.destination.position)), None)
