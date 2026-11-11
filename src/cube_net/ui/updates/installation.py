# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Which installation of Cube Net this is, so how it updates itself: the Windows installation (its installer
replaces it), the Linux AppImage (the file is replaced), the macOS app (the bundle is replaced). A copy run from the
source isn't one of them: it can't update itself (the release's page is opened instead).
"""

import os
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PyQt6.QtCore import QStandardPaths

from cube_net.ui.desktop_integration import running_appimage


class Kind(Enum):
    WINDOWS = "windows"
    APPIMAGE = "appimage"
    MACOS = "macos"


@dataclass(frozen=True)
class Installation:
    kind: Kind

    # What's replaced: the program (Windows), the AppImage file (Linux), the "Cube Net.app" bundle (macOS).
    path: Path


class ManualStepNeeded(Exception):
    """The update is downloaded, but can't be put in place by the application: the user finishes it."""

    def __init__(self, downloaded: Path, target: Path) -> None:
        super().__init__(f"{downloaded} -> {target}")
        self.downloaded = downloaded
        self.target = target


def current_installation(
    frozen: bool | None = None,
    executable: str | None = None,
    platform: str | None = None,
    environ: dict[str, str] | None = None,
) -> Installation | None:
    """This one (None: run from the source, or something else that can't be replaced). PyInstaller's builds are
    "frozen"; the AppImage's runtime says where its file is."""
    if not (getattr(sys, "frozen", False) if frozen is None else frozen):
        return None
    program = Path(executable or sys.executable)
    system = platform or sys.platform
    if system == "win32":
        return Installation(Kind.WINDOWS, program)
    if system.startswith("linux"):
        appimage = running_appimage(environ)
        return Installation(Kind.APPIMAGE, appimage.path) if appimage is not None else None
    if system == "darwin":
        bundle = program.parents[2] if len(program.parents) > 2 else program  # Cube Net.app/Contents/MacOS/Cube Net
        return Installation(Kind.MACOS, bundle) if bundle.suffix == ".app" else None
    return None


def download_folder(installation: Installation) -> Path:
    """Where the package is downloaded: an AppImage right where it is (it then just takes the old one's place), or the
    user's Downloads if that folder can't be written; anything else into a temporary folder."""
    if installation.kind is Kind.APPIMAGE:
        here = installation.path.parent
        if os.access(here, os.W_OK):
            return here
        downloads = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        return Path(downloads) if downloads else Path.home()
    return Path(tempfile.mkdtemp(prefix="cube-net-update-"))
