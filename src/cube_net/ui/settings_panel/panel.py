"""`SettingsPanel`: the tabs of the settings, over the right side of the sheet (docs/idea.txt, settings).

It's a child of the main window placed over the sheet, so the sheet doesn't move when it opens or closes, and the rest
of the sheet works as usual. It takes at most a third of the screen's width; tabs scroll when they don't fit.
"""

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFrame, QScrollArea, QTabWidget, QVBoxLayout, QWidget

from cube_net.ui.settings_panel.preferences_tab import PreferencesTab
from cube_net.ui.settings_panel.style_tab import StyleTab
from cube_net.ui.style import Style

# The panel takes at most this part of the screen's width.
MAX_SCREEN_FRACTION = 1 / 3

# Room for a vertical scroll bar, so that it never covers the fields.
SCROLL_BAR_ROOM_PX = 24


def _scrolling(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidget(widget)
    return area


class SettingsPanel(QFrame):
    def __init__(
        self, labels: QAction, logs: QAction, blink: bool, max_zoom: int, style: Style, parent: QWidget
    ) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)
        self.preferences = PreferencesTab(labels, logs, blink, max_zoom)
        self.style_tab = StyleTab(style)
        self.tabs = QTabWidget(self)
        self.tabs.addTab(_scrolling(self.preferences), "Preferences")
        self.tabs.addTab(_scrolling(self.style_tab), "Style")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.tabs)
        self.hide()

    def place_over(self, area: QRect, screen_width: int) -> None:
        """Take the right side of `area` (the sheet, in the parent's coordinates): as wide as the tabs need, but at most
        a third of the screen."""
        wanted = max(self.preferences.sizeHint().width(), self.style_tab.sizeHint().width()) + SCROLL_BAR_ROOM_PX + 8
        width = min(wanted, int(screen_width * MAX_SCREEN_FRACTION), area.width())
        self.setGeometry(QRect(area.right() + 1 - width, area.top(), width, area.height()))
        self.raise_()
