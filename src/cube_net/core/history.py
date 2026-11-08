"""`History`: undo and redo (docs/idea.txt, the actions list; docs/plan.md, section 5.2).

- At most `MAX_ACTIONS` actions are kept; the oldest ones are forgotten.
- A new action forgets everything that could have been redone.
- Undoing an approval also undoes the rearrangement before it, if that is still in the history.
- A rearrangement that can't be approved is forgotten when it's undone: it can't be redone.
- Redo always redoes exactly one action.

An entry holds the state before and after the action, whatever the owner uses as a state.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

# How many actions are kept (docs/idea.txt).
MAX_ACTIONS = 1000


class ActionKind(Enum):
    ADD_POINT = "add point"
    DELETE_POINT = "delete point"
    MOVE_POINT = "move point"
    REARRANGE = "rearrange"
    APPROVE = "approve"


@dataclass(frozen=True, slots=True)
class HistoryEntry[State]:
    kind: ActionKind
    before: State
    after: State

    # Undoing this action forgets it: it can't be redone.
    forget_on_undo: bool = False


class History[State]:
    def __init__(self, max_actions: int = MAX_ACTIONS) -> None:
        self._done: deque[HistoryEntry[State]] = deque(maxlen=max_actions)
        self._undone: list[HistoryEntry[State]] = []

    @classmethod
    def restored(
        cls, done: Iterable[HistoryEntry[State]], undone: Iterable[HistoryEntry[State]], max_actions: int = MAX_ACTIONS
    ) -> History[State]:
        """A history with these entries (`done_entries` and `undone_entries` of a saved one)."""
        history: History[State] = cls(max_actions)
        history._done.extend(done)
        history._undone.extend(undone)
        return history

    def done_entries(self) -> tuple[HistoryEntry[State], ...]:
        return tuple(self._done)

    def undone_entries(self) -> tuple[HistoryEntry[State], ...]:
        return tuple(self._undone)

    @property
    def can_undo(self) -> bool:
        return bool(self._done)

    @property
    def can_redo(self) -> bool:
        return bool(self._undone)

    @property
    def done_count(self) -> int:
        return len(self._done)

    @property
    def undone_count(self) -> int:
        return len(self._undone)

    def record(self, kind: ActionKind, before: State, after: State, forget_on_undo: bool = False) -> None:
        self._done.append(HistoryEntry(kind, before, after, forget_on_undo))
        self._undone.clear()

    def undo(self) -> State | None:
        """The state to go back to, or None if there's nothing to undo."""
        if not self._done:
            return None
        entry = self._undo_one()
        if entry.kind is ActionKind.APPROVE and self._done and self._done[-1].kind is ActionKind.REARRANGE:
            entry = self._undo_one()
        return entry.before

    def redo(self) -> State | None:
        """The state after the action just redone, or None if there's nothing to redo."""
        if not self._undone:
            return None
        entry = self._undone.pop()
        self._done.append(entry)
        return entry.after

    def _undo_one(self) -> HistoryEntry[State]:
        entry = self._done.pop()
        if not entry.forget_on_undo:
            self._undone.append(entry)
        return entry
