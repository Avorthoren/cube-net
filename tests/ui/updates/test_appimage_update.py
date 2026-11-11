# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import subprocess
from pathlib import Path

import pytest

from cube_net.ui.updates import appimage_update
from cube_net.ui.updates.appimage_update import install_appimage, start_appimage
from cube_net.ui.updates.installation import ManualStepNeeded


def appimage(path: Path, content: str = "old") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_next_to_the_old_one(tmp_path: Path) -> None:
    old = appimage(tmp_path / "CubeNet-1.0.0-linux-x86_64.AppImage")
    new = appimage(tmp_path / "CubeNet-1.2.0-linux-x86_64.AppImage", "new")
    assert install_appimage(new, old) == new
    assert not old.exists() and new.stat().st_mode & 0o111  # the old one gone, the new one executable


def test_with_the_same_name(tmp_path: Path) -> None:
    same = appimage(tmp_path / "Cube.AppImage", "new")  # the download replaced it already
    assert install_appimage(same, same) == same and same.exists()


def test_elsewhere_with_the_password_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    old = tmp_path / "opt" / "Cube.AppImage"
    new = appimage(tmp_path / "Downloads" / "CubeNet-1.2.0-linux-x86_64.AppImage", "new")
    asked: list[list[str]] = []
    monkeypatch.setattr(appimage_update.shutil, "which", lambda tool: "/usr/bin/pkexec")

    def run(command: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        asked.append(command)
        return subprocess.CompletedProcess(command, 0)

    assert install_appimage(new, old, run) == old.parent / new.name
    assert asked[0][:4] == ["/usr/bin/pkexec", "/bin/sh", "-c", appimage_update.PUT_IN_PLACE]
    assert asked[0][5:] == [str(new), str(old.parent / new.name), str(old)]
    assert not new.exists()  # moved there


@pytest.mark.parametrize("pkexec", [None, "/usr/bin/pkexec"], ids=["no pkexec", "cancelled"])
def test_or_by_hand(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pkexec: str | None) -> None:
    old = tmp_path / "opt" / "Cube.AppImage"
    new = appimage(tmp_path / "Downloads" / "CubeNet-1.2.0-linux-x86_64.AppImage", "new")
    monkeypatch.setattr(appimage_update.shutil, "which", lambda tool: pkexec)
    with pytest.raises(ManualStepNeeded) as raised:
        install_appimage(new, old, lambda command, **_: subprocess.CompletedProcess(command, 126))
    assert raised.value.downloaded == new and raised.value.target == old.parent / new.name
    assert new.exists() and new.stat().st_mode & 0o111  # ready to be started from there


def test_started_on_its_own_with_the_systems_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPIMAGE", "/old/Cube.AppImage")
    monkeypatch.setenv("APPDIR", "/tmp/.mount_old")
    started: list[tuple[list[str], dict[str, object]]] = []
    start_appimage(Path("/new/Cube.AppImage"), lambda command, **options: started.append((command, options)))
    command, options = started[0]
    env = options["env"]
    assert command == ["/new/Cube.AppImage"] and options["start_new_session"] is True
    assert isinstance(env, dict) and "APPIMAGE" not in env and "APPDIR" not in env
