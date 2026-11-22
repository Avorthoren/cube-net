# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from fractions import Fraction as F

from PyQt6.QtWidgets import QToolBar
from pytestqt.qtbot import QtBot

from cube_net.ui.template.net_area import NetArea


def test_the_area_and_its_hint(qtbot: QtBot) -> None:
    toolbar = QToolBar()
    qtbot.addWidget(toolbar)
    area = NetArea(toolbar)
    assert area.label.text() == "Net area\n—" and area.copied_hint() == ""
    area.set_area(F(20, 3))
    assert area.label.text() == "Net area\n6.667"
    assert area.label.toolTip() == "Area of the net the loop draws\n20/3 ≈ 6.667"
    assert area.copied_hint() == "20/3 ≈ 6.667"
