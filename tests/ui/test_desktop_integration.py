# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The applications menu's entry of an AppImage, in a throwaway data folder (nothing of the user's is touched)."""

import shutil
from pathlib import Path

import pytest

from cube_net.ui import desktop_integration as integration
from cube_net.ui.desktop_integration import AppImage, DesktopEntry

PACKAGING = Path(__file__).resolve().parents[2] / "packaging"


@pytest.fixture
def appimage(tmp_path: Path) -> AppImage:
    """An AppImage's content as its build makes it (the packaging files), and the file in a folder with a space."""
    appdir = tmp_path / "mounted"
    (appdir / "usr/share/mime/packages").mkdir(parents=True)
    shutil.copy(PACKAGING / "linux/cube-net.desktop", appdir / "cube-net.desktop")
    shutil.copy(PACKAGING / "linux/cube-net.xml", appdir / "usr/share/mime/packages/cube-net.xml")
    shutil.copy(Path(integration.__file__).parent / "icons/cube_net.png", appdir / "cube-net.png")
    file = tmp_path / "My Apps" / "CubeNet-abc1234-linux-x86_64.AppImage"
    file.parent.mkdir()
    file.write_text("an AppImage")
    return AppImage(file, appdir)


@pytest.fixture
def entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DesktopEntry:
    told: list[list[str]] = []
    monkeypatch.setattr(integration.subprocess, "run", lambda command, **_: told.append(command))
    return DesktopEntry(tmp_path / "data")


def test_running_from_an_appimage(appimage: AppImage, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integration.sys, "platform", "linux")
    env = {"APPIMAGE": str(appimage.path), "APPDIR": str(appimage.appdir)}
    assert integration.running_appimage(env) == appimage
    assert integration.running_appimage({}) is None  # run otherwise
    assert integration.running_appimage({**env, "APPIMAGE": "/nowhere"}) is None
    monkeypatch.setattr(integration.sys, "platform", "win32")
    assert integration.running_appimage(env) is None


def test_the_data_folder() -> None:
    assert integration.data_home({"XDG_DATA_HOME": "/x/data"}) == Path("/x/data")
    assert integration.data_home({}) == Path.home() / ".local/share"


def test_install(appimage: AppImage, entry: DesktopEntry) -> None:
    entry.install(appimage)
    text = entry.entry.read_text()
    assert f'Exec="{appimage.path}" %f\n' in text  # quoted: there's a space in the path
    assert f"TryExec={appimage.path}\n" in text  # hidden while there's no file there
    assert f"Icon={entry.icon}\n" in text
    assert "MimeType=application/x-cube-net-project;\n" in text and "StartupWMClass=Cube Net\n" in text
    assert entry.icon.read_bytes() == (appimage.appdir / "cube-net.png").read_bytes()
    assert entry.mime.read_text() == (appimage.appdir / "usr/share/mime/packages/cube-net.xml").read_text()
    assert entry.installed_for() == appimage.path


def test_moved_it_follows(appimage: AppImage, entry: DesktopEntry, tmp_path: Path) -> None:
    entry.install(appimage)
    assert not entry.refresh(appimage)  # the same place: nothing to do
    moved = tmp_path / "elsewhere.AppImage"
    appimage.path.rename(moved)
    assert entry.refresh(AppImage(moved, appimage.appdir))
    assert entry.installed_for() == moved
    assert f"Exec={moved} %f\n" in entry.entry.read_text()


def test_gone_it_comes_back(appimage: AppImage, entry: DesktopEntry) -> None:
    entry.install(appimage)
    entry.icon.unlink()
    assert entry.refresh(appimage) and entry.icon.is_file()


def test_remove(appimage: AppImage, entry: DesktopEntry) -> None:
    entry.install(appimage)
    entry.remove()
    assert not entry.entry.exists() and not entry.icon.exists() and not entry.mime.exists()
    assert entry.installed_for() is None
    entry.remove()  # nothing there: fine too


def test_the_desktop_is_told(appimage: AppImage, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    told: list[tuple[list[str], dict[str, str]]] = []
    monkeypatch.setattr(integration.subprocess, "run", lambda command, env, **_: told.append((command, env)))
    monkeypatch.setattr(integration.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI/inside")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/local/lib")
    monkeypatch.setenv("GIO_MODULE_DIR", "/tmp/nothing")
    DesktopEntry(tmp_path / "data").install(appimage)
    data = tmp_path / "data"
    assert [command for command, _ in told] == [
        ["/usr/bin/update-mime-database", str(data / "mime")],
        ["/usr/bin/update-desktop-database", str(data / "applications")],
    ]
    env = told[0][1]
    assert env["LD_LIBRARY_PATH"] == "/usr/local/lib" and "GIO_MODULE_DIR" not in env  # the system's own


@pytest.mark.parametrize(
    ("path", "argument"),
    [
        ("/home/me/Cube.AppImage", "/home/me/Cube.AppImage"),
        ("/home/me/My Apps/Cube.AppImage", '"/home/me/My Apps/Cube.AppImage"'),
        ('/home/me/a"b$c.AppImage', '"/home/me/a\\"b\\$c.AppImage"'),
    ],
)
def test_exec_quoting(path: str, argument: str) -> None:
    assert integration.exec_argument(Path(path)) == argument


def test_a_backslash_survives_the_round_trip() -> None:
    program = Path("/home/me/odd\\name.AppImage")
    text = integration.entry_for("[Desktop Entry]\nExec=cube-net %f\nIcon=cube-net\n", program, Path("/i.png"))
    assert "TryExec=/home/me/odd\\\\name.AppImage" in text
    assert integration.installed_program(text) == program
