# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Reading GitHub's answer about the latest release (never the real GitHub: a file, or a simulated failure)."""

import json
import urllib.error
from pathlib import Path

import pytest

from cube_net.ui.updates import latest_release
from cube_net.ui.updates.latest_release import LatestRelease, UpdateCheckError, fetch_latest_release, release_from

ANSWER = {
    "tag_name": "v1.2.0",
    "body": "- Ctrl+click deletes a point.",
    "html_url": "https://github.com/Avorthoren/cube-net/releases/tag/v1.2.0",
    "assets": [
        {"name": "CubeNet-1.2.0-windows-x64-setup.exe", "size": 61_000_000},
        {"name": "CubeNet-1.2.0-linux-x86_64.AppImage", "size": 78_400_000},
        {"name": "CubeNet-1.2.0-macos-arm64.dmg", "size": 70_000_000},
        {"name": "SHA256SUMS", "size": 300},
    ],
}


def test_what_the_answer_says() -> None:
    release = release_from(ANSWER)
    assert release.version == "1.2.0"  # without the tag's "v"
    assert release.notes == "- Ctrl+click deletes a point."
    assert release.page.endswith("/tag/v1.2.0")


@pytest.mark.parametrize(
    ("platform", "size"), [("win32", 61_000_000), ("linux", 78_400_000), ("darwin", 70_000_000), ("sunos5", None)]
)
def test_the_size_of_this_systems_package(platform: str, size: int | None) -> None:
    assert release_from(ANSWER).package_size(platform) == size


def test_an_answer_without_a_release() -> None:
    with pytest.raises(UpdateCheckError):
        release_from({"message": "rate limit"})


def test_asked_somewhere_else_for_trying(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    answer = tmp_path / "latest.json"
    answer.write_text(json.dumps(ANSWER))
    monkeypatch.setenv(latest_release.URL_VARIABLE, answer.as_uri())
    release = fetch_latest_release()
    assert isinstance(release, LatestRelease) and release.version == "1.2.0"


def test_no_release_yet(monkeypatch: pytest.MonkeyPatch) -> None:
    def not_found(*_: object, **__: object) -> object:
        raise urllib.error.HTTPError("url", 404, "Not Found", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(latest_release.urllib.request, "urlopen", not_found)
    assert fetch_latest_release("https://example.com/latest") is None


@pytest.mark.parametrize(
    ("error", "said"),
    [
        (urllib.error.HTTPError("url", 403, "rate limit exceeded", None, None), "403"),  # type: ignore[arg-type]
        (urllib.error.URLError("Name or service not known"), "Name or service not known"),
        (TimeoutError("timed out"), "timed out"),
    ],
)
def test_failures_say_why(monkeypatch: pytest.MonkeyPatch, error: Exception, said: str) -> None:
    def failing(*_: object, **__: object) -> object:
        raise error

    monkeypatch.setattr(latest_release.urllib.request, "urlopen", failing)
    with pytest.raises(UpdateCheckError, match=said):
        fetch_latest_release("https://example.com/latest")
