# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from cube_net.ui.help.demo.steps import CLICK_MS, Press, Release, Wait, click


def test_a_click_is_a_press_a_moment_and_a_release() -> None:
    assert click() == [Press(), Wait(CLICK_MS), Release()]
