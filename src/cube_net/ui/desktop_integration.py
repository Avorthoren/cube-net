# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Linux, AppImage: Cube Net in the desktop's applications menu, with its icon, opening project files.

An AppImage is just a file: the desktop knows nothing about it until its desktop entry, icon and file type are
installed in the user's data folder (`~/.local/share`, or `$XDG_DATA_HOME`). `DesktopEntry` installs them, taken from
the running AppImage itself (the ones its build put in), with the AppImage's own path in the entry:
- `Exec`: what the menu and a double-click start (with the file, `%f`);
- `TryExec`: the same path, so that the desktop hides the entry while there's no file there (it was moved or deleted)
  instead of showing one that does nothing; started again from its new place, the app puts its new path in
  (`refresh`).
Then it tells the desktop to read its file types and entries again. `remove` takes all of it away.
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# The desktop entry's name (cube-net.desktop): the application says it's that one (`setDesktopFileName`), so that
# the Dock shows its icon.
ENTRY_NAME = "cube-net"

# The files inside the AppImage (its AppDir) that are installed.
APPDIR_ENTRY = "cube-net.desktop"
APPDIR_ICON = "cube-net.png"
APPDIR_MIME = "usr/share/mime/packages/cube-net.xml"

# Characters that make an argument of `Exec` need quotes, and those that need a backslash inside them (the desktop
# entry specification).
RESERVED = set(" \t\n\"'\\><~|&;$*?#()`")
ESCAPED_IN_QUOTES = '"`$\\'


@dataclass(frozen=True)
class AppImage:
    # The AppImage file.
    path: Path

    # Where its content is while it runs.
    appdir: Path


def running_appimage(environ: dict[str, str] | None = None) -> AppImage | None:
    """The AppImage this runs from, if it does (Linux only): its runtime says so in $APPIMAGE and $APPDIR."""
    env = os.environ if environ is None else environ
    if not sys.platform.startswith("linux") or not env.get("APPIMAGE") or not env.get("APPDIR"):
        return None
    path, appdir = Path(env["APPIMAGE"]), Path(env["APPDIR"])
    return AppImage(path, appdir) if path.is_file() and appdir.is_dir() else None


def data_home(environ: dict[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    return Path(env["XDG_DATA_HOME"]) if env.get("XDG_DATA_HOME") else Path.home() / ".local/share"


def exec_argument(path: Path) -> str:
    """`path` as an argument of `Exec`: in double quotes if it needs them, with what needs it escaped inside."""
    text = str(path)
    if not RESERVED & set(text):
        return text
    return '"' + "".join("\\" + c if c in ESCAPED_IN_QUOTES else c for c in text) + '"'


def string_value(text: str) -> str:
    """`text` as a value of a desktop entry (a backslash is written twice)."""
    return text.replace("\\", "\\\\")


def entry_for(template: str, program: Path, icon: Path) -> str:
    """The AppImage's desktop entry with `program` in it (`Exec` starts it with the file, `TryExec` checks it's
    there) and the installed icon's own path (found whatever the icon theme and its caches)."""
    lines = []
    for line in template.splitlines():
        if line.startswith("Exec="):
            lines.append(f"Exec={string_value(exec_argument(program))} %f")
            lines.append(f"TryExec={string_value(str(program))}")
        elif line.startswith("Icon="):
            lines.append(f"Icon={string_value(str(icon))}")
        elif not line.startswith("TryExec="):
            lines.append(line)
    return "\n".join(lines) + "\n"


def installed_program(entry: str) -> Path | None:
    """The program an installed entry is for (its `TryExec`)."""
    for line in entry.splitlines():
        if line.startswith("TryExec="):
            return Path(line.removeprefix("TryExec=").replace("\\\\", "\\"))
    return None


class DesktopEntry:
    """The desktop entry, the icon and the file type of projects in the user's data folder."""

    def __init__(self, data: Path) -> None:
        self.entry = data / "applications" / f"{ENTRY_NAME}.desktop"
        self.icon = data / "icons/hicolor/256x256/apps" / f"{ENTRY_NAME}.png"
        self.mime = data / "mime/packages" / f"{ENTRY_NAME}.xml"
        self._data = data

    def installed_for(self) -> Path | None:
        """The AppImage the installed entry starts, if there's one."""
        if not self.entry.is_file():
            return None
        return installed_program(self.entry.read_text(encoding="utf-8"))

    def install(self, appimage: AppImage) -> None:
        """Install the entry (for this AppImage), the icon and the file type; raises OSError if it can't."""
        template = (appimage.appdir / APPDIR_ENTRY).read_text(encoding="utf-8")
        for path in (self.entry, self.icon, self.mime):
            path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(appimage.appdir / APPDIR_ICON, self.icon)
        shutil.copyfile(appimage.appdir / APPDIR_MIME, self.mime)
        self.entry.write_text(entry_for(template, appimage.path, self.icon), encoding="utf-8")
        self._tell_the_desktop()

    def refresh(self, appimage: AppImage) -> bool:
        """Install it again if it's for another place (the AppImage was moved, or this is another copy) or gone;
        whether it was."""
        if self.installed_for() == appimage.path and self.icon.is_file() and self.mime.is_file():
            return False
        self.install(appimage)
        return True

    def remove(self) -> None:
        for path in (self.entry, self.icon, self.mime):
            path.unlink(missing_ok=True)
        self._tell_the_desktop()

    def _tell_the_desktop(self) -> None:
        """Have the desktop read its file types and entries again (if its tools are there; nothing breaks if not:
        it reads them at the next login anyway)."""
        for tool, folder in (("update-mime-database", "mime"), ("update-desktop-database", "applications")):
            found = shutil.which(tool)
            if found and (self._data / folder).is_dir():
                subprocess.run(
                    [found, str(self._data / folder)], env=system_environment(), capture_output=True, check=False
                )


def system_environment() -> dict[str, str]:
    """The environment for the system's own programs: without what the AppImage's start set for itself (the library
    path to its own libraries, the GLib modules' folder), which would make them load the wrong libraries."""
    env = dict(os.environ)
    original = env.pop("LD_LIBRARY_PATH_ORIG", None)  # PyInstaller keeps what it was before it changed it
    if original is not None:
        env["LD_LIBRARY_PATH"] = original
    else:
        env.pop("LD_LIBRARY_PATH", None)
    env.pop("GIO_MODULE_DIR", None)
    return env
