# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make a release of Cube Net: `./release.sh 1.2.0` (or `python scripts/release.py 1.2.0`), `--dry-run` to only check.

In this order, stopping at the first problem (in red, with what to do):
1. The version: MAJOR.MINOR.PATCH, without leading zeros, optionally with -alpha, -beta or -rc and a number
   (1.2.0-beta, 1.2.0-rc.2, 1.2.0-alpha3): a version Python's packaging accepts (PEP 440). The tag is "v" + it.
2. The working tree is clean, 3. on `master`.
4. Fetch the tags and pull `master` (fast-forward only; a dry run doesn't pull, it tells if it would).
5. The tag doesn't exist yet, 6. and the version isn't lower than the highest released one. Pre-releases of a version
   are all equal, and lower than the version itself: 1.2.0-alpha == 1.2.0-beta.2 < 1.2.0.
7. CHANGELOG.md has a "## Unreleased" section with something in it: the notes of this release.
8. ruff finds nothing (if `RUN_RUFF`), 9. and the tests pass (their output is shown if they don't).
Then, after a summary and a "y" from the user: the version and today's date go into `cube_net/__init__.py`, the
"Unreleased" section becomes this version's (and a new empty one starts above it), all that is committed as
"Release vX", tagged "vX" (an annotated tag) and pushed with `master` at once (both or neither).
"""

import argparse
import datetime
import importlib.util
import os
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

# Whether a release first checks the code with ruff (lint and formatting; it never fixes anything).
RUN_RUFF = True

# The repository, and where in it the version and the release notes are.
ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = Path("src/cube_net/__init__.py")
CHANGELOG_FILE = Path("CHANGELOG.md")

# Releases are made from this branch of this remote.
BRANCH = "master"
REMOTE = "origin"

# The heading of the changelog's section for what isn't released yet.
UNRELEASED = "## Unreleased"

# A version: numbers without leading zeros (but a lone 0), and an optional pre-release suffix.
VERSION_PATTERN = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-(alpha|beta|rc)(\.?(0|[1-9]\d*))?)?")

# The lines of `__init__.py` the release sets.
VERSION_LINE = re.compile(r'^__version__ = "[^"]*"$', re.MULTILINE)
DATE_LINE = re.compile(r'^__version_date__ = "[^"]*"$', re.MULTILINE)

# Colours for a terminal.
RED = "\033[31m"
GREEN = "\033[32m"
BOLD = "\033[1m"
RESET = "\033[0m"


class ReleaseError(Exception):
    """A check failed: the message says what's wrong, and what to do."""


@dataclass(frozen=True)
class Version:
    text: str
    major: int
    minor: int
    patch: int

    # The pre-release suffix (without the dash), if there's one: "beta.2".
    pre: str | None

    @property
    def tag(self) -> str:
        return f"v{self.text}"

    @property
    def order(self) -> tuple[int, int, int, int]:
        """What versions are compared by: the numbers, then a pre-release below the version itself (pre-releases of
        the same version are equal to each other)."""
        return self.major, self.minor, self.patch, 0 if self.pre is not None else 1


def parse_version(text: str) -> Version | None:
    """The version written as `text`, or None if it isn't one."""
    match = VERSION_PATTERN.fullmatch(text)
    if match is None:
        return None
    major, minor, patch, suffix = match.group(1), match.group(2), match.group(3), match.group(4)
    return Version(text, int(major), int(minor), int(patch), suffix[1:] if suffix else None)


def check_version(text: str) -> Version:
    if text.startswith("v"):
        raise ReleaseError(f'Give the version without the "v": {text[1:]} (the tag gets it: {text}).')
    version = parse_version(text)
    if version is None:
        raise ReleaseError(
            f"{text!r} isn't a version. Write MAJOR.MINOR.PATCH, without leading zeros, optionally with -alpha, -beta "
            "or -rc and a number: 1.2.0, 1.2.0-beta, 1.2.0-rc.2."
        )
    from packaging.version import InvalidVersion
    from packaging.version import Version as Pep440

    try:
        Pep440(text)
    except InvalidVersion:  # the pattern only lets through what PEP 440 accepts: this is a safety net
        raise ReleaseError(f"Python's packaging doesn't accept {text!r} as a version (PEP 440).") from None
    return version


def highest(versions: Sequence[Version]) -> Version | None:
    """The highest of `versions` (the first of equal ones), if there's any."""
    best: Version | None = None
    for version in versions:
        if best is None or version.order > best.order:
            best = version
    return best


def check_not_lower(version: Version, tags: Sequence[str]) -> Version | None:
    """The highest released version (from the tags "vX"; others don't count), if `version` isn't lower than it."""
    released = [v for tag in tags if tag.startswith("v") and (v := parse_version(tag[1:])) is not None]
    latest = highest(released)
    if latest is not None and version.order < latest.order:
        raise ReleaseError(f"{version.text} is lower than the latest release, {latest.text}.")
    return latest


def section_notes(changelog: str, heading: Callable[[str], bool]) -> str | None:
    """What's under the first "## " heading that `heading` accepts (up to the next "## " heading), or None if there's
    no such section."""
    lines = changelog.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("## ") and heading(line.rstrip()))
    except StopIteration:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1 : end]).strip()


