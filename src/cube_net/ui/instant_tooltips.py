# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`InstantTooltips`: the tooltips of a widget and of everything in it, shown as soon as the mouse is over their widget
and hidden as soon as it leaves (Qt's own wait before showing, and linger after: see `TooltipLabel`)."""

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QWidget

from cube_net.ui.sheet.tooltip_label import TooltipLabel

# What hides the tooltip of the widget it happens to.
_HIDING = (QEvent.Type.Leave, QEvent.Type.Hide, QEvent.Type.Close, QEvent.Type.WindowDeactivate)


class InstantTooltips(QObject):
    def __init__(self, root: QWidget) -> None:
        """For `root` and the widgets in it now (the tooltips' texts may change later: they're read when shown)."""
        super().__init__(root)
        self.label = TooltipLabel(root)
        self._shown_for: QWidget | None = None
        for widget in (root, *root.findChildren(QWidget)):
            if widget is not self.label:
                widget.installEventFilter(self)

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if not isinstance(watched, QWidget) or event is None:
            return False
        kind = event.type()
        if kind == QEvent.Type.ToolTip and watched.toolTip():
            return True  # Qt's own, late one: this one is already shown
        if kind == QEvent.Type.Enter and watched.toolTip():
            self._shown_for = watched
            self.label.show_at(watched.toolTip(), QCursor.pos())
        elif kind in _HIDING and watched is self._shown_for:
            self.hide()
        return False

    def hide(self) -> None:
        self._shown_for = None
        self.label.hide()

    def shown_for(self) -> QWidget | None:
        """The widget whose tooltip is shown, if any."""
        return self._shown_for
