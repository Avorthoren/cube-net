# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`SettingsPanel`: the tabs of the settings, over the right side of the sheet (docs/idea.txt, settings).

It's a child of the main window placed over the sheet, so the sheet doesn't move when it opens or closes, and the rest
of the sheet works as usual. It takes at most a third of the screen's width; tabs scroll when they don't fit.
"""

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFrame, QScrollArea, QTabWidget, QToolButton, QVBoxLayout, QWidget

from cube_net.ui.i18n import Language, bind
from cube_net.ui.settings_panel.preferences_tab import PreferencesTab
from cube_net.ui.settings_panel.style_tab import StyleTab
from cube_net.ui.style import Style

# The panel takes at most this part of the screen's width.
MAX_SCREEN_FRACTION = 1 / 3

# On the button that hides the panel: a double chevron pointing the way the panel goes (not a cross, which would look
# like closing the application).
HIDE_SIGN = chr(0x00BB)

# The tabs' keys: how the last one shown is remembered, in any language.
PREFERENCES = "preferences"
STYLE = "style"

# Room for a vertical scroll bar, so that it never covers the fields.
SCROLL_BAR_ROOM_PX = 24


def _scrolling(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidget(widget)
    return area


class SettingsPanel(QFrame):
    # The user clicked the button that hides the panel (it's up to the window, as with Settings in the menu bar).
    hide_requested = pyqtSignal()

    def __init__(
        self,
        labels: QAction,
        logs: QAction,
        blink: bool,
        max_zoom: int,
        style: Style,
        parent: QWidget,
        language: Language = Language.ENGLISH,
        menu_entry: QAction | None = None,
        check_updates: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)
        self.preferences = PreferencesTab(
            labels,
            logs,
            blink,
            max_zoom,
            check_updates=check_updates,
            language=language,
            menu_entry=menu_entry,
        )
        self.style_tab = StyleTab(style)
        self.tabs = QTabWidget(self)
        self._add_tab(PREFERENCES, self.preferences)
        bind(self.tabs, lambda text: self.tabs.setTabText(0, text), "Preferences")
        self._add_tab(STYLE, self.style_tab)
        bind(self.tabs, lambda text: self.tabs.setTabText(1, text), "Style")
        self.hide_button = QToolButton(self.tabs)
        self.hide_button.setText(HIDE_SIGN)
        bind(self.hide_button, self.hide_button.setToolTip, "Hide settings")
        self.hide_button.setAutoRaise(True)
        self.hide_button.clicked.connect(self.hide_requested)
        self.tabs.setCornerWidget(self.hide_button, Qt.Corner.TopRightCorner)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.tabs)
        self.hide()

    def _add_tab(self, key: str, tab: QWidget) -> None:
        index = self.tabs.addTab(_scrolling(tab), "")
        page = self.tabs.widget(index)
        assert page is not None
        page.setObjectName(key)

    def tab_name(self) -> str:
        """The shown tab's key (the same in every language)."""
        widget = self.tabs.currentWidget()
        return widget.objectName() if widget is not None else ""

    def show_tab(self, name: str) -> None:
        """Show the tab with this key; an unknown one changes nothing. (Earlier versions kept the tab's English title,
        which is its key with a capital letter.)"""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if widget is not None and widget.objectName() == name.lower():
                self.tabs.setCurrentIndex(i)

    def place_over(self, area: QRect, screen_width: int) -> None:
        """Take the right side of `area` (the sheet, in the parent's coordinates): as wide as the tabs need, but at most
        a third of the screen."""
        wanted = max(self.preferences.sizeHint().width(), self.style_tab.sizeHint().width()) + SCROLL_BAR_ROOM_PX + 8
        width = min(wanted, int(screen_width * MAX_SCREEN_FRACTION), area.width())
        self.setGeometry(QRect(area.right() + 1 - width, area.top(), width, area.height()))
        self.raise_()
