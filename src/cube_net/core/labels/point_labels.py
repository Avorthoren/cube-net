# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`PointLabels`: stable letter names for points of the cube surface (debug labels, docs/idea.txt).

The 8 cube vertices are named A..H as in docs/idea.txt. Every other point (created by cuts) gets the next free
spreadsheet-style name when it is registered: I, J, ..., Z, AA, AB, ... Names are never reused.
"""

from __future__ import annotations

from cube_net.core.cube import VERTICES, SurfacePoint
from cube_net.core.labels.excel import excel_label


class PointLabels:
    def __init__(self) -> None:
        self._names: dict[SurfacePoint, str] = {SurfacePoint.at_vertex(v): v for v in VERTICES}
        self._next = len(VERTICES)
        if [excel_label(i) for i in range(self._next)] != list(VERTICES):
            raise RuntimeError(f"cube vertex labels {VERTICES} must be the first spreadsheet names A, B, ...")

    @classmethod
    def restored(cls, names: dict[SurfacePoint, str], next_index: int) -> PointLabels:
        """The labels `saved` returned the parts of."""
        labels = cls()
        taken = len(labels._names) + len(names)
        if len(set(names.values())) != len(names) or set(names.values()) & set(labels._names.values()):
            raise ValueError("two points have the same name")
        if next_index < taken:
            raise ValueError(f"the next name's number {next_index} is less than the {taken} names there are")
        labels._names.update(names)
        labels._next = next_index
        return labels

    def saved(self) -> tuple[dict[SurfacePoint, str], int]:
        """What makes them differ from new ones: the names of all but the cube vertices, and the next name's number."""
        vertices = {SurfacePoint.at_vertex(v) for v in VERTICES}
        return {p: name for p, name in self._names.items() if p not in vertices}, self._next

    def register(self, point: SurfacePoint) -> str:
        """The name of `point`, assigning the next free one if it has none yet."""
        name = self._names.get(point)
        if name is None:
            name = self._names[point] = excel_label(self._next)
            self._next += 1
        return name

    def upcoming(self, offset: int = 0) -> str:
        """The name `register` would give after `offset` more registrations (nothing is registered)."""
        return excel_label(self._next + offset)

    def name(self, point: SurfacePoint) -> str | None:
        """The name of `point`, or None if it was never registered."""
        return self._names.get(point)
