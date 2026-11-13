# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make a release of Cube Net: `./release.sh 1.2.0` (or `python scripts/release.py 1.2.0`), `--dry-run` to only check
(`--dry-run-no-tests`: the same without the tests, which take long; ruff still runs).

In this order, stopping at the first problem (in red, with what to do):
1. The version: MAJOR.MINOR.PATCH, without leading zeros, optionally with -alpha, -beta or -rc and a number
   (1.2.0-beta, 1.2.0-rc.2, 1.2.0-alpha3): a version Python's packaging accepts (PEP 440). The tag is "v" + it.
2. The working tree is clean, 3. on `master`.
4. Fetch the tags and pull `master` (fast-forward only; a dry run doesn't pull, it tells if it would).
5. The tag doesn't exist yet, 6. and the version isn't lower than the highest released one. Pre-releases of a version
   are all equal, and lower than the version itself: 1.2.0-alpha == 1.2.0-beta.2 < 1.2.0.
7. CHANGELOG.md has a "## Unreleased" section with something in it: the notes of this release.
8. ruff finds nothing (if `RUN_RUFF`), 9. and the tests pass (one line shows their progress; their output is
   shown if they fail).
Then, after a summary and a "y" from the user: the version and today's date go into `cube_net/__init__.py`, the
"Unreleased" section becomes this version's (and a new empty one starts above it), all that is committed as
"Release vX", tagged "vX" (an annotated tag) and pushed with `master` at once (both or neither).

`./release.sh 1.2.0 --fix` (with `--dry-run` or `--dry-run-no-tests` too, if wanted): after such a release, when the
workflow failed on GitHub and the problem is fixed in new commits, the same version is tagged again on the fix (see
`fix`). Never for a version that's published: that one stays as it is, and the fix is the next version.
"""

import argparse
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path

from cube_net.core.version import Version, parse_version

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

# The lines of `__init__.py` the release sets.
VERSION_LINE = re.compile(r'^__version__ = "[^"]*"$', re.MULTILINE)
DATE_LINE = re.compile(r'^__version_date__ = "[^"]*"$', re.MULTILINE)

# The variable that tells the tests' progress plugin where to write (scripts/pytest_progress.py).
TEST_PROGRESS_VARIABLE = "CUBE_NET_TEST_PROGRESS_FD"

# GitHub's API, and how long to wait for its answer (s).
GITHUB_API = "https://api.github.com"
GITHUB_TIMEOUT = 20

# Colours for a terminal.
RED = "\033[31m"
GREEN = "\033[32m"
BOLD = "\033[1m"
RESET = "\033[0m"


class ReleaseError(Exception):
    """A check failed: the message says what's wrong, and what to do."""


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
    no such section: without the empty lines around it, and without the indentation all its lines share (" - a" and
    " - b" become "- a" and "- b", each line keeping its own place against the others)."""
    lines = changelog.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("## ") and heading(line.rstrip()))
    except StopIteration:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    section = [line.rstrip() for line in lines[start + 1 : end]]
    while section and not section[0]:
        section.pop(0)
    while section and not section[-1]:
        section.pop()
    return textwrap.dedent("\n".join(section))


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


def github_repository(remote_url: str) -> str | None:
    """ "owner/name" of the repository on GitHub, from the remote's URL (https or ssh), if it's there."""
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?/?", remote_url.strip())
    return match.group(1) if match else None


def github_page(remote_url: str) -> str | None:
    """The repository's page on GitHub, from the remote's URL, if it's there."""
    repository = github_repository(remote_url)
    return f"https://github.com/{repository}" if repository else None


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


def run_checks(root: Path, tests: bool = True) -> None:
    """ruff (if `RUN_RUFF`) and the tests (unless not `tests`); what they say is shown only if they fail."""
    if RUN_RUFF:
        for args, what in ((["check", "."], "ruff check"), (["format", "--check", "."], "ruff format --check")):
            say(f"Running {what}...")
            _tool(root, [sys.executable, "-m", "ruff", *args], f"{what} found problems (see above).")
    if tests:
        run_tests(root)
    else:
        say("Not running the tests (--dry-run-no-tests).")


def run_tests(root: Path, arguments: Sequence[str] = (), show: Callable[[str], None] | None = None) -> None:
    """The tests, with one line of progress ("Running the tests... 812 of 1706 (47%)", updated in place on a
    terminal), then how many passed. pytest's own output goes to a file, and is shown only if they fail.

    The progress comes from `scripts/pytest_progress.py`, through a pipe of its own: pytest's printed output isn't
    read for it."""
    tell = show or _show_progress
    read, write = os.pipe()
    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",  # no windows on the screen while they run
        TEST_PROGRESS_VARIABLE: str(write),
        "PYTHONPATH": os.pathsep.join(filter(None, [str(root), os.environ.get("PYTHONPATH")])),  # for the plugin
    }
    command = [sys.executable, "-m", "pytest", "-q", "--color=yes", "-p", "scripts.pytest_progress", *arguments]
    tell("Running the tests...")
    total = 0
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(
            command, cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT, pass_fds=(write,)
        )
        os.close(write)  # pytest's copy is the only one: the pipe ends when pytest does
        with os.fdopen(read, encoding="utf-8") as progress:
            for line in progress:
                done, total = (int(n) for n in line.split())
                percent = done * 100 // total if total else 100
                tell(f"Running the tests... {done} of {total} ({percent}%)")
        if process.wait() != 0:
            _end_progress()
            output.seek(0)
            print(output.read().decode("utf-8", "replace"), end="")
            raise ReleaseError("The tests failed (see above).")
    tell(f"Running the tests... {total} passed")
    _end_progress()


