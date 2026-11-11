# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime

import pytest

from cube_net.core.update_policy import due_today, offer_automatically

TODAY = datetime.date(2026, 11, 12)


def test_once_a_calendar_day() -> None:
    assert due_today(None, TODAY)  # never checked
    assert not due_today(TODAY, TODAY)
    assert due_today(TODAY - datetime.timedelta(days=1), TODAY)  # 23:55 yesterday counts as yesterday


@pytest.mark.parametrize(
    ("latest", "current", "skipped", "offered"),
    [
        ("1.2.0", "1.0.0", None, True),
        ("1.2.0", "1.0.0", "1.2.0", False),  # turned down: never again automatically
        ("1.3.0", "1.0.0", "1.2.0", True),  # a newer one than the turned down one
        ("1.2.0", "1.2.0", None, False),  # up to date
        ("1.2.0", "1.0", None, True),  # a development copy
        ("1.2.0", "1.0.0", "1.2.0-beta", True),  # 1.2.0 is newer than the pre-release turned down
    ],
)
def test_what_is_offered(latest: str, current: str, skipped: str | None, offered: bool) -> None:
    assert offer_automatically(latest, current, skipped) is offered
