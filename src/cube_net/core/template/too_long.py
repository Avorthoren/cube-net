# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""A template's points an action would make with numbers too long (`MAX_NUMBER_DIGITS`): the action is refused instead,
and the user told which point it is (`TemplateTooLong`), as in projects (`core/cutting/too_long.py`).

An action makes one point (a `VERTEX`: drawn, typed, dragged, inserted), or, closing a hole, also the points where the
hole's sides cross folds (`HOLE_CROSSING`); moving the origin makes `ORIGIN`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cube_net.core.geometry import LongNumber, Vec, long_number, on_segment
from cube_net.core.template.template import Fold, Template


class TemplateTooLongKind(Enum):
    VERTEX = "vertex"
    HOLE_CROSSING = "hole crossing"
    ORIGIN = "origin"


@dataclass(frozen=True, slots=True)
class TemplateTooLong:
    """A point an action would make whose number is too long."""

    kind: TemplateTooLongKind
    position: Vec
    number: LongNumber

    # The fold a hole's side crosses there (HOLE_CROSSING).
    fold: Fold | None = None


def template_too_long(before: Template, after: Template) -> TemplateTooLong | None:
    """The first point of `after` (an action's result) that `before` hadn't there and whose number is too long."""
    had = {vertex.id: vertex.position for vertex in before.all_vertices}
    for vertex in after.all_vertices:
        if had.get(vertex.id) == vertex.position:
            continue
        number = long_number(vertex.position)
        if number is None:
            continue
        fold = None if vertex.id in had else _fold_at(before, vertex.position)
        kind = TemplateTooLongKind.VERTEX if fold is None else TemplateTooLongKind.HOLE_CROSSING
        return TemplateTooLong(kind, vertex.position, number, fold)
    return None


def origin_too_long(position: Vec) -> TemplateTooLong | None:
    number = long_number(position)
    return None if number is None else TemplateTooLong(TemplateTooLongKind.ORIGIN, position, number)


def _fold_at(template: Template, p: Vec) -> Fold | None:
    """The fold `p` lies on, strictly between its ends (where a hole's side crosses it)."""
    for fold in template.folds:
        a, b = template.position(fold.start), template.position(fold.end)
        if p not in (a, b) and on_segment(p, a, b):
            return fold
    return None
