# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from pytestqt.qtbot import QtBot

from cube_net.core.net import Net, default_net
from cube_net.core.sheet import sheet_box
from cube_net.ui.sheet import net_style
from cube_net.ui.sheet.counterpart_blink import CounterpartBlink
from cube_net.ui.sheet.net_item import NetItem
from cube_net.ui.sheet.sheet_view import SheetView


@pytest.fixture
def setup(qtbot: QtBot) -> tuple[CounterpartBlink, NetItem, Net]:
    net = default_net()
    view = SheetView()
    qtbot.addWidget(view)
    view.set_sheet(sheet_box(v.position for v in net.vertices))
    view.set_net(net)
    item = view.net_item()
    assert item is not None
    return CounterpartBlink(view), item, net


def test_nothing_at_first(setup: tuple[CounterpartBlink, NetItem, Net]) -> None:
    blink, item, _ = setup
    assert blink.cut() is None
    assert item.hidden_cut() is None


def test_it_goes_invisible_at_once(setup: tuple[CounterpartBlink, NetItem, Net]) -> None:
    blink, item, net = setup
    cut = net.boundary_edges()[0]
    blink.set_cut(cut)
    assert blink.cut() is cut
    assert item.hidden_cut() is cut


def test_it_goes_back_and_forth(setup: tuple[CounterpartBlink, NetItem, Net], qtbot: QtBot) -> None:
    blink, item, net = setup
    cut = net.boundary_edges()[0]
    blink.set_cut(cut)
    qtbot.waitUntil(lambda: item.hidden_cut() is None, timeout=2000)
    qtbot.waitUntil(lambda: item.hidden_cut() is cut, timeout=2000)
    qtbot.waitUntil(lambda: item.hidden_cut() is None, timeout=2000)
    assert blink.cut() is cut


def test_stopping_makes_it_visible_for_good(setup: tuple[CounterpartBlink, NetItem, Net], qtbot: QtBot) -> None:
    blink, item, net = setup
    blink.set_cut(net.boundary_edges()[0])
    blink.set_cut(None)
    assert item.hidden_cut() is None
    qtbot.wait(net_style.COUNTERPART_BLINK_MS * 2)
    assert item.hidden_cut() is None


def test_another_cut_takes_over(setup: tuple[CounterpartBlink, NetItem, Net]) -> None:
    blink, item, net = setup
    first, second = net.boundary_edges()[:2]
    blink.set_cut(first)
    blink.set_cut(second)
    assert item.hidden_cut() is second


def test_the_same_cut_does_not_start_over(setup: tuple[CounterpartBlink, NetItem, Net], qtbot: QtBot) -> None:
    blink, item, net = setup
    cut = net.boundary_edges()[0]
    blink.set_cut(cut)
    qtbot.waitUntil(lambda: item.hidden_cut() is None, timeout=2000)
    blink.set_cut(cut)  # the mouse moved along the same cut
    assert item.hidden_cut() is None
