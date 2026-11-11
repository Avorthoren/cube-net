# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from pathlib import Path

import pytest

from cube_net.ui.updates.installation import Installation, Kind, current_installation, download_folder


def test_run_from_the_source_isnt_one() -> None:
    assert current_installation(frozen=False) is None


def test_windows() -> None:
    found = current_installation(frozen=True, executable=r"C:\Users\me\Cube Net\Cube Net.exe", platform="win32")
    assert found is not None and found.kind is Kind.WINDOWS


def test_an_appimage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cube_net.ui.desktop_integration.sys.platform", "linux")
    file, appdir = tmp_path / "Cube.AppImage", tmp_path / "mounted"
    file.write_text("x")
    appdir.mkdir()
    env = {"APPIMAGE": str(file), "APPDIR": str(appdir)}
    assert current_installation(frozen=True, executable="/tmp/.mount/Cube Net", platform="linux", environ=env) == (
        Installation(Kind.APPIMAGE, file)
    )
    assert current_installation(frozen=True, platform="linux", environ={}) is None  # built, but not an AppImage


def test_a_mac_bundle() -> None:
    found = current_installation(
        frozen=True, executable="/Applications/Cube Net.app/Contents/MacOS/Cube Net", platform="darwin"
    )
    assert found == Installation(Kind.MACOS, Path("/Applications/Cube Net.app"))
    assert current_installation(frozen=True, executable="/usr/local/bin/cube-net", platform="darwin") is None


def test_an_appimage_downloads_next_to_itself(tmp_path: Path) -> None:
    assert download_folder(Installation(Kind.APPIMAGE, tmp_path / "Cube.AppImage")) == tmp_path


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_or_into_downloads_if_it_cant(tmp_path: Path) -> None:
    locked = tmp_path / "opt"
    locked.mkdir()
    locked.chmod(0o555)
    try:
        folder = download_folder(Installation(Kind.APPIMAGE, locked / "Cube.AppImage"))
    finally:
        locked.chmod(0o755)
    assert folder != locked and os.access(folder, os.W_OK)


def test_others_into_a_temporary_folder(tmp_path: Path) -> None:
    folder = download_folder(Installation(Kind.WINDOWS, tmp_path / "Cube Net.exe"))
    assert folder.is_dir() and folder.name.startswith("cube-net-update-")
    folder.rmdir()
