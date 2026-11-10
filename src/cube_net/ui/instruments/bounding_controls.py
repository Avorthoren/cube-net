"""`BoundingControls`: the bounding rectangle's area label and toggle button on the instrument panel (docs/idea.txt).

- The area of the minimum-area bounding rectangle is always shown, with 3 decimals.
- The toggle button shows / hides the rectangle on the sheet.
- Below the area: the project's target area, which the user can edit there.
- When the area is below the project's threshold, the area and the rectangle turn green, and the button blinks:
  regular and fully green in equal parts, 6 changes per second. Or, if the user switched blinking off, the button is
  just green all the time.
"""

from fractions import Fraction

from PyQt6.QtCore import QLocale, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDoubleSpinBox, QLabel, QToolBar, QWidget

from cube_net.core.bounding import BoundingRectangle
from cube_net.core.project_settings import MAX_AREA_THRESHOLD, MIN_AREA_THRESHOLD
from cube_net.ui import palette
from cube_net.ui.i18n import TRANSLATIONS, bind, tr
from cube_net.ui.sheet.bounding_item import BoundingItem

# The target area has at most 3 decimals; the field's arrows change it by this much.
TARGET_DECIMALS = 3
TARGET_STEP = 0.1

# 6 changes per second: 3 times regular, 3 times green.
BLINK_INTERVAL_MS = round(1000 / 6)


def format_area(area: Fraction) -> str:
    return f"{float(area):.3f}"


class BoundingControls(QObject):
    # The rectangle was shown (True) or hidden (False) by the user.
    toggled = pyqtSignal(bool)

    # The user entered another target area (a Fraction with at most 3 decimals).
    target_changed = pyqtSignal(object)

    def __init__(self, toolbar: QToolBar, item: BoundingItem) -> None:
        super().__init__(toolbar)
        self._item = item
        self._rectangle: BoundingRectangle | None = None
        self._success = False
        self._blink_on = False
        self._blink_enabled = True

        toolbar.addSeparator()
        self.label = QLabel(toolbar)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bind(
            self.label, self.label.setToolTip, "Area of the smallest rectangle (any orientation) that contains the net"
        )
        toolbar.addWidget(self.label)
        self.target_label = QLabel(toolbar)
        bind(self.target_label, self.target_label.setText, "Target area")
        self.target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.target_label)
        self.target = QDoubleSpinBox(toolbar)
        self.target.setLocale(QLocale.c())  # always 7.100, never 7,100
        self.target.setDecimals(TARGET_DECIMALS)
        self.target.setRange(float(MIN_AREA_THRESHOLD), float(MAX_AREA_THRESHOLD))
        self.target.setSingleStep(TARGET_STEP)
        self.target.setKeyboardTracking(False)  # a value is taken when it's entered, not at every digit typed
        bind(self.target, self.target.setToolTip, "The project's goal: an area below this is a success")
        self.target.valueChanged.connect(self._on_target)
        toolbar.addWidget(self.target)
        self.action = QAction(toolbar)
        bind(self.action, self.action.setText, "Bounds")
        self.action.setCheckable(True)
        self.action.setShortcut("B")
        bind(self.action, self.action.setToolTip, "Show the smallest bounding rectangle (B)")
        self.action.toggled.connect(self._on_toggled)
        toolbar.addAction(self.action)
        self.button: QWidget | None = toolbar.widgetForAction(self.action)

        TRANSLATIONS.changed.connect(self._show_area)
        self._timer = QTimer(self)
        self._timer.setInterval(BLINK_INTERVAL_MS)
        self._timer.timeout.connect(self._blink)

    @property
    def success(self) -> bool:
        return self._success

    @property
    def blinking(self) -> bool:
        return self._timer.isActive()

    def set_blink_enabled(self, enabled: bool) -> None:
        """Whether the button blinks on success; if it doesn't, it's just green while the area is below the target."""
        self._blink_enabled = enabled
        self._show_success()

    def set_target(self, threshold: Fraction) -> None:
        """Show this target area (without taking that for a change by the user)."""
        self.target.blockSignals(True)
        self.target.setValue(float(threshold))
        self.target.blockSignals(False)

    def _on_target(self, value: float) -> None:
        scale = 10**TARGET_DECIMALS
        self.target_changed.emit(Fraction(round(value * scale), scale))

    def update(self, rectangle: BoundingRectangle, threshold: Fraction) -> None:
        """Show the area of `rectangle` and react to whether it's below `threshold`."""
        self._rectangle = rectangle
        self._success = rectangle.area < threshold
        self._show_area()
        self.label.setStyleSheet(f"color: {palette.SUCCESS.name()}; font-weight: bold;" if self._success else "")
        self._show_success()
        self._refresh_item()

    def _show_success(self) -> None:
        """The button: blinking or steadily green on success (as the user chose), regular otherwise."""
        blink = self._success and self._blink_enabled
        if blink and not self._timer.isActive():
            self._timer.start()
        elif not blink:
            self._timer.stop()
            self._set_blink(self._success)

    def _show_area(self) -> None:
        if self._rectangle is not None:
            self.label.setText(f"{tr('Area')}\n{format_area(self._rectangle.area)}")

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
            if on and self.button.minimumSize() != self.button.maximumSize():
                # A style sheet sizes the button differently: keep the size it has without one, or the whole panel
                # would change its width with every blink.
                self.button.setFixedSize(self.button.sizeHint())
            green = palette.SUCCESS.name()
            self.button.setStyleSheet(f"background-color: {green}; border: 1px solid {green};" if on else "")
