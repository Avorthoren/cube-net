"""`DemoPlayer`: an animation of Help -> Help with its play and replay button.

Before it's played, it shows its first picture with a play button in the middle. Played, it runs its script; after
the end, nothing changes for `STILL_MS`, then a replay button appears, which starts it again from the beginning. An
animation may begin where others end: their scripts (`before`) are run at once first.
"""

from collections.abc import Iterator, Sequence
from enum import Enum

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtWidgets import QFrame, QGridLayout, QWidget

from cube_net.core.geometry import Box
from cube_net.ui.help.demo.demo_sheet import AROUND_THE_NET, DemoSheet
from cube_net.ui.help.demo.round_button import RoundButton, Symbol
from cube_net.ui.help.demo.steps import Move, Step

# How long the last picture stays before the replay button appears (ms).
STILL_MS = 2000

# The size of an animation's sheet (px), unless it says otherwise.
DEFAULT_SIZE = QSize(560, 400)

# The thin frame around an animation.
BORDER = "#DADCE0"


class PlayerState(Enum):
    # The first picture, with the play button.
    READY = "ready"

    # Playing.
    PLAYING = "playing"

    # Over: the last picture, and after a while the replay button.
    ENDED = "ended"


class DemoPlayer(QFrame):
    def __init__(
        self,
        steps: Sequence[Step],
        before: Sequence[Sequence[Step]] = (),
        size: QSize = DEFAULT_SIZE,
        shown: Box = AROUND_THE_NET,
        labels: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """`labels`: whether the vertices have their debug labels (an app setting)."""
        super().__init__(parent)
        self.setObjectName("demo")
        self.setStyleSheet(f"#demo {{ border: 1px solid {BORDER}; border-radius: 6px; }}")
        self._steps = list(steps)
        self._before = [list(part) for part in before]
        self._size = size
        self._shown = shown
        self._labels = labels
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(1, 1, 1, 1)
        self.sheet: DemoSheet = self._new_sheet()
        self.button = RoundButton(self)
        self.button.clicked.connect(self.play)
        self._layout.addWidget(self.button, 0, 0, Qt.AlignmentFlag.AlignCenter)  # over the sheet
        self._run: Iterator[int] | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._next)
        self._state = PlayerState.READY

    def state(self) -> PlayerState:
        return self._state

    def play(self) -> None:
        """From the beginning (if it has been played already, on a fresh sheet)."""
        if self._state is PlayerState.ENDED:
            old = self.sheet
            self.sheet = self._new_sheet()
            old.deleteLater()
            self.button.raise_()
        self._timer.stop()
        self.button.hide()
        self._state = PlayerState.PLAYING
        self._run = self.sheet.play(self._steps)
        self._next()

    def set_labels_shown(self, shown: bool) -> None:
        self._labels = shown
        self.sheet.set_labels_shown(shown)

    def restyle(self) -> None:
        self.sheet.restyle()

    def _new_sheet(self) -> DemoSheet:
        sheet = DemoSheet(self._size, self._shown, self._labels, self)
        for part in self._before:
            for _ in sheet.play(part, instant=True):
                pass
        first = self._steps[0] if self._steps else None
        if sheet.mouse() is None and isinstance(first, Move):
            sheet.place(first.to)  # the mouse is where the script starts, from the first picture on
        self._layout.addWidget(sheet, 0, 0)
        sheet.show()
        return sheet

    def _next(self) -> None:
        if self._run is None:  # the end has been still long enough
            self.button.set_symbol(Symbol.REPLAY)
            self.button.show()
            self.button.raise_()
            return
        try:
            delay = next(self._run)
        except StopIteration:
            self._run = None
            self._state = PlayerState.ENDED
            self._timer.start(STILL_MS)
            return
        self._timer.start(delay)