def _show_progress(text: str) -> None:
    """On a terminal, the line is rewritten in place; elsewhere (a log) only the end is worth a line."""
    if sys.stdout.isatty():
        sys.stdout.write(f"\r\033[K{text}")
        sys.stdout.flush()
    elif "passed" in text:
        print(text, flush=True)


def _end_progress() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\n")
        sys.stdout.flush()


def _tool(root: Path, command: list[str], failure: str, env: dict[str, str] | None = None) -> None:
    done = subprocess.run(command, cwd=root, capture_output=True, text=True, env=env)
    if done.returncode != 0:
        print(done.stdout, end="")
        print(done.stderr, end="", file=sys.stderr)
        raise ReleaseError(failure)


def check_tools(tests: bool = True) -> None:
    """The tools the checks need are in this Python."""
    needed = ["packaging", *(["pytest"] if tests else []), *(["ruff"] if RUN_RUFF else [])]
    missing = [name for name in needed if importlib.util.find_spec(name) is None]
    if missing:
        raise ReleaseError(
            f"This Python ({sys.executable}) has no {', '.join(missing)}: activate the project's virtual environment "
            '(pip install -e ".[dev]"), or point PYTHON at its python.'
        )


def github_releases(repository: str, tag: str) -> tuple[list[dict[str, object]], bool]:
    """GitHub's releases of `tag`, and whether drafts are among what it was asked about: they're visible only with a
    token of someone who can push there ($GITHUB_TOKEN). Without one, only a published release can be found."""
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "cube-net-release-script"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        found: list[dict[str, object]] = []
        for page in range(1, 11):  # 100 a page, newest first: plenty
            batch = _github(f"/repos/{repository}/releases?per_page=100&page={page}", headers)
            assert isinstance(batch, list)
            found += [r for r in batch if r.get("tag_name") == tag]
            if len(batch) < 100:
                break
        return found, True
    one = _github(f"/repos/{repository}/releases/tags/{urllib.parse.quote(tag)}", headers)
    return ([one] if isinstance(one, dict) else []), False


