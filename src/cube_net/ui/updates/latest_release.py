# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The latest release of Cube Net on GitHub: its version, notes, page, and the size of this system's package.

GitHub's "latest" is the newest published release that isn't a pre-release (drafts are never seen). The answer comes
over HTTPS with the certificates of `certifi`, the same on every system (a built app can't count on the system's own:
macOS' Python has none, and Linux keeps them in different places).

For trying the update check without a release: $CUBE_NET_UPDATES_URL can name another place to ask instead (a
`file://` URL of a JSON file shaped like GitHub's answer, say).
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import certifi

from cube_net import __version__

# Where GitHub tells the latest release, and how long to wait for its answer (s).
LATEST_RELEASE_URL = "https://api.github.com/repos/Avorthoren/cube-net/releases/latest"
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
class LatestRelease:
    # Its version, without the tag's "v": "1.2.0".
    version: str

    # Its notes (Markdown: the changelog's section).
    notes: str

    # Its page on GitHub.
    page: str

    # Its files, by name.
    files: dict[str, ReleaseFile] = field(default_factory=dict)

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
    """The latest release (None: there's none yet), or an UpdateCheckError."""
    address = url or os.environ.get(URL_VARIABLE) or LATEST_RELEASE_URL
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
    return release_from(answer)


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
        notes=str(answer.get("body") or ""),
        page=str(answer.get("html_url") or "https://github.com/Avorthoren/cube-net/releases/latest"),
        files=files,
    )
