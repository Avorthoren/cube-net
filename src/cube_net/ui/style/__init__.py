# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The look of the net and the sheet the user can change (Settings -> Style): the open document's (a project's or a
template's), put in place for everything that paints."""

from cube_net.core.style import Style, StyleError
from cube_net.ui.style.apply import apply_style
from cube_net.ui.style.default_style import DEFAULT_STYLE, fitted

__all__ = ["DEFAULT_STYLE", "Style", "StyleError", "apply_style", "fitted"]
