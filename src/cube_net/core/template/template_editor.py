# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`TemplateEditor`: making a template, action by action, with undo and redo (docs/template_idea.txt).

INITIAL       a point anywhere on the sheet   -> the loop's first vertex -> LOOPING
LOOPING       a point                         -> the next vertex (if its segment touches nothing)
              the first vertex again          -> the loop closed (3 segments at least) -> FINALIZATION
FINALIZATION  a side's middle                 -> a new vertex there
              delete a vertex                 -> (6 stay at least; its folds go with it)
              move a vertex                   -> (if the loop and the folds stay as they must)
              a vertex to another             -> a fold
              delete a fold; colour a face; label a vertex

Every action is recorded in the history (at most 1000 are kept); undo and redo go back and forth through them. What
changes nothing isn't an action. The editor never touches Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from cube_net.core.geometry import Vec
from cube_net.core.history import ActionKind, History
from cube_net.core.origin import DEFAULT_ORIGIN, Origin
from cube_net.core.template.rules import (
    MIN_VERTICES,
    MIN_VERTICES_TO_CLOSE,
    TemplateProblem,
    TemplateRejection,
    check,
    fold_problem,
    on_the_sheet,
)
from cube_net.core.template.template import Fold, Label, Template
from cube_net.core.template.validation import reindexed


class TemplateState(Enum):
    INITIAL = "initial"
    LOOPING = "looping"
    FINALIZATION = "finalization"


@dataclass(frozen=True, slots=True)
class TemplateSnapshot:
    """Everything an action changes (what the history keeps, and what's saved)."""

    template: Template
    origin: Origin = DEFAULT_ORIGIN


