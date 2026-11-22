# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from cube_net.ui.help.help_tab import HelpTab


def test_a_tab_by_its_name_or_the_first_one() -> None:
    assert HelpTab.named("hotkeys") is HelpTab.HOTKEYS
    assert HelpTab.named("") is HelpTab.NETWORK  # none kept yet
    assert HelpTab.named("gone") is HelpTab.NETWORK
