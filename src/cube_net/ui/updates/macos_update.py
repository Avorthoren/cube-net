# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""macOS: the new "Cube Net.app" (from the downloaded .dmg) takes the old one's place, then starts.

The bundle can't be replaced while it runs, so a small script does it once the application has quit: it opens the
.dmg out of sight, copies the new bundle next to the old one, swaps them (the old one comes back if the copy fails),
closes the .dmg and starts the new one. Downloaded by the application itself, the .dmg isn't marked as coming from
the internet, so Gatekeeper doesn't ask again. If the bundle's folder can't be written, the user finishes by hand:
the .dmg is opened in Finder (`ManualStepNeeded`).
"""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from cube_net.ui.updates.installation import ManualStepNeeded

# The script: $1 the application's process, $2 the .dmg, $3 the bundle to replace.
SWAP = """#!/bin/sh
pid="$1"; dmg="$2"; bundle="$3"
while kill -0 "$pid" 2>/dev/null; do sleep 0.3; done
mount="$(mktemp -d)"
hdiutil attach -nobrowse -quiet -mountpoint "$mount" "$dmg" || exit 1
new="$(find "$mount" -maxdepth 1 -name '*.app' | head -n 1)"
if [ -n "$new" ] && ditto "$new" "$bundle.new"; then
    rm -rf "$bundle.old" && mv "$bundle" "$bundle.old" && mv "$bundle.new" "$bundle" && rm -rf "$bundle.old"
else
    rm -rf "$bundle.new"
fi
hdiutil detach -quiet "$mount"
rm -f "$dmg"
open "$bundle"
"""


def install_macos(dmg: Path, bundle: Path, pid: int, start: Callable[..., object] = subprocess.Popen) -> None:
    """Have the new bundle replace `bundle` once the process `pid` (this application) has quit."""
    if not (os.access(bundle.parent, os.W_OK) and os.access(bundle, os.W_OK)):
        raise ManualStepNeeded(dmg, bundle)
    script = dmg.parent / "update.sh"
    script.write_text(SWAP, encoding="utf-8")
    start(["/bin/sh", str(script), str(pid), str(dmg), str(bundle)], start_new_session=True, close_fds=True)


def open_in_finder(dmg: Path, start: Callable[..., object] = subprocess.Popen) -> None:
    """Show the .dmg in Finder, for dragging the new version onto Applications by hand."""
    start(["open", str(dmg)])