class TemplateEditor:
    def __init__(self, template: Template | None = None) -> None:
        self.template = Template() if template is None else template
        self.origin = DEFAULT_ORIGIN
        self.history: History[TemplateSnapshot] = History()

    @property
    def state(self) -> TemplateState:
        if self.template.closed:
            return TemplateState.FINALIZATION
        return TemplateState.LOOPING if self.template.vertices else TemplateState.INITIAL

    def snapshot(self) -> TemplateSnapshot:
        return TemplateSnapshot(self.template, self.origin)

    def load(self, snapshot: TemplateSnapshot, history: History[TemplateSnapshot]) -> None:
        """Continue a saved template."""
        self.template, self.origin = snapshot.template, snapshot.origin
        self.history = history

    # --- the loop -----------------------------------------------------------------------------------------------------

    def add_point(self, p: Vec) -> TemplateRejection | None:
        """The loop's next vertex at `p`; at its first vertex, the loop is closed."""
        if self.template.closed:
            raise ValueError("the loop is closed")
        if not on_the_sheet(p):
            return TemplateRejection(TemplateProblem.OFF_THE_SHEET)
        vertices = self.template.vertices
        if vertices and p == vertices[0].position:
            if len(vertices) < MIN_VERTICES_TO_CLOSE:
                return TemplateRejection(TemplateProblem.TOO_EARLY_TO_CLOSE)
            closed = self.template.closed_loop()
            return self._apply(ActionKind.ADD_VERTEX, closed, [(vertices[-1].id, vertices[0].id)])
        if vertices and p == vertices[-1].position:
            return TemplateRejection(TemplateProblem.CROSSING)  # a segment of no length
        after = self.template.with_vertex_appended(p)
        changed = [(vertices[-1].id, after.vertices[-1].id)] if vertices else []
        return self._apply(ActionKind.ADD_VERTEX, after, changed)

    def insert_vertex(self, a: int, b: int) -> None:
        """A new vertex in the middle of the loop's side from `a` to `b` (always allowed)."""
        self._require_closed()
        middle = (self.template.position(a) + self.template.position(b)) / 2
        self._record(ActionKind.ADD_VERTEX, self.template.with_vertex_inserted(a, b, middle))

    def move_problem(self, vertex_id: int, p: Vec) -> TemplateRejection | None:
        """What would be wrong with the vertex at `p` (None: nothing), without moving it."""
        if not on_the_sheet(p):
            return TemplateRejection(TemplateProblem.OFF_THE_SHEET)
        after = self.template.with_vertex_moved(vertex_id, p)
        return check(after, self._segments_at(after, vertex_id))

    def move_vertex(self, vertex_id: int, p: Vec) -> TemplateRejection | None:
        self._require_closed()
        if p == self.template.position(vertex_id):
            return None  # released where it was: not an action
        problem = self.move_problem(vertex_id, p)
        if problem is None:
            self._record(ActionKind.MOVE_VERTEX, self.template.with_vertex_moved(vertex_id, p))
        return problem

    def delete_vertex(self, vertex_id: int) -> TemplateRejection | None:
        """Delete a vertex: its two sides become one, and the folds that end at it go too."""
        self._require_closed()
        if len(self.template.vertices) <= MIN_VERTICES:
            return TemplateRejection(TemplateProblem.TOO_FEW_VERTICES)
        i = self.template.index_of(vertex_id)
        vertices = self.template.vertices
        before, after_id = vertices[i - 1].id, vertices[(i + 1) % len(vertices)].id
        after = self.template.without_vertex(vertex_id)
        return self._apply(ActionKind.DELETE_VERTEX, after, [(before, after_id)])

    # --- folds, colours, labels ---------------------------------------------------------------------------------------

    def add_fold(self, start: int, end: int) -> TemplateRejection | None:
        self._require_closed()
        problem = fold_problem(self.template, start, end) or check(
            replace(self.template, folds=(*self.template.folds, Fold(start, end))), [(start, end)]
        )  # where it goes first: one that crosses another fold has no face to divide
        if problem is None:
            self._record(ActionKind.ADD_FOLD, self.template.with_fold(start, end))
        return problem

    def delete_fold(self, fold: Fold) -> None:
        self._require_closed()
        self._record(ActionKind.DELETE_FOLD, self.template.without_fold(fold))

    def set_face_color(self, face_index: int, color: str) -> None:
        self._require_closed()
        if self.template.faces[face_index].color != color:
            self._record(ActionKind.SET_FACE_COLOR, self.template.with_face_color(face_index, color))

    def set_label(self, vertex_id: int, label: Label | None) -> TemplateRejection | None:
        """Give a vertex a label (None: take its label away). Another vertex's label can't be taken."""
        if label is not None:
            owner = self.template.label_owner(label)
            if owner is not None and owner.id != vertex_id:
                return TemplateRejection(TemplateProblem.LABEL_TAKEN)
        if self.template.vertex(vertex_id).label != label:
            self._record(ActionKind.SET_LABEL, self.template.with_label(vertex_id, label))
        return None

    def reindex(self) -> None:
        """Every name's indices made 1, 2, 3, ... in their order (validation's offer): one action."""
        after = reindexed(self.template)
        if after != self.template:
            self._record(ActionKind.SET_LABEL, after)

    # --- the origin, undo and redo ------------------------------------------------------------------------------------

    def move_origin(self, origin: Origin) -> None:
        if origin != self.origin:
            before = self.snapshot()
            self.origin = origin
            self.history.record(ActionKind.MOVE_ORIGIN, before, self.snapshot())

    def undo(self) -> bool:
        return self._go_to(self.history.undo())

    def redo(self) -> bool:
        return self._go_to(self.history.redo())

    # --- helpers ------------------------------------------------------------------------------------------------------

    def _go_to(self, snapshot: TemplateSnapshot | None) -> bool:
        if snapshot is None:
            return False
        self.template, self.origin = snapshot.template, snapshot.origin
        return True

    def _apply(self, kind: ActionKind, after: Template, changed: list[tuple[int, int]]) -> TemplateRejection | None:
        problem = check(after, changed)
        if problem is None:
            self._record(kind, after)
        return problem

    def _record(self, kind: ActionKind, after: Template) -> None:
        before = self.snapshot()
        self.template = after
        self.history.record(kind, before, self.snapshot())

    def _require_closed(self) -> None:
        if not self.template.closed:
            raise ValueError("the loop isn't closed yet")

    @staticmethod
    def _segments_at(template: Template, vertex_id: int) -> list[tuple[int, int]]:
        """The loop's sides and the folds that end at a vertex."""
        sides = [side for side in template.loop_sides() if vertex_id in side]
        return sides + [(f.start, f.end) for f in template.folds_at(vertex_id)]
