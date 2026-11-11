# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make a release for trying the update without publishing one: `python scripts/make_test_release.py PACKAGE VERSION`.

Next to PACKAGE (a build's package: an AppImage, a Windows installer, a .dmg) it writes SHA256SUMS and latest.json,
shaped like GitHub's answer about its latest release, with file:// links to them. A built app started with
CUBE_NET_UPDATES_URL set to latest.json's link (printed at the end) takes it for the latest release: Help -> Check
for updates then offers VERSION, downloads PACKAGE from the disk, checks it and installs it, as it would from GitHub.
"""

import hashlib
import json
import sys
from pathlib import Path

from cube_net.core.version import parse_version


def make(package: Path, version: str) -> Path:
    """Write SHA256SUMS and latest.json next to `package`; latest.json's path."""
    if parse_version(version) is None:
        raise ValueError(f"{version!r} isn't a version (1.2.0, 1.2.0-beta, ...)")
    folder = package.resolve().parent
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    sums = folder / "SHA256SUMS"
    sums.write_text(f"{digest}  {package.name}\n", encoding="utf-8")
    answer = {
        "tag_name": f"v{version}",
        "body": f"- A test release ({package.name}), made by scripts/make_test_release.py.",
        "html_url": folder.as_uri(),
        "assets": [
            {"name": package.name, "size": package.stat().st_size, "browser_download_url": package.resolve().as_uri()},
            {"name": sums.name, "size": sums.stat().st_size, "browser_download_url": sums.as_uri()},
        ],
    }
    latest = folder / "latest.json"
    latest.write_text(json.dumps(answer, indent=2), encoding="utf-8")
    return latest


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("Usage: python scripts/make_test_release.py PACKAGE VERSION", file=sys.stderr)
        return 2
    latest = make(Path(args[0]), args[1])
    print(f"Start the app to update with:\n  CUBE_NET_UPDATES_URL={latest.as_uri()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
