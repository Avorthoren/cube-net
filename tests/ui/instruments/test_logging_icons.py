# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6.QtCore import QSize
from pytestqt.qtbot import QtBot

from cube_net.ui.instruments.logging_icons import ICON_PX, RECORD, record_icon, stop_icon


def test_record_is_a_red_dot(qtbot: QtBot) -> None:
    image = record_icon().pixmap(QSize(ICON_PX, ICON_PX)).toImage()
    middle = image.pixelColor(image.width() // 2, image.height() // 2)
    corner = image.pixelColor(1, 1)
    assert middle.name() == RECORD.name()
    assert corner.alpha() == 0  # round: nothing in the corners


def test_stop_is_a_red_square_in_a_frame(qtbot: QtBot) -> None:
    image = stop_icon().pixmap(QSize(ICON_PX, ICON_PX)).toImage()
    scale = image.width() / ICON_PX
    middle = image.pixelColor(image.width() // 2, image.height() // 2)
    near_inner_corner = image.pixelColor(round(7 * scale), round(7 * scale))
    frame = image.pixelColor(round(2 * scale), image.height() // 2)
    assert middle.name() == RECORD.name() == near_inner_corner.name()  # a square: red up to its corners
    assert frame.alpha() > 0 and frame.name() != RECORD.name()


def test_they_differ(qtbot: QtBot) -> None:
    assert (
        record_icon().pixmap(QSize(ICON_PX, ICON_PX)).toImage() != stop_icon().pixmap(QSize(ICON_PX, ICON_PX)).toImage()
    )
