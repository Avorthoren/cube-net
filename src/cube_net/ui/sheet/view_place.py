# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`ViewPlace`: where a sheet's view is: the sheet point at its window's top left corner (outside the view: it's
the sheet as the window shows it, wherever the view is in it), and its zoom. The window keeps the sheet in place on
the screen when the view moves or changes size in it (the instrument panel next to it gets wider, say), and so does
the place. The app keeps the last one (`AppSettings.last_view`), so that it shows the file it reopens as the user left
it."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ViewPlace:
    # The sheet point at the window's top left corner (units).
    x: float
    y: float

    # The zoom: screen pixels per unit.
    scale: float


@dataclass(frozen=True, slots=True)
class LastView:
    """Where the view was when the app was closed, and the file that was shown (it's used only for that one)."""

    # The project's or the template's file.
    path: Path

    place: ViewPlace