def _github(path: str, headers: dict[str, str]) -> object:
    """What GitHub's API answers (None for "not found"), or a ReleaseError if it can't be asked."""
    request = urllib.request.Request(GITHUB_API + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=GITHUB_TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise ReleaseError(f"GitHub answered {error.code} ({error.reason}) about {path}.") from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise ReleaseError(f"Couldn't ask GitHub about the releases ({error}): try again.") from None


def confirm(question: str) -> bool:
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


# --- the release --------------------------------------------------------------------------------------------------


def prepare(git: Git, text: str, dry_run: bool, tests: bool = True) -> Version:
    """What every run checks and does first: the version, the tools, a clean tree on master, the tags fetched and
    master pulled (a dry run doesn't pull: it tells if it would)."""
    version = check_version(text)
    say(f"Version {version.text}, tag {version.tag}")
    check_tools(tests)
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
    return version


def release(
    text: str, dry_run: bool, root: Path = ROOT, today: datetime.date | None = None, tests: bool = True
) -> None:
    """`tests`: False only with `dry_run` (--dry-run-no-tests)."""
    assert tests or dry_run
    day = today or datetime.date.today()
    git = Git(root)
    version = prepare(git, text, dry_run, tests)
    if git("tag", "--list", version.tag):
        raise ReleaseError(f"The tag {version.tag} exists already: choose another version (or --fix it).")
    latest = check_not_lower(version, git("tag", "--list", "v*").split())
    changelog_path = root / CHANGELOG_FILE
    changelog = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else None
    notes = check_notes(changelog)
    run_checks(root, tests)

    say("")
    say(f"{BOLD}Release {version.tag}{RESET}" + (f" (the latest so far: {latest.tag})" if latest else " (the first)"))
    say(f"  from {git('log', '-1', '--format=%h %s')}")
    if latest is not None:
        say(f"  {git('rev-list', '--count', f'{latest.tag}..HEAD')} commit(s) since {latest.tag}")
    _show_notes(notes)
    if dry_run:
        _dry_run_passed(tests)
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
    _show_links(git)


def fix(text: str, dry_run: bool, root: Path = ROOT, tests: bool = True) -> None:
    """Tag the version again, on the commit that fixes what made its workflow fail. After `prepare`:
    1. The tag exists, here and on the remote (the same one: fetching would have failed otherwise).
    2. It's on a commit `release` made ("Release vX"), and it's an annotated tag, as `release` makes them.
    3. That commit is in master's history, and there's something new after it (the fix).
    4. The package still says this version, and CHANGELOG.md still has its non-empty section.
    5. No other release tag is higher (the fix is for the latest release, not an older one).
    6. GitHub has no published release of it (never re-tagged: the fix of a published one is the next version), and
       no draft either, if it can be seen ($GITHUB_TOKEN); without a token, a reminder about drafts.
    7. ruff and the tests.
    Then, after a summary and a "y": the local tag is made again on the current commit, the remote one is deleted
    (only if it's still the one checked here) and master is pushed with the new tag, which starts the workflow."""
    assert tests or dry_run
    git = Git(root)
    version = prepare(git, text, dry_run, tests)
    tag = version.tag
    if not git("tag", "--list", tag):
        raise ReleaseError(f"There's no tag {tag}: --fix moves the tag of a release made before (without --fix).")
    remote = git("ls-remote", "--tags", REMOTE, f"refs/tags/{tag}")
    if not remote:
        raise ReleaseError(f"{tag} is here but not on {REMOTE}: its release didn't get pushed. Push it, or delete it.")
    remote_object = remote.split()[0]
    old = git("rev-list", "-n", "1", tag)
    if git("cat-file", "-t", tag) != "tag" or git("log", "-1", "--format=%s", old) != f"Release {tag}":
        raise ReleaseError(f'{tag} isn\'t a tag the release script made (annotated, on a commit "Release {tag}").')
    try:
        git("merge-base", "--is-ancestor", old, "HEAD")
    except ReleaseError:
        raise ReleaseError(f"{tag}'s commit isn't in {BRANCH}'s history: it can't be fixed from here.") from None
    if git("rev-parse", "HEAD") == old:
        raise ReleaseError(
            f"There's nothing after {tag}: commit the fix first. (If the workflow failed for nothing in the code, "
            'use "Re-run failed jobs" on its page instead.)'
        )
    found = _package_version((root / VERSION_FILE).read_text(encoding="utf-8"))
    if found != version.text:
        raise ReleaseError(f"The package says {found} now, not {version.text}: this isn't {tag}'s fix any more.")
    changelog_path = root / CHANGELOG_FILE
    changelog = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else ""
    notes = version_notes(changelog, version)
    if not notes:
        raise ReleaseError(f'{CHANGELOG_FILE} has no section "## {version.text} (...)" with something in it any more.')
    higher = [t for t in git("tag", "--list", "v*").split() if (v := parse_version(t[1:])) and v.order > version.order]
    if higher:
        raise ReleaseError(f"{', '.join(higher)} came after {tag}: only the latest release can be fixed this way.")
    _check_not_released(git, tag)
    run_checks(root, tests)

    say("")
    say(f"{BOLD}Fix {tag}{RESET}: move it from {git('log', '-1', '--format=%h %s', old)}")
    say(f"  to {git('log', '-1', '--format=%h %s')}, after:")
    for line in git("log", "--format=%h %s", f"{old}..HEAD").splitlines():
        say(f"    {line}")
    _show_notes(notes)
    if dry_run:
        _dry_run_passed(tests)
        return
    if not confirm(f"Move {tag} to this commit and push it with {BRANCH} to {REMOTE}?"):
        say("Nothing was changed.")
        return

    old_object = git("rev-parse", f"refs/tags/{tag}")
    git("tag", "-f", "-a", tag, "-m", f"Cube Net {version.text}")
    say(f"Moving {tag} on {REMOTE}...")
    try:
        git("push", f"--force-with-lease=refs/tags/{tag}:{remote_object}", REMOTE, f":refs/tags/{tag}")
    except ReleaseError as error:
        git("update-ref", f"refs/tags/{tag}", old_object)  # back as it was: nothing changed
        raise ReleaseError(f"{error}\n{tag} is as it was, here and on {REMOTE}.") from None
    try:
        git("push", "--atomic", REMOTE, BRANCH, tag)
    except ReleaseError as error:
        raise ReleaseError(
            f"{error}\n{tag} is deleted on {REMOTE} and made again here, on the fix. Push it with\n"
            f"  git push --atomic {REMOTE} {BRANCH} {tag}"
        ) from None
    say(f"{GREEN}{tag} is on the fix now.{RESET}")
    _show_links(git)


def _check_not_released(git: Git, tag: str) -> None:
    repository = github_repository(git("remote", "get-url", REMOTE))
    if repository is None:
        raise ReleaseError(f"{REMOTE} isn't on GitHub: there's no way to see whether {tag} is released.")
    say(f"Asking GitHub about {tag}'s release...")
    releases, with_drafts = github_releases(repository, tag)
    if any(not r.get("draft") for r in releases):
        raise ReleaseError(
            f"{tag} is published on GitHub: a published version is never tagged again. Release the fix as the next "
            "version instead."
        )
    if releases:
        raise ReleaseError(f"GitHub has a draft release of {tag}: delete it on the Releases page first.")
    if not with_drafts:
        say(f"  (Drafts can't be seen without $GITHUB_TOKEN: if there's one of {tag}, delete it on the Releases page.)")


def _package_version(source: str) -> str | None:
    match = re.search(r'^__version__ = "([^"]*)"$', source, re.MULTILINE)
    return match.group(1) if match else None


def _show_notes(notes: str) -> None:
    say("  Notes:")
    for line in notes.splitlines():
        say(f"    {line}")
    say("")


def _show_links(git: Git) -> None:
    page = github_page(git("remote", "get-url", REMOTE))
    if page is not None:
        say(f"The build: {page}/actions")
        say(f"The draft release, once it's built: {page}/releases")


# --- the command line --------------------------------------------------------------------------------------------


def say(text: str) -> None:
    print(text if sys.stdout.isatty() else _plain(text), flush=True)  # before anything that goes to stderr


def _dry_run_passed(tests: bool) -> None:
    passed = "every check passed" if tests else "every check passed (the tests weren't run)"
    say(f"{GREEN}Dry run: {passed}; nothing was changed.{RESET}")


def _plain(text: str) -> str:
    return re.sub(r"\033\[\d+m", "", text)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Make a release of Cube Net (see the docstring of scripts/release.py)."
    )
    parser.add_argument("version", help="the version, without the v: 1.2.0, 1.2.0-beta, 1.2.0-rc.2")
    dry = parser.add_mutually_exclusive_group()
    dry.add_argument("--dry-run", action="store_true", help="only check: change, commit and push nothing")
    dry.add_argument(
        "--dry-run-no-tests", action="store_true", help="the same as --dry-run, without the tests (ruff still runs)"
    )
    parser.add_argument(
        "--fix", action="store_true", help="tag this released (but not published) version again, on the fix"
    )
    args = parser.parse_args(argv)
    try:
        dry_run, tests = args.dry_run or args.dry_run_no_tests, not args.dry_run_no_tests
        if args.fix:
            fix(args.version, dry_run, tests=tests)
        else:
            release(args.version, dry_run, tests=tests)
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
