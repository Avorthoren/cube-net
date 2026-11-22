# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`NetArea`: the instrument panel's "Net area" while a template is made (in place of the bounding rectangle's
controls): the area of the net the loop draws, 3 decimals; its hint, shown at once, gives the exact value too, and
Ctrl+C copies that line in full while the hint is shown."""

from fractions import Fraction

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QToolBar

from cube_net.ui.i18n import TRANSLATIONS, tr
from cube_net.ui.instant_tooltips import InstantTooltips
from cube_net.ui.instruments.bounding_controls import exact_area_text, format_area
from cube_net.ui.sheet.coordinates_text import MAX_DIGITS

# Shown while there's no area (the loop isn't closed).
NO_AREA = "—"


class NetArea(QObject):
    def __init__(self, toolbar: QToolBar) -> None:
        super().__init__(toolbar)
        self._area: Fraction | None = None
        self.label = QLabel(toolbar)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tooltips = InstantTooltips(self.label)
        self.action: QAction = toolbar.addWidget(self.label)
        TRANSLATIONS.changed.connect(self._show)
        self._show()

    def set_area(self, area: Fraction | None) -> None:
        self._area = area
        self._show()

    def hint_shown(self) -> bool:
        return self.tooltips.shown_for() is self.label

    def copied_hint(self) -> str:
        """What Ctrl+C copies while the hint is shown: the exact value's line, in full (nothing without an area)."""
        return "" if self._area is None else exact_area_text(self._area, None)

    def _show(self) -> None:
        value = NO_AREA if self._area is None else format_area(self._area)
        self.label.setText(f"{tr('Net area')}\n{value}")
        hint = tr("Area of the net the loop draws")
        if self._area is not None:
            hint += "\n" + exact_area_text(self._area, MAX_DIGITS)
        self.label.setToolTip(hint)
        self.tooltips.refresh()
