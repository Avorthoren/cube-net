# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""How the instrument panel's buttons look: like buttons, outlined and raised, before the mouse is over them too
(the system's style draws them flat until then, so they didn't look like buttons). Pressed, or switched on (the
Ruler, the Bounds), they look pushed in. Colours: `palette.TOOL_BUTTON_*`."""

from cube_net.ui import palette

# The corners' radius and the room inside the outline (px).
RADIUS_PX = 4
PADDING = "3px 6px"


def _gradient(top: str, bottom: str) -> str:
    return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {top}, stop:1 {bottom})"


def tool_buttons_style() -> str:
    """The style sheet of the panel (it styles its buttons)."""
    top, bottom = palette.TOOL_BUTTON_TOP.name(), palette.TOOL_BUTTON_BOTTOM.name()
    hover = palette.TOOL_BUTTON_HOVER_BOTTOM.name()
    down_top, down_bottom = palette.TOOL_BUTTON_DOWN_TOP.name(), palette.TOOL_BUTTON_DOWN_BOTTOM.name()
    return f"""
        QToolButton {{
            border: 1px solid {palette.TOOL_BUTTON_BORDER.name()};
            border-radius: {RADIUS_PX}px;
            padding: {PADDING};
            margin: 2px;
            background: {_gradient(top, bottom)};
        }}
        QToolButton:hover {{
            border-color: {palette.TOOL_BUTTON_HOVER_BORDER.name()};
            background: {_gradient(top, hover)};
        }}
        QToolButton:pressed, QToolButton:checked {{
            border-color: {palette.TOOL_BUTTON_DOWN_BORDER.name()};
            background: {_gradient(down_top, down_bottom)};
        }}
    """
