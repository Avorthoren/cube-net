# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The release workflow's check of a pushed tag: `python -m scripts.check_release v1.2.0 notes.md` (from the root).

The rules of `release.sh` (the same code: `scripts/release.py`), for a tag that may have been pushed by hand:
1. The tag is "v" + a valid version (PEP 440, no leading zeros, an optional -alpha, -beta or -rc).
2. Its commit is on `master` (as fetched from origin).
3. It's the version of the package (`cube_net.__version__` at that commit).
4. It isn't lower than any other release tag.
5. CHANGELOG.md has a non-empty section for it ("## 1.2.0 (2026-11-20)", as `release.sh` makes it): its text is
   written to the notes file, for the release.
On GitHub Actions it also tells the workflow the version and whether it's a pre-release (`GITHUB_OUTPUT`).
"""

import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from scripts.release import (
    BRANCH,
    CHANGELOG_FILE,
    REMOTE,
    ROOT,
    VERSION_FILE,
    Git,
    ReleaseError,
    Version,
    check_not_lower,
    check_version,
    version_notes,
)

# The version in `cube_net/__init__.py`.
PACKAGE_VERSION = re.compile(r'^__version__ = "([^"]*)"$', re.MULTILINE)


def check_tag(tag: str) -> Version:
    if not tag.startswith("v"):
        raise ReleaseError(f'A release tag starts with "v": {tag!r} isn\'t one.')
    return check_version(tag[1:])


def package_version(source: str) -> str:
    match = PACKAGE_VERSION.search(source)
    if match is None:
        raise ReleaseError(f"{VERSION_FILE} has no __version__ line.")
    return match.group(1)


def check_package_version(version: Version, source: str) -> None:
    found = package_version(source)
    if found != version.text:
        raise ReleaseError(f"The tag is {version.tag}, but the package says {found}: they must be the same version.")


def check_version_notes(version: Version, changelog: str | None) -> str:
    notes = None if changelog is None else version_notes(changelog, version)
    if not notes:
        raise ReleaseError(f'{CHANGELOG_FILE} has no section "## {version.text} (...)" with something in it.')
    return notes


def check(tag: str, root: Path = ROOT) -> tuple[Version, str]:
    """The version of `tag` and its notes, if every rule holds for it."""
    git = Git(root)
    version = check_tag(tag)
    if not git("tag", "--list", tag):
        raise ReleaseError(f"There's no tag {tag} here.")
    commit = git("rev-list", "-n", "1", tag)
    try:
        git("merge-base", "--is-ancestor", commit, f"{REMOTE}/{BRANCH}")
    except ReleaseError:
        raise ReleaseError(f"{tag} isn't on {BRANCH}: releases are made from {BRANCH}.") from None
    check_package_version(version, git("show", f"{commit}:{VERSION_FILE.as_posix()}"))
    others = [t for t in git("tag", "--list", "v*").split() if t != tag]
    check_not_lower(version, others)
    changelog = git("show", f"{commit}:{CHANGELOG_FILE.as_posix()}") if _exists(git, commit, CHANGELOG_FILE) else None
    return version, check_version_notes(version, changelog)


def _exists(git: Git, commit: str, path: Path) -> bool:
    return bool(git("ls-tree", "--name-only", commit, "--", path.as_posix()))


def main(argv: Sequence[str] | None = None, root: Path = ROOT) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 2:
        print("Usage: python -m scripts.check_release TAG NOTES_FILE", file=sys.stderr)
        return 2
    tag, notes_file = args
    try:
        version, notes = check(tag, root)
    except ReleaseError as error:
        print(f"::error::{error}" if os.environ.get("GITHUB_ACTIONS") else str(error), file=sys.stderr)
        return 1
    Path(notes_file).write_text(notes + "\n", encoding="utf-8")
    print(f"{tag}: every check passed. The notes:\n{notes}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as file:
            file.write(f"version={version.text}\nprerelease={'true' if version.pre else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
