# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exact comparison of angular sectors around a point. A sector is the open arc going counter-clockwise from one
direction to another; directions are non-zero vectors of any length, so everything stays rational."""

from cube_net.core.geometry.vec import Vec


def strictly_within(start: Vec, x: Vec, end: Vec) -> bool:
    """Is direction `x` strictly inside the counter-clockwise arc from `start` to `end`? Equal directions as `start`
    and `end` mean a full turn, minus that one direction."""
    span = start.cross(end)
    if span > 0:  # less than half a turn
        return start.cross(x) > 0 and x.cross(end) > 0
    if span < 0:  # more than half a turn: everything but the closed arc from `end` to `start`
        return not (end.cross(x) >= 0 and x.cross(start) >= 0)
    if start.dot(end) < 0:  # exactly half a turn
        return start.cross(x) > 0
    return x.cross(start) != 0 or x.dot(start) < 0  # a full turn


def sectors_overlap(start1: Vec, end1: Vec, start2: Vec, end2: Vec) -> bool:
    """Do two sectors share a positive angle? Sectors that only touch along a direction don't."""
    same_start = start1.cross(start2) == 0 and start1.dot(start2) > 0
    return same_start or strictly_within(start1, start2, end1) or strictly_within(start2, start1, end2)
