# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

import pytest

from cube_net import app


def test_the_window_is_shown_and_then_reopens_the_last_project(monkeypatch: pytest.MonkeyPatch) -> None:
    """In that order: if reopening has something to say, it says it over a window that's there."""
    calls: list[str] = []

    class FakeApplication:
        def __init__(self, _argv: list[str]) -> None:
            calls.append("application")

        def setApplicationName(self, _name: str) -> None:
            pass

        def setOrganizationName(self, _name: str) -> None:
            pass

        def setWindowIcon(self, icon: str) -> None:
            calls.append(f"icon {icon}")

        def exec(self) -> int:
            calls.append("exec")
            return 7

    class FakeWindow:
        def show(self) -> None:
            calls.append("show")

        def reopen_last_project(self) -> None:
            calls.append("reopen")

    monkeypatch.setattr(app, "QApplication", FakeApplication)
    monkeypatch.setattr(app, "MainWindow", FakeWindow)
    monkeypatch.setattr(app, "QIcon", lambda path: Path(path).name)
    assert app.main([]) == 7
    assert calls == ["application", "icon cube_net.png", "show", "reopen", "exec"]


def test_the_icon_is_there() -> None:
    assert app.ICON.is_file()


def test_the_smoke_test_shows_the_window_and_quits(monkeypatch: pytest.MonkeyPatch) -> None:
    """The builds start themselves with it: the window appears, and the app quits by itself after a moment."""
    calls: list[str] = []

    class FakeApplication:
        def __init__(self, _argv: list[str]) -> None:
            pass

        def setApplicationName(self, _name: str) -> None:
            pass

        def setOrganizationName(self, _name: str) -> None:
            pass

        def setWindowIcon(self, _icon: object) -> None:
            pass

        def quit(self) -> None:
            calls.append("quit")

        def exec(self) -> int:
            calls.append("exec")
            return 0

    class FakeWindow:
        def __init__(self, settings: object = None, session_dir: object = None) -> None:
            assert settings is not None and session_dir is not None  # not the user's
            calls.append("window")

        def show(self) -> None:
            calls.append("show")

        def reopen_last_project(self) -> None:
            calls.append("reopen")

    class FakeTimer:
        @staticmethod
        def singleShot(ms: int, slot: object) -> None:
            calls.append(f"quit in {ms} ms")

    monkeypatch.setattr(app, "QApplication", FakeApplication)
    monkeypatch.setattr(app, "MainWindow", FakeWindow)
    monkeypatch.setattr(app, "QIcon", lambda path: path)
    monkeypatch.setattr(app, "QTimer", FakeTimer)
    assert app.main(["cube-net", app.SMOKE_TEST]) == 0
    assert calls == ["window", "show", f"quit in {app.SMOKE_TEST_MS} ms", "exec"]  # no reopening