def unreleased_notes(changelog: str) -> str | None:
    """What's under "## Unreleased", or None if there's no such section."""
    return section_notes(changelog, lambda line: line == UNRELEASED)


def version_notes(changelog: str, version: Version) -> str | None:
    """What's under the section of `version` ("## 1.2.0 (2026-11-20)", as a release makes it), or None."""
    return section_notes(
        changelog, lambda line: line == f"## {version.text}" or line.startswith(f"## {version.text} (")
    )


def check_notes(changelog: str | None) -> str:
    if changelog is None:
        raise ReleaseError(f'There\'s no {CHANGELOG_FILE}: make one, with a "{UNRELEASED}" section for this release.')
    notes = unreleased_notes(changelog)
    if notes is None:
        raise ReleaseError(f'{CHANGELOG_FILE} has no "{UNRELEASED}" section: add one, with what\'s new.')
    if not notes:
        raise ReleaseError(f'The "{UNRELEASED}" section of {CHANGELOG_FILE} is empty: write what\'s new in it.')
    return notes


def released_changelog(changelog: str, version: Version, day: datetime.date) -> str:
    """The changelog with its "Unreleased" section given to `version`, and a new empty one above it."""
    lines = changelog.splitlines(keepends=True)
    i = next(i for i, line in enumerate(lines) if line.rstrip() == UNRELEASED)
    lines[i] = f"{UNRELEASED}\n\n## {version.text} ({day.isoformat()})\n"
    return "".join(lines)


def versioned(source: str, version: Version, day: datetime.date) -> str:
    """`__init__.py` with this version and its date (ISO, as About shows it)."""
    for line in (VERSION_LINE, DATE_LINE):
        if line.search(source) is None:
            raise ReleaseError(f"{VERSION_FILE} has no line like {line.pattern.strip('^$')}.")
    source = VERSION_LINE.sub(f'__version__ = "{version.text}"', source)
    return DATE_LINE.sub(f'__version_date__ = "{day.isoformat()}"', source)


def github_page(remote_url: str) -> str | None:
    """The repository's page on GitHub, from the remote's URL (https or ssh), if it's there."""
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?/?", remote_url.strip())
    return f"https://github.com/{match.group(1)}" if match else None


# --- the repository and the tools ----------------------------------------------------------------------------------


class Git:
    def __init__(self, root: Path) -> None:
        self.root = root

    def __call__(self, *args: str) -> str:
        """Run git; its output, or a ReleaseError with what it said."""
        done = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)
        if done.returncode != 0:
            said = (done.stderr or done.stdout).strip()
            raise ReleaseError(f"git {' '.join(args)} failed:\n{said}")
        return done.stdout.strip()


def run_checks(root: Path) -> None:
    """ruff (if `RUN_RUFF`) and the tests; what they say is shown only if they fail."""
    if RUN_RUFF:
        for args, what in ((["check", "."], "ruff check"), (["format", "--check", "."], "ruff format --check")):
            say(f"Running {what}...")
            _tool(root, [sys.executable, "-m", "ruff", *args], f"{what} found problems (see above).")
    say("Running the tests...")
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}  # no windows on the screen while they run
    _tool(root, [sys.executable, "-m", "pytest", "-q", "--color=yes"], "The tests failed (see above).", env)


def _tool(root: Path, command: list[str], failure: str, env: dict[str, str] | None = None) -> None:
    done = subprocess.run(command, cwd=root, capture_output=True, text=True, env=env)
    if done.returncode != 0:
        print(done.stdout, end="")
        print(done.stderr, end="", file=sys.stderr)
        raise ReleaseError(failure)


