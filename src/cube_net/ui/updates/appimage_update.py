# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Linux: the new AppImage takes the old one's place, then starts.

Downloaded right next to the old one (its folder can be written), it's made executable and the old file is deleted
(the running AppImage doesn't mind: it runs from what it unpacked). The new one keeps its own name, which says its
version; the applications menu's entry follows it when it starts. Downloaded elsewhere (the folder needs administrator
rights, like /opt), the desktop's password window (`pkexec`) puts it in place; if that's not there, or cancelled, the
user finishes by hand (`ManualStepNeeded`).
"""

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from cube_net.ui.desktop_integration import system_environment
from cube_net.ui.updates.installation import ManualStepNeeded

# Run with administrator rights: put the new one ($1) in place ($2), executable, and delete the old one ($3) if it's
# another file.
PUT_IN_PLACE = 'install -m 0755 "$1" "$2" && { [ "$2" = "$3" ] || rm -f "$3"; }'

# What the AppImage's runtime set for the running one: the new one gets its own.
APPIMAGE_VARIABLES = ("APPIMAGE", "APPDIR", "ARGV0", "OWD")


def install_appimage(
    new: Path, current: Path, run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run
) -> Path:
    """Put `new` in place of `current`; the AppImage to start."""
    target = current.parent / new.name
    if new.parent == current.parent:
        new.chmod(0o755)
        if new != current:
            current.unlink(missing_ok=True)
        return new
    pkexec = shutil.which("pkexec")
    if pkexec is not None:
        done = run(
            [pkexec, "/bin/sh", "-c", PUT_IN_PLACE, "sh", str(new), str(target), str(current)],
            env=system_environment(),
            capture_output=True,
            check=False,
        )
        if done.returncode == 0:
            new.unlink(missing_ok=True)
            return target
    new.chmod(0o755)
    raise ManualStepNeeded(new, target)


def start_appimage(path: Path, start: Callable[..., object] = subprocess.Popen) -> None:
    """Start the AppImage on its own (it outlives this one), with the system's environment."""
    env = system_environment()
    for name in APPIMAGE_VARIABLES:
        env.pop(name, None)
    start([str(path)], env=env, start_new_session=True, close_fds=True, cwd=os.path.expanduser("~"))
