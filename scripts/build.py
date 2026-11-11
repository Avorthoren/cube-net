# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Build the application for this system: `python -m scripts.build` (from the root, with PyInstaller installed).

1. PyInstaller makes the program's folder (`packaging/cube_net.spec`), in build/.
2. The launch test: the built program starts with --smoke-test, shows its window and quits by itself; anything else
   (a crash, a missing piece of Qt) fails the build.
3. The package for this system goes into dist/ (<name>: the version for a release, the commit for a test build: see
   `label`):
   - Linux: CubeNet-<name>-linux-x86_64.AppImage (appimagetool: $APPIMAGETOOL, or on PATH), launch-tested too;
   - Windows: CubeNet-<name>-windows-x64-setup.exe (Inno Setup's ISCC: $ISCC, on PATH, or where it installs);
   - macOS: CubeNet-<name>-macos-arm64.dmg, with "Cube Net.app" and a link to Applications.
On GitHub Actions it tells the workflow the package's path (`GITHUB_OUTPUT`: file=...).
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from cube_net.core.version import parse_version

ROOT = Path(__file__).resolve().parent.parent
NAME = "Cube Net"
SPEC = ROOT / "packaging/cube_net.spec"
WORK = ROOT / "build/pyinstaller"
DIST = ROOT / "dist"

# How long the launch test may take (s): starting a big program from a fresh folder is slow on some machines.
SMOKE_TEST_TIMEOUT = 180

# Where Inno Setup's compiler is when it's installed the usual way.
ISCC_PLACES = (Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"), Path("C:/Program Files/Inno Setup 6/ISCC.exe"))


class BuildError(Exception):
    pass


def version() -> str:
    source = (ROOT / "src/cube_net/__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]*)"$', source, re.MULTILINE)
    if match is None:
        raise BuildError("src/cube_net/__init__.py has no __version__ line.")
    return match.group(1)


def numbers(text: str) -> str:
    """Just the three numbers of a version, as Windows and macOS want them: 1.2.0-beta.2 -> 1.2.0, 1.0 -> 1.0.0."""
    match = re.match(r"\d+(?:\.\d+)*", text)
    parts = match.group(0).split(".") if match else []
    return ".".join([*parts, "0", "0", "0"][:3])


def run(command: list[str], **kwargs: object) -> None:
    print("$", " ".join(command), flush=True)
    done = subprocess.run(command, **kwargs)  # type: ignore[call-overload]
    if done.returncode != 0:
        raise BuildError(f"{command[0]} failed (exit code {done.returncode}).")


def pyinstaller() -> Path:
    """The program's folder ("Cube Net/", or "Cube Net.app" on macOS)."""
    out = WORK / "dist"
    options = ["--noconfirm", "--clean", "--distpath", str(out), "--workpath", str(WORK / "work")]
    run([sys.executable, "-m", "PyInstaller", *options, str(SPEC)], cwd=ROOT)
    return out / (f"{NAME}.app" if sys.platform == "darwin" else NAME)


def program(folder: Path) -> Path:
    """The program to start, in the folder PyInstaller made."""
    if sys.platform == "darwin":
        return folder / "Contents" / "MacOS" / NAME
    return folder / (f"{NAME}.exe" if sys.platform == "win32" else NAME)


def smoke_test(command: list[str], env: dict[str, str] | None = None) -> None:
    """Start it with --smoke-test, without a screen: it must quit by itself with exit code 0."""
    environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen", **(env or {})}
    print("Launch test:", " ".join(command), flush=True)
    try:
        done = subprocess.run([*command, "--smoke-test"], env=environment, timeout=SMOKE_TEST_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise BuildError(f"The launch test didn't end within {SMOKE_TEST_TIMEOUT} s.") from None
    if done.returncode != 0:
        raise BuildError(f"The launch test failed (exit code {done.returncode}).")


def tool(variable: str, name: str, places: tuple[Path, ...] = ()) -> str:
    """A packaging tool: from the environment variable, on PATH, or in one of its usual places."""
    found = os.environ.get(variable) or shutil.which(name) or next((str(p) for p in places if p.exists()), None)
    if found is None:
        raise BuildError(f"Can't find {name}: install it, or set {variable} to it.")
    return found


def linux(folder: Path, name: str) -> Path:
    appdir = WORK / "AppDir"
    shutil.rmtree(appdir, ignore_errors=True)
    shutil.copytree(folder, appdir / "usr/lib/cube-net", symlinks=True)
    shutil.copy2(ROOT / "packaging/linux/AppRun", appdir / "AppRun")
    (appdir / "AppRun").chmod(0o755)
    shutil.copy2(ROOT / "packaging/linux/cube-net.desktop", appdir / "cube-net.desktop")
    # The file type of projects, where desktop integration tools look for it.
    mime = appdir / "usr/share/mime/packages"
    mime.mkdir(parents=True)
    shutil.copy2(ROOT / "packaging/linux/cube-net.xml", mime / "cube-net.xml")
    shutil.copy2(ROOT / "src/cube_net/ui/icons/cube_net.png", appdir / "cube-net.png")
    out = DIST / f"CubeNet-{name}-linux-x86_64.AppImage"
    # appimagetool is an AppImage itself: unpacked as it runs, it needs no FUSE (CI machines have none).
    run(
        [tool("APPIMAGETOOL", "appimagetool"), str(appdir), str(out)], env={**os.environ, "ARCH": "x86_64"} | _no_fuse()
    )
    smoke_test([str(out)], _no_fuse())
    return out


def _no_fuse() -> dict[str, str]:
    return {"APPIMAGE_EXTRACT_AND_RUN": "1"}


def windows(folder: Path, text: str, name: str) -> Path:
    name = f"CubeNet-{name}-windows-x64-setup"
    iscc = tool("ISCC", "iscc", ISCC_PLACES)
    defines = {
        "Version": text,
        "Numbers": numbers(text),
        "Source": str(folder),
        "OutputDir": str(DIST),
        "OutputName": name,
        "Icon": str(ROOT / "packaging/icons/cube_net.ico"),
    }
    run([iscc, *(f"/D{key}={value}" for key, value in defines.items()), str(ROOT / "packaging/windows/cube_net.iss")])
    return DIST / f"{name}.exe"


def macos(bundle: Path, name: str) -> Path:
    staging = WORK / "dmg"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    shutil.copytree(bundle, staging / bundle.name, symlinks=True)
    (staging / "Applications").symlink_to("/Applications")  # drag the app onto it to install
    out = DIST / f"CubeNet-{name}-macos-arm64.dmg"
    run(["hdiutil", "create", "-volname", NAME, "-srcfolder", str(staging), "-ov", "-format", "UDZO", str(out)])
    return out


def label(text: str) -> str:
    """What the package's file name says between "CubeNet-" and the system: a release's build (of a tag) the
    version; any other build (a test) its commit, with the version before it once a version has been released: until
    then the version means nothing yet (CubeNet-abc1234-..., CubeNet-1.2.0-abc1234-...)."""
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        return text
    commit = git("rev-parse", "--short=7", "HEAD")
    released = any(parse_version(tag[1:]) is not None for tag in git("tag", "--list", "v*").split())
    return f"{text}-{commit}" if released else commit


def git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if done.returncode != 0:
        raise BuildError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def build() -> Path:
    text = version()
    name = label(text)
    DIST.mkdir(exist_ok=True)
    folder = pyinstaller()
    smoke_test([str(program(folder))])
    if sys.platform.startswith("linux"):
        return linux(folder, name)
    if sys.platform == "win32":
        return windows(folder, text, name)
    if sys.platform == "darwin":
        return macos(folder, name)
    raise BuildError(f"No package for {sys.platform}.")


def main() -> int:
    try:
        out = build()
    except BuildError as error:
        print(f"::error::{error}" if os.environ.get("GITHUB_ACTIONS") else str(error), file=sys.stderr)
        return 1
    print(f"Built {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB)")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as file:
            file.write(f"file={out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