def check_tools() -> None:
    """The tools the checks need are in this Python."""
    needed = ["packaging", "pytest", *(["ruff"] if RUN_RUFF else [])]
    missing = [name for name in needed if importlib.util.find_spec(name) is None]
    if missing:
        raise ReleaseError(
            f"This Python ({sys.executable}) has no {', '.join(missing)}: activate the project's virtual environment "
            '(pip install -e ".[dev]"), or point PYTHON at its python.'
        )


def confirm(question: str) -> bool:
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


# --- the release --------------------------------------------------------------------------------------------------


def release(text: str, dry_run: bool, root: Path = ROOT, today: datetime.date | None = None) -> None:
    day = today or datetime.date.today()
    git = Git(root)
    version = check_version(text)
    say(f"Version {version.text}, tag {version.tag}")
    check_tools()

    if git("status", "--porcelain"):
        raise ReleaseError("The working tree isn't clean: commit or stash the changes first.")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != BRANCH:
        raise ReleaseError(f"This is {branch!r}, not {BRANCH!r}: releases are made from {BRANCH}.")

    say(f"Fetching {REMOTE}...")
    git("fetch", "--tags", REMOTE)
    behind = int(git("rev-list", "--count", f"{BRANCH}..{REMOTE}/{BRANCH}"))
    if behind and dry_run:
        say(f"{BRANCH} is {behind} commit(s) behind {REMOTE}: a real run would pull them first (not checked here).")
    elif behind:
        say(f"Pulling {behind} commit(s)...")
        git("pull", "--ff-only", REMOTE, BRANCH)

    if git("tag", "--list", version.tag):
        raise ReleaseError(f"The tag {version.tag} exists already: choose another version.")
    latest = check_not_lower(version, git("tag", "--list", "v*").split())
    changelog_path = root / CHANGELOG_FILE
    changelog = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else None
    notes = check_notes(changelog)
    run_checks(root)

    say("")
    say(f"{BOLD}Release {version.tag}{RESET}" + (f" (the latest so far: {latest.tag})" if latest else " (the first)"))
    say(f"  from {git('log', '-1', '--format=%h %s')}")
    if latest is not None:
        say(f"  {git('rev-list', '--count', f'{latest.tag}..HEAD')} commit(s) since {latest.tag}")
    say("  Notes:")
    for line in notes.splitlines():
        say(f"    {line}")
    say("")
    if dry_run:
        say(f"{GREEN}Dry run: every check passed; nothing was changed.{RESET}")
        return
    if not confirm(f"Commit, tag {version.tag} and push to {REMOTE}?"):
        say("Nothing was changed.")
        return

    assert changelog is not None
    version_path = root / VERSION_FILE
    version_path.write_text(versioned(version_path.read_text(encoding="utf-8"), version, day), encoding="utf-8")
    changelog_path.write_text(released_changelog(changelog, version, day), encoding="utf-8")
    git("add", str(VERSION_FILE), str(CHANGELOG_FILE))
    git("commit", "-m", f"Release {version.tag}")
    git("tag", "-a", version.tag, "-m", f"Cube Net {version.text}")
    say(f"Pushing {BRANCH} and {version.tag}...")
    try:
        git("push", "--atomic", REMOTE, BRANCH, version.tag)
    except ReleaseError as error:
        raise ReleaseError(
            f"{error}\nThe release commit and the tag are made here, but not pushed. Push them with\n"
            f"  git push --atomic {REMOTE} {BRANCH} {version.tag}\n"
            f"or undo them with\n  git tag -d {version.tag} && git reset --hard HEAD~1"
        ) from None
    say(f"{GREEN}Released {version.tag}.{RESET}")
    page = github_page(git("remote", "get-url", REMOTE))
    if page is not None:
        say(f"The build: {page}/actions")
        say(f"The draft release, once it's built: {page}/releases")


# --- the command line --------------------------------------------------------------------------------------------


def say(text: str) -> None:
    print(text if sys.stdout.isatty() else _plain(text), flush=True)  # before anything that goes to stderr


def _plain(text: str) -> str:
    return re.sub(r"\033\[\d+m", "", text)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Make a release of Cube Net (see the docstring of scripts/release.py)."
    )
    parser.add_argument("version", help="the new version, without the v: 1.2.0, 1.2.0-beta, 1.2.0-rc.2")
    parser.add_argument("--dry-run", action="store_true", help="only check: change, commit and push nothing")
    args = parser.parse_args(argv)
    try:
        release(args.version, args.dry_run)
    except ReleaseError as error:
        message = str(error)
        print(f"{RED}{message}{RESET}" if sys.stderr.isatty() else message, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped; nothing was changed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
