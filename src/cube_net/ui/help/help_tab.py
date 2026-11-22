# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`HelpTab`: the tabs of Help -> Help, in their order (the value is what the settings keep of the one shown last)."""

from __future__ import annotations

from enum import Enum


class HelpTab(Enum):
    NETWORK = "network"
    TEMPLATE = "template"
    HOTKEYS = "hotkeys"

    @classmethod
    def named(cls, value: str) -> HelpTab:
        """The tab of this value; the first one for any other (none kept yet, or one that's gone)."""
        return next((tab for tab in cls if tab.value == value), cls.NETWORK)
