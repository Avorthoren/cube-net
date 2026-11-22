# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The state of the project (or the template) in a session log: one line with the whole of it, so that a log can be
reproduced exactly.

The line holds the bytes of a project file, in base64. To get them back as files that the app can open:

    python -m cube_net.ui.session.snapshots <session log>

There's one more snapshot whenever another project comes along during the session. No Qt here: it runs anywhere.
"""

import base64
import binascii
import contextlib
import sys
from pathlib import Path

from cube_net.core.project import (
    PROJECT_SUFFIX,
    TEMPLATE_SUFFIX,
    Project,
    ProjectFileError,
    TemplateDocument,
    document_from_bytes,
    project_to_bytes,
    template_to_bytes,
)

# What comes after the time on a snapshot's line.
SNAPSHOT_FIELDS = ("state", "snapshot")


def snapshot_text(document: Project | TemplateDocument) -> str:
    """The project (or the template) as one word, to go into a log line."""
    content = project_to_bytes(document) if isinstance(document, Project) else template_to_bytes(document)
    return base64.b64encode(content).decode("ascii")


def snapshots_in(log: Path) -> list[bytes]:
    """The contents of project files, one for each snapshot in the log, in order. A line that was cut off (the app
    crashed while writing it) doesn't count: the snapshots before it are still good."""
    found = []
    with log.open(encoding="utf-8") as lines:
        for line in lines:
            fields = line.split()
            if len(fields) == 4 and not line.startswith("#") and tuple(fields[1:3]) == SNAPSHOT_FIELDS:
                with contextlib.suppress(binascii.Error):
                    found.append(base64.b64decode(fields[3], validate=True))
    return found


def extract_snapshots(log: Path) -> list[Path]:
    """Write the log's snapshots to files next to it: `<log's name>-1.cubenet`, ... Returns their paths."""
    paths = []
    for i, content in enumerate(snapshots_in(log), start=1):
        path = log.with_name(f"{log.stem}-{i}{_suffix(content)}")
        path.write_bytes(content)
        paths.append(path)
    return paths


def _suffix(content: bytes) -> str:
    """A template's file ending for a template, a project's for anything else."""
    try:
        return TEMPLATE_SUFFIX if isinstance(document_from_bytes(content), TemplateDocument) else PROJECT_SUFFIX
    except ProjectFileError:
        return PROJECT_SUFFIX


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m cube_net.ui.session.snapshots <session log>", file=sys.stderr)
        return 2
    paths = extract_snapshots(Path(argv[0]))
    for path in paths:
        print(path)
    if not paths:
        print("no snapshots in that log", file=sys.stderr)
    return 0 if paths else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
