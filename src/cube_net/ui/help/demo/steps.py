# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The steps of an animation's script: what the mouse and the keys do, in sheet coordinates (units)."""

from dataclasses import dataclass

from PyQt6.QtCore import Qt

# A point on the sheet.
type Point = tuple[float, float]


@dataclass(frozen=True)
class Move:
    """The mouse goes to `to` (through the points of `via` first, in straight lines), in `ms` milliseconds."""

    to: Point
    ms: int = 700
    via: tuple[Point, ...] = ()


@dataclass(frozen=True)
class Press:
    """The left mouse button goes down where the mouse is."""


@dataclass(frozen=True)
class Release:
    """The left mouse button goes up where the mouse is."""


@dataclass(frozen=True)
class Keys:
    """These modifier keys are held from now on (`NoModifier`: none)."""

    modifiers: Qt.KeyboardModifier


@dataclass(frozen=True)
class RightClick:
    """A right click where the mouse is: the sheet's menu opens there, with the items it has at that spot."""


@dataclass(frozen=True)
class ToItem:
    """The mouse goes to item `item` of the open menu (its index), in `ms` milliseconds."""

    item: int
    ms: int = 500


@dataclass(frozen=True)
class Type:
    """Keys are typed into the open window, one every `ms` milliseconds: the characters of `text` (a tab goes to the
    next field, a line break is Enter)."""

    text: str
    ms: int = 220


@dataclass(frozen=True)
class DoubleClick:
    """A double click where the mouse is (a template's face: its colour)."""


@dataclass(frozen=True)
class Paste:
    """`text` pasted into the open window at once (Ctrl+V): into the field with the focus, in place of its selected
    text (a colour window without one: its colour)."""

    text: str


@dataclass(frozen=True)
class ToWidget:
    """The mouse goes to the middle of a widget by its name (`DRAW_HOLE`, `VALIDATE`, `COLOR_CODE`), in `ms`
    milliseconds."""

    name: str
    ms: int = 700


@dataclass(frozen=True)
class Wait:
    """Nothing happens for `ms` milliseconds."""

    ms: int


type Step = Move | Press | Release | Keys | RightClick | ToItem | Type | DoubleClick | Paste | ToWidget | Wait

# How long the mouse button stays down in a click.
CLICK_MS = 110


def click() -> list[Step]:
    """A click where the mouse is."""
    return [Press(), Wait(CLICK_MS), Release()]


# The widgets the mouse goes to by name (`ToWidget`): the buttons of a template's instrument panel (Validate, Draw
# hole), and the colour's code ("#RRGGBB") in the colour window.
VALIDATE = "validate"
DRAW_HOLE = "draw hole"
COLOR_CODE = "color code"
