# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The look of the net and the sheet the user can change (Settings -> Style): an app setting, not a project's one."""

from cube_net.ui.style.apply import apply_style
from cube_net.ui.style.style import DEFAULT_STYLE, Style, StyleError

__all__ = ["DEFAULT_STYLE", "Style", "StyleError", "apply_style"]
