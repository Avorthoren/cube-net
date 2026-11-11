# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

import pytest

from cube_net import app
from cube_net.ui.file_requests import FileRequests


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """What `main` does, in order, with stand-ins for the application and the window."""
    done: list[str] = []

    class FakeApplication:
        def __init__(self, argv: list[str]) -> None:
            self._argv = argv
            done.append("application")

        def arguments(self) -> list[str]:
            return list(self._argv)

        def setApplicationName(self, _name: str) -> None:
            pass

        def setOrganizationName(self, _name: str) -> None:
            pass

        def setDesktopFileName(self, name: str) -> None:
            done.append(f"desktop entry {name}")

        def setWindowIcon(self, icon: str) -> None:
            done.append(f"icon {icon}")

        def installEventFilter(self, watcher: object) -> None:
            assert isinstance(watcher, FileRequests)
            done.append("file requests")

        def quit(self) -> None:
            done.append("quit")

        def exec(self) -> int:
            done.append("exec")
            return 7

    class FakeWindow:
        def __init__(self, settings: object = None, session_dir: object = None, appimage: object = None) -> None:
            done.append("window" + (" with its own settings" if settings is not None else ""))

        def show(self) -> None:
            done.append("show")

        def reopen_last_project(self) -> None:
            done.append("reopen")

        def offer_menu_entry(self) -> None:
            done.append("menu entry")

        def check_for_updates_at_start(self) -> None:
            done.append("updates")

        def open_project_at_start(self, path: Path) -> None:
            done.append(f"open {path}")

        def open_project_requested(self, path: Path) -> None:
            pass

    monkeypatch.setattr(app, "QApplication", FakeApplication)
    monkeypatch.setattr(app, "MainWindow", FakeWindow)
    monkeypatch.setattr(app, "QIcon", lambda path: Path(path).name)
    monkeypatch.setattr(app, "FileRequests", lambda open_file, parent: FileRequests(open_file))
    return done


def test_the_window_is_shown_and_then_reopens_the_last_project(calls: list[str]) -> None:
    """In that order: if reopening has something to say, it says it over a window that's there."""
    assert app.main(["cube-net"]) == 7
    assert calls == [
        "application",
        "desktop entry cube-net",
        "icon cube_net.png",
        "window",
        "show",
        "menu entry",
        "file requests",
        "reopen",
        "updates",
        "exec",
    ]


def test_a_project_given_opens_instead_of_the_last_one(calls: list[str]) -> None:
    """A double-clicked file comes so on Windows and Linux."""
    app.main(["cube-net", "/home/me/work/net.cubenet"])
    assert "open /home/me/work/net.cubenet" in calls and "reopen" not in calls
    assert calls.index("show") < calls.index("open /home/me/work/net.cubenet")


@pytest.mark.parametrize(
    ("arguments", "project"),
    [
        (["cube-net"], None),
        (["cube-net", "a.cubenet"], Path("a.cubenet")),
        (["cube-net", "--some-option", "b.cubenet", "c.cubenet"], Path("b.cubenet")),  # the first one
        (["cube-net", "-psn_0_12345"], None),  # an old macOS' process number, not a file
    ],
)
def test_the_project_argument(arguments: list[str], project: Path | None) -> None:
    assert app.project_argument(arguments) == project


def test_the_icon_is_there() -> None:
    assert app.ICON.is_file()


def test_the_smoke_test_shows_the_window_and_quits(calls: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    """The builds start themselves with it: the window appears, and the app quits by itself after a moment."""

    class FakeTimer:
        @staticmethod
        def singleShot(ms: int, slot: object) -> None:
            calls.append(f"quit in {ms} ms")

    monkeypatch.setattr(app, "QTimer", FakeTimer)
    assert app.main(["cube-net", app.SMOKE_TEST]) == 7
    # Its own settings (not the user's), no project opened or reopened.
    assert calls[3:] == ["window with its own settings", "show", f"quit in {app.SMOKE_TEST_MS} ms", "exec"]
