# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`BoundingControls`: the bounding rectangle's area label and toggle button on the instrument panel (docs/idea.txt).

- The area of the minimum-area bounding rectangle is always shown, with 3 decimals. Its hint has a second line with
  the exact area, a reduced fraction like the coordinates hint's, then "=" or "≈" and the panel's 3 decimals:
  "16129/1250 ≈ 12.903". The hint shows as soon as the mouse is over the area (`InstantTooltips`), and while it's
  shown, Ctrl+C copies it, with every number in full (`copied_hint`).
- The toggle button shows / hides the rectangle on the sheet.
- Below the area: the project's target area, which the user can edit there. What's typed is taken on Enter, or when
  the field loses the focus: when the user clicks anywhere else in the window, even on what doesn't take the focus
  (the instrument panel's buttons and labels).
- When the area is below the project's threshold, the area and the rectangle turn green, and the button blinks:
  regular and fully green in equal parts, 6 changes per second. Or, if the user switched blinking off, the button is
  just green all the time.
"""

from fractions import Fraction

from PyQt6.QtCore import QEvent, QLocale, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QFontMetrics
from PyQt6.QtWidgets import QApplication, QDoubleSpinBox, QLabel, QToolBar, QWidget

from cube_net.core.bounding import BoundingRectangle
from cube_net.core.project_settings import MAX_AREA_THRESHOLD, MIN_AREA_THRESHOLD
from cube_net.ui import palette
from cube_net.ui.i18n import TRANSLATIONS, bind, tr
from cube_net.ui.instant_tooltips import InstantTooltips
from cube_net.ui.instruments.button_look import RADIUS_PX
from cube_net.ui.sheet.bounding_item import BoundingItem
from cube_net.ui.sheet.coordinates_text import MAX_DIGITS, fraction_text, is_exact

# The target area has at most 3 decimals; the field's arrows change it by this much.
TARGET_DECIMALS = 3
TARGET_STEP = 0.1

# 6 changes per second: 3 times regular, 3 times green.
BLINK_INTERVAL_MS = round(1000 / 6)


def format_area(area: Fraction) -> str:
    return f"{float(area):.3f}"


def exact_area_text(area: Fraction, limit: int | None = MAX_DIGITS) -> str:
    """The hint's second line: the exact area, and what the panel shows ("16129/1250 ≈ 12.903", "12 = 12.000"). A
    numerator or a denominator longer than `limit` digits shows as `TOO_LONG` (None: every number in full)."""
    return f"{fraction_text(area, limit)} {'=' if is_exact(area) else '≈'} {format_area(area)}"


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

        # What it put on the toolbar, to show or hide together.
        self._toolbar_actions = [toolbar.addSeparator()]
        self.label = QLabel(toolbar)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tooltips = InstantTooltips(self.label)  # at once: no waiting over the area
        self._show_tooltip()  # and again with every area, and in another language
        self._toolbar_actions.append(toolbar.addWidget(self.label))
        self.target_label = QLabel(toolbar)
        bind(self.target_label, self.target_label.setText, "Target area")
        self.target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._toolbar_actions.append(toolbar.addWidget(self.target_label))
        self.target = QDoubleSpinBox(toolbar)
        self.target.setLocale(QLocale.c())  # always 7.100, never 7,100
        self.target.setDecimals(TARGET_DECIMALS)
        self.target.setRange(float(MIN_AREA_THRESHOLD), float(MAX_AREA_THRESHOLD))
        self.target.setSingleStep(TARGET_STEP)
        self.target.setKeyboardTracking(False)  # a value is taken when it's entered, not at every digit typed
        bind(self.target, self.target.setToolTip, "The project's goal: an area below this is a success")
        self.target.valueChanged.connect(self._on_target)
        self._toolbar_actions.append(toolbar.addWidget(self.target))
        app = QApplication.instance()
        assert app is not None
        app.installEventFilter(self)  # see `eventFilter`
        self.action = QAction(toolbar)
        bind(self.action, self.action.setText, "Bounds")
        self.action.setCheckable(True)
        self.action.setShortcut("B")
        bind(self.action, self.action.setToolTip, "Show the smallest bounding rectangle (B)")
        self.action.toggled.connect(self._on_toggled)
        toolbar.addAction(self.action)
        self._toolbar_actions.append(self.action)
        self.button: QWidget | None = toolbar.widgetForAction(self.action)

        TRANSLATIONS.changed.connect(self._show_area)
        self._timer = QTimer(self)
        self._timer.setInterval(BLINK_INTERVAL_MS)
        self._timer.timeout.connect(self._blink)

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        """A mouse press elsewhere in the window takes the focus from the target field, which takes what was typed
        then (before what was clicked acts: a button acts when the mouse is released)."""
        if (
            event is not None
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(watched, QWidget)
            and self.target.hasFocus()
            and watched is not self.target
            and not self.target.isAncestorOf(watched)
            and watched.window() is self.target.window()
        ):
            self.target.clearFocus()
        return False

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

    def _show_tooltip(self) -> None:
        """What the area is, and (once there is one) its exact value."""
        self.label.setToolTip(self._hint())
        self.tooltips.refresh()  # if it's shown

    def _hint(self, limit: int | None = MAX_DIGITS) -> str:
        text = tr("Area of the smallest rectangle (any orientation) that contains the net")
        if self._rectangle is not None:
            text += "\n" + exact_area_text(self._rectangle.area, limit)
        return text

    def set_shown(self, shown: bool) -> None:
        """Show or hide all of it (hidden while a template is made, which has no target and no rectangle)."""
        for action in self._toolbar_actions:
            action.setVisible(shown)
        if not shown:
            self.action.setChecked(False)

    def hint_shown(self) -> bool:
        """Is the area's hint shown now?"""
        return self.tooltips.shown_for() is self.label

    def copied_hint(self) -> str:
        """What Ctrl+C copies while the hint is shown: its text, with every number in full."""
        return self._hint(limit=None)

    def _show_area(self) -> None:
        self._show_tooltip()
        if self._rectangle is not None:
            text = f"{tr('Area')}\n{format_area(self._rectangle.area)}"
            self.label.setText(text)
            # On success the text is bold, which is wider: the label has that width all along, so the panel (as wide as
            # its widest item) doesn't change its width when the target is reached.
            bold = QFont(self.label.font())
            bold.setBold(True)
            metrics = QFontMetrics(bold)
            margins = self.label.contentsMargins()
            widest = max(metrics.horizontalAdvance(line) for line in text.split("\n"))
            self.label.setMinimumWidth(widest + margins.left() + margins.right() + 2 * self.label.margin())

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
            on_style = f"background: {green}; border: 1px solid {green}; border-radius: {RADIUS_PX}px;"
            self.button.setStyleSheet(on_style if on else "")  # off: the panel's look again
