# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The steps of an animation's script: what the mouse and the modifier keys do, in sheet coordinates (units)."""

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
class Wait:
    """Nothing happens for `ms` milliseconds."""

    ms: int


type Step = Move | Press | Release | Keys | Wait

# How long the mouse button stays down in a click.
CLICK_MS = 110


def click() -> list[Step]:
    """A click where the mouse is."""
    return [Press(), Wait(CLICK_MS), Release()]
