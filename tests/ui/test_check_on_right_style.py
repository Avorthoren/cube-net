# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QColor, QImage
from PyQt6.QtWidgets import QMenu, QStyle, QStyleOptionMenuItem
from pytestqt.qtbot import QtBot

from cube_net.ui.check_on_right_style import CheckOnRightStyle, use_on


def menu_with(qtbot: QtBot, checked: bool) -> tuple[QMenu, QAction]:
    menu = QMenu()
    qtbot.addWidget(menu)
    action = QAction("Instruments", menu)
    action.setCheckable(True)
    action.setChecked(checked)
    menu.addAction(action)
    return menu, action


def picture(menu: QMenu) -> QImage:
    menu.adjustSize()
    return menu.grab().toImage()


def differs(first: QImage, second: QImage, x0: int, x1: int) -> bool:
    """Do the two pictures differ anywhere between columns x0 and x1?"""
    return any(
        QColor(first.pixel(x, y)) != QColor(second.pixel(x, y))
        for x in range(x0, x1)
        for y in range(min(first.height(), second.height()))
    )


def test_use_on_keeps_the_style_with_the_menu(qtbot: QtBot) -> None:
    menu, _ = menu_with(qtbot, True)
    style = use_on(menu)
    assert menu.style() is style
    assert style.parent() is menu


def test_the_check_box_is_on_the_right(qtbot: QtBot) -> None:
    on, _ = menu_with(qtbot, True)
    off, _ = menu_with(qtbot, False)
    use_on(on)
    use_on(off)
    checked, unchecked = picture(on), picture(off)
    assert checked.size() == unchecked.size()
    rect = on.actionGeometry(on.actions()[0])
    style = on.style()
    assert isinstance(style, CheckOnRightStyle)
    box = style.box_rect(rect)
    assert box.left() > rect.center().x()  # in the right half
    assert differs(checked, unchecked, box.left(), box.right() + 1)  # it shows the state
    assert not differs(checked, unchecked, 0, rect.center().x())  # and nothing on the left does


def test_room_is_made_for_the_box(qtbot: QtBot) -> None:
    plain, _ = menu_with(qtbot, True)
    styled, _ = menu_with(qtbot, True)
    style = use_on(styled)
    option = QStyleOptionMenuItem()
    option.text = "Instruments"
    option.menuItemType = QStyleOptionMenuItem.MenuItemType.Normal
    option.checkType = QStyleOptionMenuItem.CheckType.NonExclusive
    size = style.sizeFromContents(QStyle.ContentsType.CT_MenuItem, option, plain.fontMetrics().size(0, "Instruments"))
    box = style.box_rect(styled.actionGeometry(styled.actions()[0]))
    assert size.width() >= plain.fontMetrics().horizontalAdvance("Instruments") + box.width()


def test_a_click_switches_the_item(qtbot: QtBot) -> None:
    menu, action = menu_with(qtbot, False)
    use_on(menu)
    menu.popup(QPoint(0, 0))
    qtbot.waitExposed(menu)
    rect = menu.actionGeometry(action)
    qtbot.mouseClick(menu, Qt.MouseButton.LeftButton, pos=rect.center())
    assert action.isChecked()
