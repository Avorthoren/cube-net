# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from cube_net.ui.session.recent_lines import RecentLines


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_lines_as_a_session_logs_with_relative_time() -> None:
    clock = FakeClock()
    lines = RecentLines(clock=clock)
    lines.header("hello")
    clock.now = 101.25
    lines.write("press", "L", "1.000,2.000")
    assert lines.lines() == ["# hello", "1.250 press L 1.000,2.000"]
    lines.close()
    assert not lines.closed  # it goes on keeping them
    lines.write("key", "A")
    assert len(lines.lines()) == 3


def test_only_the_latest_are_kept() -> None:
    lines = RecentLines(size=3, clock=FakeClock())
    for i in range(5):
        lines.write("key", i)
    assert [line.split()[-1] for line in lines.lines()] == ["2", "3", "4"]
