# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The latest release of Cube Net on GitHub: its version, notes, page, and the size of this system's package; and the
notes of the releases before it, so that a user several versions behind sees all that's new to them.

One question gets them all: GitHub's list of releases (the newest 100). The latest is the highest version among the
published ones that aren't pre-releases (drafts are never seen); the notes are those of the same releases. The
answer comes over HTTPS with the certificates of `certifi`, the same on every system (a built app can't count on the
system's own: macOS' Python has none, and Linux keeps them in different places).

For trying the update check without a release: $CUBE_NET_UPDATES_URL can name another place to ask instead (a
`file://` URL of a JSON file shaped like GitHub's answer, say: its list of releases, or a single release).
"""

import json
import os
import ssl
import sys
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass, field, replace

import certifi

from cube_net import __version__
from cube_net.core.version import newer, order_of, parse_version

# Where GitHub lists the releases (the newest first, as many as one answer can have), and how long to wait for its
# answer (s).
RELEASES_URL = "https://api.github.com/repos/Avorthoren/cube-net/releases?per_page=100"
TIMEOUT_S = 15

# Another place to ask, for trying the check (see the module's docstring).
URL_VARIABLE = "CUBE_NET_UPDATES_URL"

# How this system's package ends (scripts/build.py names them so).
PACKAGE_ENDINGS = {
    "win32": "-windows-x64-setup.exe",
    "linux": "-linux-x86_64.AppImage",
    "darwin": "-macos-arm64.dmg",
}


# The release's file with the checksums of the others (the release workflow makes it).
CHECKSUMS = "SHA256SUMS"


class UpdateCheckError(Exception):
    """The latest release couldn't be found out: the message says why."""


@dataclass(frozen=True)
class ReleaseFile:
    # Its size (bytes).
    size: int

    # Where it's downloaded from.
    url: str


@dataclass(frozen=True)
class ReleaseNotes:
    # The version, without the tag's "v": "1.2.0".
    version: str

    # When it was published ("2026-11-20"; "" if the answer doesn't say).
    date: str

    # What's new in it (Markdown: the changelog's section; "" if nothing).
    notes: str


@dataclass(frozen=True)
class LatestRelease:
    # Its version, without the tag's "v": "1.2.0".
    version: str

    # Its notes (Markdown: the changelog's section).
    notes: str

    # Its page on GitHub.
    page: str

    # Its files, by name.
    files: dict[str, ReleaseFile] = field(default_factory=dict)

    # When it was published ("2026-11-20"; "" if the answer doesn't say).
    date: str = ""

    # The notes of the releases before it (and its own), the newest first; empty if the answer had only this one.
    history: tuple[ReleaseNotes, ...] = ()

    def notes_since(self, current: str) -> list[ReleaseNotes]:
        """The notes of every release newer than `current`, up to this one, the newest first."""
        own = ReleaseNotes(self.version, self.date, self.notes)
        history = self.history or (own,)
        return [
            notes
            for notes in history
            if newer(notes.version, current) and order_of(notes.version) <= order_of(self.version)
        ] or [own]

    def package(self, platform: str | None = None) -> tuple[str, ReleaseFile] | None:
        """The package for this system (or `platform`), with its name, if the release has one."""
        ending = PACKAGE_ENDINGS.get(_system(platform or sys.platform))
        return next(((name, file) for name, file in self.files.items() if ending and name.endswith(ending)), None)

    def package_size(self, platform: str | None = None) -> int | None:
        package = self.package(platform)
        return package[1].size if package is not None else None

    def checksums(self) -> ReleaseFile | None:
        return self.files.get(CHECKSUMS)


def _system(platform: str) -> str:
    return "linux" if platform.startswith("linux") else platform


def fetch_latest_release(url: str | None = None) -> LatestRelease | None:
    """The latest release, with the notes of those before it (None: there's none yet), or an UpdateCheckError."""
    address = url or os.environ.get(URL_VARIABLE) or RELEASES_URL
    request = urllib.request.Request(
        address, headers={"Accept": "application/vnd.github+json", "User-Agent": f"Cube-Net/{__version__}"}
    )
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S, context=context) as response:
            answer = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None  # no release yet
        raise UpdateCheckError(f"GitHub answered {error.code} ({error.reason})") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise UpdateCheckError(str(reason)) from None
    except ValueError:
        raise UpdateCheckError("GitHub's answer can't be read") from None
    return latest_from(answer) if isinstance(answer, list) else release_from(answer)


def latest_from(answer: list[object]) -> LatestRelease | None:
    """The latest release in GitHub's list of releases, with all their notes (None: no release in it)."""
    releases = [
        release_from(item)
        for item in answer
        if isinstance(item, dict)
        and not item.get("draft")
        and not item.get("prerelease")
        and isinstance(item.get("tag_name"), str)
        and parse_version(item["tag_name"].removeprefix("v")) is not None
    ]
    if not releases:
        return None
    releases.sort(key=lambda release: order_of(release.version), reverse=True)
    history = tuple(ReleaseNotes(release.version, release.date, release.notes) for release in releases)
    return replace(releases[0], history=history)


def tidy_notes(notes: str) -> str:
    """A release's notes as GitHub keeps them ("\\r\\n" between the lines), with "\\n" between them, without the empty
    lines around them, and without the indentation all their lines share."""
    lines = [line.rstrip() for line in notes.replace("\r\n", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return textwrap.dedent("\n".join(lines))


def release_from(answer: object) -> LatestRelease:
    """The release in GitHub's answer (a release's JSON)."""
    if not isinstance(answer, dict) or not isinstance(answer.get("tag_name"), str):
        raise UpdateCheckError("GitHub's answer has no release in it")
    files = {
        str(asset.get("name")): ReleaseFile(int(asset.get("size", 0)), str(asset.get("browser_download_url", "")))
        for asset in answer.get("assets") or []
        if isinstance(asset, dict)
    }
    return LatestRelease(
        version=answer["tag_name"].removeprefix("v"),
        notes=tidy_notes(str(answer.get("body") or "")),
        page=str(answer.get("html_url") or "https://github.com/Avorthoren/cube-net/releases/latest"),
        files=files,
        date=str(answer.get("published_at") or "")[:10],
    )
