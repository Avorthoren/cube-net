# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`PointLabels`: stable letter names for points of a body's surface (debug labels, docs/idea.txt).

The body's vertices have their own names (A..H for the cube, as in docs/idea.txt). Every other point (created by
cuts) gets the first spreadsheet-style name not taken yet when it is registered: for the cube I, J, ..., Z, AA, AB,
... Names are never reused.
"""

from __future__ import annotations

from cube_net.core.body import Body, SurfacePoint
from cube_net.core.labels.excel import excel_label


class PointLabels:
    def __init__(self, body: Body) -> None:
        self._body = body
        self._names: dict[SurfacePoint, str] = {SurfacePoint.at_vertex(body, v): v for v in body.vertex_names}
        self._taken: set[str] = set(self._names.values())
        # The number of the spreadsheet name to try next.
        self._next = 0
        self._skip_taken()

    @classmethod
    def restored(cls, body: Body, names: dict[SurfacePoint, str], next_index: int) -> PointLabels:
        """The labels `saved` returned the parts of."""
        labels = cls(body)
        if len(set(names.values())) != len(names) or set(names.values()) & labels._taken:
            raise ValueError("two points have the same name")
        labels._names.update(names)
        labels._taken.update(names.values())
        if next_index < len(labels._names):
            count = len(labels._names)
            raise ValueError(f"the next name's number {next_index} is less than the {count} names there are")
        labels._next = next_index
        labels._skip_taken()
        return labels

    def saved(self) -> tuple[dict[SurfacePoint, str], int]:
        """What makes them differ from new ones: the names of all but the body's vertices, and the next name's
        number."""
        vertices = {SurfacePoint.at_vertex(self._body, v) for v in self._body.vertex_names}
        return {p: name for p, name in self._names.items() if p not in vertices}, self._next

    def register(self, point: SurfacePoint) -> str:
        """The name of `point`, assigning the next free one if it has none yet."""
        name = self._names.get(point)
        if name is None:
            name = self._names[point] = excel_label(self._next)
            self._taken.add(name)
            self._next += 1
            self._skip_taken()
        return name

    def upcoming(self, offset: int = 0) -> str:
        """The name `register` would give after `offset` more registrations (nothing is registered)."""
        i = self._next
        while True:
            if excel_label(i) not in self._taken:
                if offset == 0:
                    return excel_label(i)
                offset -= 1
            i += 1

    def name(self, point: SurfacePoint) -> str | None:
        """The name of `point`, or None if it was never registered."""
        return self._names.get(point)

    def _skip_taken(self) -> None:
        while excel_label(self._next) in self._taken:
            self._next += 1
