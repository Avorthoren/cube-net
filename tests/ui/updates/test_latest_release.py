# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Reading GitHub's answer about the latest release (never the real GitHub: a file, or a simulated failure)."""

import json
import urllib.error
from pathlib import Path

import pytest

from cube_net.ui.updates import latest_release
from cube_net.ui.updates.latest_release import (
    LatestRelease,
    ReleaseNotes,
    UpdateCheckError,
    fetch_latest_release,
    latest_from,
    release_from,
)

ANSWER = {
    "tag_name": "v1.2.0",
    "body": "- Ctrl+click deletes a point.",
    "html_url": "https://github.com/Avorthoren/cube-net/releases/tag/v1.2.0",
    "assets": [
        {"name": "CubeNet-1.2.0-windows-x64-setup.exe", "size": 61_000_000, "browser_download_url": "https://dl/w"},
        {"name": "CubeNet-1.2.0-linux-x86_64.AppImage", "size": 78_400_000, "browser_download_url": "https://dl/l"},
        {"name": "CubeNet-1.2.0-macos-arm64.dmg", "size": 70_000_000, "browser_download_url": "https://dl/m"},
        {"name": "SHA256SUMS", "size": 300, "browser_download_url": "https://dl/sums"},
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


def test_this_systems_package_and_the_checksums() -> None:
    release = release_from(ANSWER)
    package = release.package("linux")
    assert (
        package is not None and package[0] == "CubeNet-1.2.0-linux-x86_64.AppImage" and package[1].url == "https://dl/l"
    )
    checksums = release.checksums()
    assert checksums is not None and checksums.url == "https://dl/sums"


def test_an_answer_without_a_release() -> None:
    with pytest.raises(UpdateCheckError):
        release_from({"message": "rate limit"})


def test_asked_somewhere_else_for_trying(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    answer = tmp_path / "latest.json"
    answer.write_text(json.dumps(ANSWER))
    monkeypatch.setenv(latest_release.URL_VARIABLE, answer.as_uri())
    release = fetch_latest_release()
    assert isinstance(release, LatestRelease) and release.version == "1.2.0"


def listed(version: str, **more: object) -> dict[str, object]:
    """A release as GitHub lists it."""
    return {"tag_name": f"v{version}", "body": f"- In {version}.", "published_at": "2027-01-20T10:00:00Z", **more}


LIST = [
    listed("1.4.0", draft=True),  # (GitHub shows drafts only to the repository's owners)
    listed("1.3.0-beta", prerelease=True),
    listed("1.1.0"),  # the list is in the order they were made, not by version
    listed("1.2.0"),
    {"tag_name": "nightly"},  # not a version
    listed("1.0.0"),
]


def test_the_latest_of_the_list_with_all_their_notes() -> None:
    release = latest_from(LIST)
    assert release is not None and release.version == "1.2.0" and release.date == "2027-01-20"
    assert [notes.version for notes in release.history] == ["1.2.0", "1.1.0", "1.0.0"]
    assert release.history[1] == ReleaseNotes("1.1.0", "2027-01-20", "- In 1.1.0.")


def test_an_empty_list_has_no_release() -> None:
    assert latest_from([]) is None
    assert latest_from([listed("2.0.0", draft=True)]) is None


@pytest.mark.parametrize(
    ("current", "versions"),
    [
        ("1.1.0", ["1.2.0"]),
        ("1.0.0", ["1.2.0", "1.1.0"]),
        ("0.9.0", ["1.2.0", "1.1.0", "1.0.0"]),
        ("1.0", ["1.2.0", "1.1.0", "1.0.0"]),
    ],
)
def test_the_notes_since_the_users_version(current: str, versions: list[str]) -> None:
    release = latest_from(LIST)
    assert release is not None
    assert [notes.version for notes in release.notes_since(current)] == versions


def test_a_single_release_has_only_its_own_notes() -> None:
    release = release_from(ANSWER)
    assert release.notes_since("0.1.0") == [ReleaseNotes("1.2.0", "", "- Ctrl+click deletes a point.")]


def test_the_list_read_from_somewhere_else(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    answer = tmp_path / "releases.json"
    answer.write_text(json.dumps(LIST))
    monkeypatch.setenv(latest_release.URL_VARIABLE, answer.as_uri())
    release = fetch_latest_release()
    assert release is not None and release.version == "1.2.0" and len(release.history) == 3


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
