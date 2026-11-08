"""The rules of `History`, as scripts of actions. The state is simply the number of the action that led to it."""

import pytest

from cube_net.core.history import MAX_ACTIONS, ActionKind, History

P = ActionKind.ADD_POINT
D = ActionKind.DELETE_POINT
M = ActionKind.MOVE_POINT
R = ActionKind.REARRANGE
A = ActionKind.APPROVE


# The actions of a script (see `run`).
LETTERS = {"p": P, "d": D, "m": M, "r": R, "a": A}


def run(history: History[int], script: str, start: int = 0) -> int:
    """Play `script`: "p d m r a" record those actions, "!" records a rearrangement that can't be approved, and "z:3" /
    "y:3" undo / redo expecting state 3 ("z:-" and "y:-" expect that there's nothing to do)."""
    state = start
    next_state = start
    for step in script.split():
        if step[0] in "zy":
            got = history.undo() if step[0] == "z" else history.redo()
            expected = step.split(":")[1]
            if expected == "-":
                assert got is None, step
            else:
                assert got == int(expected), step
                assert got is not None
                state = got
        else:
            next_state += 1
            kind, forget = (R, True) if step == "!" else (LETTERS[step], False)
            history.record(kind, state, next_state, forget)
            state = next_state
    return state


@pytest.mark.parametrize(
    "script",
    [
        pytest.param("z:- y:-", id="nothing to undo or redo at first"),
        pytest.param("p z:0 z:-", id="undo one action"),
        pytest.param("p d m z:2 z:1 z:0 z:-", id="actions are undone last to first"),
        pytest.param("p d z:1 z:0 y:1 y:2 y:-", id="redo goes the other way"),
        pytest.param("p z:0 y:1 z:0 y:1", id="back and forth"),
        pytest.param("p d z:1 m y:-", id="a new action forgets what could be redone"),
        pytest.param("p r a z:1", id="undoing an approval also undoes its rearrangement"),
        pytest.param("p r a z:1 z:0 z:-", id="and nothing else"),
        pytest.param("p r a z:1 y:2 y:3 y:-", id="redo after that is one action at a time"),
        pytest.param("p r a z:1 y:2 z:1 y:2 y:3", id="the rearrangement alone back and forth"),
        pytest.param("p r a z:1 y:2 y:3 z:1", id="a redone approval takes its rearrangement along again"),
        pytest.param("p r z:1 y:2 a z:1", id="a rearrangement undone alone, redone and approved"),
        pytest.param("p ! z:1 y:-", id="a rearrangement that can't be approved can't be redone"),
        pytest.param("p d z:1 ! z:1 y:-", id="and what could be redone before it is gone"),
        pytest.param("p r a p r a z:4 z:3 z:1 y:2 y:3 y:4 y:5 y:6 y:-", id="two cuts in a row"),
        pytest.param("p r a p z:3 z:1 z:0", id="the approval comes back alone after the action behind it"),
    ],
)
def test_rules(script: str) -> None:
    run(History(), script)


@pytest.mark.parametrize(
    ("max_actions", "script"),
    [
        pytest.param(3, "p p p p z:3 z:2 z:1 z:-", id="the oldest action is forgotten"),
        pytest.param(3, "r a p p z:3 z:2 z:1 z:-", id="the rearrangement is gone: the approval is undone alone"),
        pytest.param(3, "p r a p z:3 z:1 z:-", id="both still there, and the oldest is the rearrangement"),
        pytest.param(2, "p r a z:1 y:2 y:3 z:1 z:-", id="both exactly fill it"),
        pytest.param(3, "r a p p z:3 z:2 z:1 y:2 y:3 y:4 y:-", id="redo after the trim"),
        pytest.param(3, "p d m z:2 z:1 y:2 y:3 z:2 z:1 z:0 z:-", id="undoing and redoing loses nothing"),
    ],
)
def test_trimming(max_actions: int, script: str) -> None:
    run(History(max_actions), script)


class TestTheRealLimit:
    def test_1000_actions_are_kept(self) -> None:
        assert MAX_ACTIONS == 1000
        history: History[int] = History()
        run(history, "p " * 1001)
        assert history.done_count == 1000
        states = [history.undo() for _ in range(1000)]
        assert states == list(range(1000, 0, -1))
        assert history.undo() is None

    def test_oldest_is_the_rearrangement(self) -> None:
        history: History[int] = History()
        run(history, "r a " + "p " * 998)
        assert history.done_count == 1000
        for _ in range(998):
            history.undo()
        assert history.undo() == 0  # the approval and the rearrangement together
        assert history.undo() is None

    def test_oldest_is_the_approval(self) -> None:
        history: History[int] = History()
        run(history, "r a " + "p " * 999)
        assert history.done_count == 1000
        for _ in range(999):
            history.undo()
        assert history.undo() == 1  # the approval alone: its rearrangement is forgotten
        assert history.undo() is None
        assert history.redo() == 2  # and it can be redone


def test_counts() -> None:
    history: History[int] = History()
    assert (history.can_undo, history.can_redo) == (False, False)
    run(history, "p r a z:1")
    assert (history.can_undo, history.can_redo) == (True, True)
    assert (history.done_count, history.undone_count) == (1, 2)
