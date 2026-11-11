# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The build script's helpers, and that the packaging files agree with it (the builds themselves run on GitHub)."""

import re
import sys
from pathlib import Path

import pytest

from cube_net import __version__
from scripts import build


def test_the_version_is_the_packages() -> None:
    assert build.version() == __version__


@pytest.mark.parametrize(
    ("text", "numbers"),
    [("1.2.0", "1.2.0"), ("1.2.0-beta.2", "1.2.0"), ("10.0.3-rc1", "10.0.3"), ("1.0", "1.0.0"), ("2", "2.0.0")],
)
def test_just_the_numbers(text: str, numbers: str) -> None:
    assert build.numbers(text) == numbers


@pytest.mark.parametrize(
    ("platform", "program"),
    [
        ("linux", Path("Cube Net/Cube Net")),
        ("win32", Path("Cube Net/Cube Net.exe")),
        ("darwin", Path("Cube Net.app/Contents/MacOS/Cube Net")),
    ],
)
def test_the_program_in_the_folder(monkeypatch: pytest.MonkeyPatch, platform: str, program: Path) -> None:
    monkeypatch.setattr(sys, "platform", platform)
    folder = Path("Cube Net.app" if platform == "darwin" else "Cube Net")
    assert build.program(folder) == program


def test_a_tool_from_the_environment_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPIMAGETOOL", "/opt/appimagetool")
    assert build.tool("APPIMAGETOOL", "appimagetool") == "/opt/appimagetool"


def test_a_missing_tool_says_how_to_give_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ISCC", raising=False)
    monkeypatch.setattr(build.shutil, "which", lambda name: None)
    with pytest.raises(build.BuildError, match="set ISCC"):
        build.tool("ISCC", "iscc", (Path("/nowhere/ISCC.exe"),))


def test_the_linux_files_agree() -> None:
    desktop = (build.ROOT / "packaging/linux/cube-net.desktop").read_text()
    assert "Icon=cube-net\n" in desktop and "Name=Cube Net\n" in desktop
    assert "Exec=cube-net %f\n" in desktop  # a project file given to it comes on the command line
    assert "StartupWMClass=Cube Net\n" in desktop  # X11: the windows' class (the app's name), for the Dock's icon
    mime = (build.ROOT / "packaging/linux/cube-net.xml").read_text()
    kind = re.search(r'<mime-type type="([^"]+)">', mime)
    assert kind is not None and f"MimeType={kind.group(1)};\n" in desktop  # the type it opens is the one defined
    assert '<glob pattern="*.cubenet"' in mime
    app_run = build.ROOT / "packaging/linux/AppRun"
    assert '"$HERE/usr/lib/cube-net/Cube Net"' in app_run.read_text()
    assert 'export GIO_MODULE_DIR="$HERE/' in app_run.read_text()  # not the system's GLib modules
    assert app_run.stat().st_mode & 0o111  # it's run as it is


def test_the_installer_gets_everything_it_needs() -> None:
    script = (build.ROOT / "packaging/windows/cube_net.iss").read_text()
    used = set(re.findall(r"\{#(\w+)\}", script))
    assert used == {"Version", "Numbers", "Source", "OutputDir", "OutputName", "Icon"}
    assert "AppId={{0554B29B-25AF-4364-969F-0AD244EAC194}" in script  # never changes: updates find the installed one
    assert "PrivilegesRequired=lowest" in script  # no administrator rights


def test_the_icons_are_where_the_recipe_takes_them() -> None:
    spec = (build.ROOT / "packaging/cube_net.spec").read_text()
    for icon in re.findall(r'"(packaging/icons/[^"]+)"', spec):
        assert (build.ROOT / icon).is_file(), icon


def test_windows_opens_project_files_with_it() -> None:
    script = (build.ROOT / "packaging/windows/cube_net.iss").read_text()
    assert "ChangesAssociations=yes" in script
    assert (
        r'Subkey: "Software\Classes\.cubenet"; ValueType: string; ValueName: ""; ValueData: "CubeNet.Project"' in script
    )
    assert r'ValueData: """{app}\Cube Net.exe"" ""%1"""' in script  # the file comes on the command line
    assert "uninsdeletekey" in script  # and the uninstaller takes it away


def test_after_an_update_the_new_version_starts() -> None:
    """The application runs the installer silently for an update: then (only then) it starts the new version."""
    script = (build.ROOT / "packaging/windows/cube_net.iss").read_text()
    assert 'Filename: "{app}\\Cube Net.exe"; Flags: nowait skipifnotsilent' in script


def test_macos_opens_project_files_with_it() -> None:
    spec = (build.ROOT / "packaging/cube_net.spec").read_text()
    assert '"public.filename-extension": ["cubenet"]' in spec
    assert '"LSItemContentTypes": [PROJECT_TYPE]' in spec and '"LSHandlerRank": "Owner"' in spec


def test_the_extension_is_the_projects() -> None:
    from cube_net.core.project import PROJECT_SUFFIX

    assert PROJECT_SUFFIX == ".cubenet"  # what the three packages register


class TestLabel:
    """The package's name: the version for a release, the commit for a test build (after the version, once there's a
    release)."""

    def answer(self, monkeypatch: pytest.MonkeyPatch, tags: str) -> None:
        replies = {("rev-parse", "--short=7", "HEAD"): "abc1234", ("tag", "--list", "v*"): tags}
        monkeypatch.setattr(build, "git", lambda *args: replies[args])

    def test_a_release(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
        self.answer(monkeypatch, "v1.0.0")
        assert build.label("1.0.0") == "1.0.0"

    def test_a_test_build_before_any_release(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_REF_TYPE", raising=False)
        self.answer(monkeypatch, "")
        assert build.label("1.0") == "abc1234"
        self.answer(monkeypatch, "vacation not-a-release v1.0")  # tags that aren't release tags don't count
        assert build.label("1.0") == "abc1234"

    def test_a_test_build_after_a_release(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
        self.answer(monkeypatch, "v1.0.0\nv1.0.1-beta")
        assert build.label("1.0.1") == "1.0.1-abc1234"
