# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The hotkeys of the application, for Help -> Help: every key and mouse gesture of its own (not those of its windows'
fields and buttons), grouped by what they're for. A key can be in two groups, when it does something else in each.

The keys are written as Qt's portable key sequences ("Ctrl+N") and shown the system's way (on macOS, ⌘N). A test checks
that every shortcut of the application is here.
"""

from dataclasses import dataclass

from PyQt6.QtGui import QKeySequence

from cube_net.ui.i18n import tr


@dataclass(frozen=True)
class Hotkey:
    # What to press, as a portable key sequence ("Ctrl+Shift+S"), or a modifier held with
    # `mouse` ("Shift"); "" for the mouse alone.
    keys: str

    # What the mouse does (English, translated when shown): "click a vertex", "right-click"...; "" for keys alone.
    mouse: str

    # What it does (English, translated when shown).
    action: str

    # The modifier `keys` is held (no mouse): "hold Shift".
    held: bool = False

    def shown(self) -> str:
        """How it's written in the help, in the current language and the system's way."""
        if self.held:
            return tr("hold {key}", key=native_modifier(self.keys))
        if not self.mouse:
            return native(self.keys)
        if not self.keys:
            return tr(self.mouse)
        return f"{native_modifier(self.keys)} + {tr(self.mouse)}"


@dataclass(frozen=True)
class HotkeyGroup:
    # Its title (English, translated when shown).
    title: str

    hotkeys: tuple[Hotkey, ...]


def native(keys: str) -> str:
    """A key sequence as the system writes it (Ctrl+N; on macOS, ⌘N)."""
    return QKeySequence(keys).toString(QKeySequence.SequenceFormat.NativeText)


def native_modifier(modifier: str) -> str:
    """A modifier key alone ("Shift", "Ctrl") as the system writes it (on macOS, ⇧ and ⌘)."""
    with_key = native(f"{modifier}+A")
    return with_key[: -len("A")].rstrip("+")


# Unlocking a slope set with Set slope: while cutting and while dragging.
_UNLOCK = Hotkey("Esc", "", "Unlock the slope set with Set slope")

HOTKEYS = (
    HotkeyGroup(
        "Projects",
        (
            Hotkey("Ctrl+N", "", "New project"),
            Hotkey("Ctrl+O", "", "Open a project"),
            Hotkey("Ctrl+S", "", "Save the project"),
            Hotkey("Ctrl+Shift+S", "", "Save it under another name"),
            Hotkey("Ctrl+Q", "", "Quit"),
        ),
    ),
    HotkeyGroup(
        "Undo and redo",
        (
            Hotkey("Ctrl+Z", "", "Undo the last action"),
            Hotkey("Ctrl+Y", "", "Redo it"),
        ),
    ),
    HotkeyGroup(
        "Making a cut",
        (
            Hotkey("Shift", "", "The new segment is horizontal or vertical", held=True),
            _UNLOCK,
        ),
    ),
    HotkeyGroup(
        "Adjusting the cut",
        (
            Hotkey("Shift", "drag a vertex", "The segment from the vertex before it is horizontal or vertical"),
            Hotkey("Ctrl", "click a vertex", "Delete it (any but the first and the last)"),
            _UNLOCK,
        ),
    ),
    HotkeyGroup(
        "Gluing",
        (Hotkey("Ctrl+Enter", "", "Approve the rearranged net (when its halves don't overlap)"),),
    ),
    HotkeyGroup(
        "Instruments",
        (
            Hotkey("R", "", "Switch the ruler on or off (off, it forgets its points)"),
            Hotkey(
                "Shift",
                "",
                "While measuring: the ruler's segment is horizontal or vertical; the next ones, parallel or "
                "perpendicular to the one before",
                held=True,
            ),
            Hotkey("B", "", "Show or hide the smallest bounding rectangle"),
        ),
    ),
    HotkeyGroup(
        "The view",
        (
            Hotkey("", "mouse wheel", "Zoom in or out"),
            Hotkey("", "drag the sheet", "Move the sheet"),
            Hotkey("L", "", "Show or hide the vertex labels"),
            Hotkey("C", "", "Show or hide the vertex coordinates"),
            Hotkey("Ctrl+C", "", "Copy the coordinates shown next to the mouse"),
        ),
    ),
    HotkeyGroup(
        "Help",
        (
            Hotkey("F1", "", "This help"),
            Hotkey("Esc", "", "Close it"),
        ),
    ),
)
