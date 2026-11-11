# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Windows: the new installer does the update. A running program's files can't be replaced, so the installer is
started on its own, without questions (it shows its progress), and the application quits; the installer replaces it
(the same installation: the same AppId) and starts the new version (packaging/windows/cube_net.iss)."""

import subprocess
from collections.abc import Callable
from pathlib import Path

# The installer's options: no questions, no restart of Windows, and the running application closed if it's still
# there.
SILENT = ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"]


def start_installer(setup: Path, start: Callable[..., object] = subprocess.Popen) -> None:
    """Start the installer on its own: it outlives the application."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    start([str(setup), *SILENT], creationflags=flags, close_fds=True)
