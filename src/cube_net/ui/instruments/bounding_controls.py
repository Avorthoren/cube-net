"""`BoundingControls`: the bounding rectangle's area label and toggle button on the instrument panel (docs/idea.txt).

- The area of the minimum-area bounding rectangle is always shown, with 3 decimals.
- The toggle button shows / hides the rectangle on the sheet.
- When the area is below the project's threshold, the area and the rectangle turn green, and the button blinks:
  regular and fully green in equal parts, 6 changes per second.
"""

from fractions import Fraction

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QToolBar, QWidget

from cube_net.core.bounding import BoundingRectangle
from cube_net.ui import palette
from cube_net.ui.sheet.bounding_item import BoundingItem

# 6 changes per second: 3 times regular, 3 times green.
BLINK_INTERVAL_MS = round(1000 / 6)


def format_area(area: Fraction) -> str:
    return f"{float(area):.3f}"


class BoundingControls(QObject):
    # The rectangle was shown (True) or hidden (False) by the user.
    toggled = pyqtSignal(bool)

    def __init__(self, toolbar: QToolBar, item: BoundingItem) -> None:
        super().__init__(toolbar)
        self._item = item
        self._rectangle: BoundingRectangle | None = None
        self._success = False
        self._blink_on = False

        toolbar.addSeparator()
        self.label = QLabel(toolbar)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setToolTip("Area of the smallest rectangle (any orientation) that contains the net")
        toolbar.addWidget(self.label)
        self.action = QAction("Bounds", toolbar)
        self.action.setCheckable(True)
        self.action.setShortcut("B")
        self.action.setToolTip("Show the smallest bounding rectangle (B)")
        self.action.toggled.connect(self._on_toggled)
        toolbar.addAction(self.action)
        self.button: QWidget | None = toolbar.widgetForAction(self.action)

        self._timer = QTimer(self)
        self._timer.setInterval(BLINK_INTERVAL_MS)
        self._timer.timeout.connect(self._blink)

    @property
    def success(self) -> bool:
        return self._success

    @property
    def blinking(self) -> bool:
        return self._timer.isActive()

    def update(self, rectangle: BoundingRectangle, threshold: Fraction) -> None:
        """Show the area of `rectangle` and react to whether it's below `threshold`."""
        self._rectangle = rectangle
        self._success = rectangle.area < threshold
        self.label.setText(f"Area\n{format_area(rectangle.area)}")
        self.label.setStyleSheet(f"color: {palette.SUCCESS.name()}; font-weight: bold;" if self._success else "")
        if self._success and not self._timer.isActive():
            self._timer.start()
        elif not self._success and self._timer.isActive():
            self._timer.stop()
            self._set_blink(False)
        self._refresh_item()

    def _on_toggled(self, checked: bool) -> None:
        self._refresh_item()
        self.toggled.emit(checked)

    def _refresh_item(self) -> None:
        show = self.action.isChecked() and self._rectangle is not None
        corners = self._rectangle.corners if show and self._rectangle is not None else None
        self._item.set_rectangle(corners, self._success)

    def _blink(self) -> None:
        self._set_blink(not self._blink_on)

    def _set_blink(self, on: bool) -> None:
        self._blink_on = on
        if self.button is not None:
            green = palette.SUCCESS.name()
            self.button.setStyleSheet(f"background-color: {green}; border: 1px solid {green};" if on else "")
