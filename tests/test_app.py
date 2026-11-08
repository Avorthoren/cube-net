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
    assert app.main([]) == 7
    assert calls == ["application", "show", "reopen", "exec"]
