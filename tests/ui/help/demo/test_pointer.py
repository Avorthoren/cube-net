# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from cube_net.ui.help.demo.pointer import RIPPLE_MS, Pointer, pointer_image
from cube_net.ui.sheet.cursors import CursorKind, cursor_for


def test_the_app_cursors_and_an_arrow_for_the_system_ones(qtbot: QtBot) -> None:
    pixmap, tip = pointer_image(CursorKind.PENCIL)
    assert pixmap.cacheKey() == cursor_for(CursorKind.PENCIL).pixmap().cacheKey()
    assert tip == QPointF(cursor_for(CursorKind.PENCIL).hotSpot())
    arrow, _ = pointer_image(CursorKind.ARROW)
    assert pointer_image(CursorKind.BUTTON)[0].cacheKey() == arrow.cacheKey()
    assert not arrow.toImage().isNull()


def test_a_ripple_fades_away(qtbot: QtBot) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    pointer = Pointer(parent, lambda p: p)
    pointer.set_state(QPointF(10, 10), CursorKind.ARROW, ctrl=True)
    pointer.ripple()
    assert pointer._timer.isActive()
    qtbot.waitUntil(lambda: not pointer._timer.isActive(), timeout=RIPPLE_MS + 500)
    assert pointer.position() == QPointF(10, 10)
