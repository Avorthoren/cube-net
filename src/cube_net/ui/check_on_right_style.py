# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""`CheckOnRightStyle`: a menu's checkable items show a check box to the right of their text, not a check mark on the
left. The box only shows whether the thing is on: clicking the item (anywhere) switches it, as with any menu item.

Set on a menu with `use_on`. A system menu bar (macOS) draws its menus itself and ignores it.
"""

from PyQt6.QtCore import QRect, QSize
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QMenu, QProxyStyle, QStyle, QStyleOption, QStyleOptionButton, QStyleOptionMenuItem, QWidget

# Room between the check box and the item's right edge, and between the text and the box.
MARGIN_PX = 8


def _checkable(option: QStyleOption | None) -> bool:
    return isinstance(option, QStyleOptionMenuItem) and option.checkType != QStyleOptionMenuItem.CheckType.NotCheckable


def _plain(option: QStyleOptionMenuItem) -> QStyleOptionMenuItem:
    """The item as if it weren't checkable (no check mark, nor room for one, on the left)."""
    plain = QStyleOptionMenuItem(option)
    plain.checkType = QStyleOptionMenuItem.CheckType.NotCheckable
    plain.checked = False
    plain.menuHasCheckableItems = False
    return plain


class CheckOnRightStyle(QProxyStyle):
    """The application's style (whatever it is), but with the check box of checkable menu items on the right."""

    def _box_size(self, option: QStyleOption | None, widget: QWidget | None) -> QSize:
        metric = QStyle.PixelMetric
        return QSize(
            self.pixelMetric(metric.PM_IndicatorWidth, option, widget),
            self.pixelMetric(metric.PM_IndicatorHeight, option, widget),
        )

    def box_rect(self, item: QRect, option: QStyleOption | None = None, widget: QWidget | None = None) -> QRect:
        """Where an item's check box is: at its right, in the middle of its height."""
        size = self._box_size(option, widget)
        top = item.top() + (item.height() - size.height()) // 2
        return QRect(item.right() - MARGIN_PX - size.width() + 1, top, size.width(), size.height())

    def sizeFromContents(
        self,
        type: QStyle.ContentsType,
        option: QStyleOption | None,
        size: QSize,
        widget: QWidget | None = None,
    ) -> QSize:
        if type != QStyle.ContentsType.CT_MenuItem or not _checkable(option):
            return super().sizeFromContents(type, option, size, widget)
        assert isinstance(option, QStyleOptionMenuItem)
        result = super().sizeFromContents(type, _plain(option), size, widget)
        box = self._box_size(option, widget)
        return QSize(result.width() + box.width() + 2 * MARGIN_PX, max(result.height(), box.height()))

    def drawControl(
        self,
        element: QStyle.ControlElement,
        option: QStyleOption | None,
        painter: QPainter | None,
        widget: QWidget | None = None,
    ) -> None:
        if element != QStyle.ControlElement.CE_MenuItem or not _checkable(option):
            super().drawControl(element, option, painter, widget)
            return
        assert isinstance(option, QStyleOptionMenuItem)
        super().drawControl(element, _plain(option), painter, widget)
        state = QStyle.StateFlag
        box = QStyleOptionButton()
        box.palette = option.palette
        box.direction = option.direction
        box.state = (option.state & state.State_Enabled) | (state.State_On if option.checked else state.State_Off)
        box.rect = self.box_rect(option.rect, option, widget)
        super().drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, box, painter, widget)


def use_on(menu: QMenu) -> CheckOnRightStyle:
    """Give `menu` this style (kept alive by the menu)."""
    style = CheckOnRightStyle()
    style.setParent(menu)
    menu.setStyle(style)
    return style
