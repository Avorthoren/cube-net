# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The release script: its rules, and whole releases in throwaway repositories (with a bare one as the remote)."""

import datetime
import re
import subprocess
from pathlib import Path

import pytest
from scripts.release import ReleaseError, Version, parse_version

from scripts import release

DAY = datetime.date(2026, 11, 20)


def v(text: str) -> Version:
    version = parse_version(text)
    assert version is not None
    return version


class TestVersions:
    @pytest.mark.parametrize(
        "text", ["0.0.0", "1.0.0", "1.2.3", "10.20.30", "1.2.0-alpha", "1.2.0-beta.2", "1.2.0-rc1", "1.2.0-rc.0"]
    )
    def test_valid(self, text: str) -> None:
        assert release.check_version(text).text == text

    @pytest.mark.parametrize(
        "text",
        [
            "1.0",
            "1.2.3.4",
            "01.2.3",
            "1.02.3",
            "1.2.03",
            "1.2.0-alpha1a2b3c",
            "1.2.0-gamma",
            "1.2.0-beta.02",
            "1.2.0b2",
        ],
    )
    def test_invalid(self, text: str) -> None:
        with pytest.raises(ReleaseError, match="isn't a version"):
            release.check_version(text)

    def test_without_the_v(self) -> None:
        with pytest.raises(ReleaseError, match='without the "v"'):
            release.check_version("v1.2.0")

    def test_the_tag_has_it(self) -> None:
        assert v("1.2.0-beta").tag == "v1.2.0-beta"

    def test_order(self) -> None:
        assert v("1.2.0-alpha").order == v("1.2.0-beta.2").order == v("1.2.0-alpha3").order
        assert v("1.2.0-rc.9").order < v("1.2.0").order < v("1.2.1-alpha").order < v("1.2.1").order
        assert v("1.9.9").order < v("1.10.0").order  # numbers, not text

    def test_not_lower_than_the_highest_release(self) -> None:
        tags = ["v1.2.0", "v1.3.0-beta", "v1.1.0", "not-a-version", "v2"]
        assert release.check_not_lower(v("1.3.0-rc.1"), tags) == v("1.3.0-beta")  # equal pre-releases are fine
        assert release.check_not_lower(v("1.3.0"), tags) is not None
        with pytest.raises(ReleaseError, match=re.escape("lower than the latest release, 1.3.0-beta")):
            release.check_not_lower(v("1.2.5"), tags)
        with pytest.raises(ReleaseError):
            release.check_not_lower(v("1.3.0-beta"), [*tags, "v1.3.0"])

    def test_the_first_release_can_be_anything(self) -> None:
        assert release.check_not_lower(v("0.0.1"), []) is None


CHANGELOG = """# Changelog

## Unreleased

- New: Ctrl+click deletes a point.

## 1.0.0 (2026-11-01)

- The first release.
"""


class TestChangelog:
    def test_the_unreleased_notes(self) -> None:
        assert release.check_notes(CHANGELOG) == "- New: Ctrl+click deletes a point."

    @pytest.mark.parametrize(
        ("changelog", "problem"),
        [
            (None, "There's no CHANGELOG.md"),
            ("# Changelog\n\n## 1.0.0\n\n- Something.\n", "has no"),
            ("# Changelog\n\n## Unreleased\n\n   \n\t\n## 1.0.0\n\n- Something.\n", "is empty"),
            ("# Changelog\n\n## Unreleased\n", "is empty"),
        ],
    )
    def test_problems(self, changelog: str | None, problem: str) -> None:
        with pytest.raises(ReleaseError, match=problem):
            release.check_notes(changelog)

    def test_the_section_becomes_the_versions_and_a_new_one_starts(self) -> None:
        released = release.released_changelog(CHANGELOG, v("1.1.0"), DAY)
        assert "## Unreleased\n\n## 1.1.0 (2026-11-20)\n\n- New: Ctrl+click deletes a point.\n\n## 1.0.0" in released
        assert release.unreleased_notes(released) == ""


def test_the_version_and_its_date_in_the_package() -> None:
    source = '"""Cube Net."""\n\n__version__ = "1.0"\n\n# When.\n__version_date__ = "2026-11-10"\n'
    assert release.versioned(source, v("1.2.0-rc.1"), DAY) == (
        '"""Cube Net."""\n\n__version__ = "1.2.0-rc.1"\n\n# When.\n__version_date__ = "2026-11-20"\n'
    )
    with pytest.raises(ReleaseError, match="__version_date__"):
        release.versioned('__version__ = "1.0"\n', v("1.2.0"), DAY)


def test_the_real_package_has_both_lines() -> None:
    source = (release.ROOT / release.VERSION_FILE).read_text(encoding="utf-8")
    assert release.versioned(source, v("9.9.9"), DAY) != source


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/Avorthoren/cube-net.git",
        "https://github.com/Avorthoren/cube-net",
        "git@github.com:Avorthoren/cube-net.git",
    ],
)
def test_the_github_page(url: str) -> None:
    assert release.github_page(url) == "https://github.com/Avorthoren/cube-net"
    assert release.github_page("https://example.com/x/y.git") is None


# --- whole releases ------------------------------------------------------------------------------------------------


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A clone of a bare "origin", on master, with the package's version file, a changelog and one commit pushed.
    The checks (ruff, tests) pass at once, and the user says "y"."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "master", str(origin))
    root = tmp_path / "work"
    git(tmp_path, "clone", str(origin), str(root))
    git(root, "checkout", "-b", "master")
    git(root, "config", "user.name", "Tester")
    git(root, "config", "user.email", "tester@example.com")
    package = root / "src" / "cube_net"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "1.0"\n\n__version_date__ = "2026-11-10"\n')
    (root / "CHANGELOG.md").write_text(CHANGELOG)
    git(root, "add", ".")
    git(root, "commit", "-m", "Start")
    git(root, "push", "-u", "origin", "master")
    monkeypatch.setattr(release, "run_checks", lambda root: None)
    monkeypatch.setattr(release, "confirm", lambda question: True)
    return root


def remote_tags(root: Path) -> str:
    return git(root, "ls-remote", "--tags", "origin")


def test_a_release_commits_tags_and_pushes(repo: Path) -> None:
    release.release("1.1.0", dry_run=False, root=repo, today=DAY)
    assert git(repo, "log", "-1", "--format=%s") == "Release v1.1.0"
    assert git(repo, "status", "--porcelain") == ""
    assert '__version__ = "1.1.0"' in (repo / "src/cube_net/__init__.py").read_text()
    assert '__version_date__ = "2026-11-20"' in (repo / "src/cube_net/__init__.py").read_text()
    assert "## 1.1.0 (2026-11-20)" in (repo / "CHANGELOG.md").read_text()
    assert git(repo, "cat-file", "-t", "v1.1.0") == "tag"  # an annotated one
    assert git(repo, "tag", "-l", "--format=%(contents:subject)", "v1.1.0") == "Cube Net 1.1.0"
    assert "refs/tags/v1.1.0" in remote_tags(repo)
    assert git(repo, "rev-parse", "origin/master") == git(repo, "rev-parse", "HEAD")


def test_a_dry_run_changes_nothing(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD")
    release.release("1.1.0", dry_run=True, root=repo, today=DAY)
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == ""
    assert git(repo, "tag") == "" and remote_tags(repo) == ""


def test_no_means_nothing_changes(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release, "confirm", lambda question: False)
    head = git(repo, "rev-parse", "HEAD")
    release.release("1.1.0", dry_run=False, root=repo, today=DAY)
    assert git(repo, "rev-parse", "HEAD") == head and git(repo, "status", "--porcelain") == ""


def test_a_dirty_tree_stops_it(repo: Path) -> None:
    (repo / "notes.txt").write_text("not committed")
    with pytest.raises(ReleaseError, match="isn't clean"):
        release.release("1.1.0", dry_run=False, root=repo, today=DAY)


def test_only_from_master(repo: Path) -> None:
    git(repo, "checkout", "-b", "feature")
    with pytest.raises(ReleaseError, match="not 'master'"):
        release.release("1.1.0", dry_run=False, root=repo, today=DAY)


def test_a_tag_on_the_remote_counts(repo: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    git(tmp_path, "clone", str(tmp_path / "origin.git"), str(other))
    git(other, "tag", "v2.0.0")
    git(other, "push", "origin", "v2.0.0")
    with pytest.raises(ReleaseError, match="exists already"):
        release.release("2.0.0", dry_run=False, root=repo, today=DAY)
    with pytest.raises(ReleaseError, match=re.escape("lower than the latest release, 2.0.0")):
        release.release("1.9.0", dry_run=False, root=repo, today=DAY)


def test_new_commits_on_the_remote_are_pulled_first(repo: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    git(tmp_path, "clone", str(tmp_path / "origin.git"), str(other))
    git(other, "config", "user.name", "Tester")
    git(other, "config", "user.email", "tester@example.com")
    (other / "new.txt").write_text("from elsewhere")
    git(other, "add", ".")
    git(other, "commit", "-m", "Elsewhere")
    git(other, "push", "origin", "master")
    release.release("1.1.0", dry_run=False, root=repo, today=DAY)
    assert (repo / "new.txt").exists()
    assert git(repo, "log", "-2", "--format=%s").split("\n") == ["Release v1.1.0", "Elsewhere"]


def test_an_empty_changelog_section_stops_it(repo: Path) -> None:
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n")
    git(repo, "commit", "-am", "Empty notes")
    with pytest.raises(ReleaseError, match="is empty"):
        release.release("1.1.0", dry_run=False, root=repo, today=DAY)


def test_failing_checks_stop_it(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(root: Path) -> None:
        raise ReleaseError("The tests failed (see above).")

    monkeypatch.setattr(release, "run_checks", failing)
    with pytest.raises(ReleaseError, match="tests failed"):
        release.release("1.1.0", dry_run=False, root=repo, today=DAY)
    assert git(repo, "tag") == ""


def test_main_says_it_in_red_and_fails(capsys: pytest.CaptureFixture[str]) -> None:
    assert release.main(["v1.2.0"]) == 1
    assert 'without the "v"' in capsys.readouterr().err


# --- --fix: the same version again, on the fix ------------------------------------------------------------------


@pytest.fixture
def released(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """`repo` after `release.sh 1.1.0` and a fix committed and pushed; GitHub knows no release of v1.1.0 (drafts
    included)."""
    release.release("1.1.0", dry_run=False, root=repo, today=DAY)
    (repo / "fix.txt").write_text("the fix")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Fix the build")
    git(repo, "push", "origin", "master")
    monkeypatch.setattr(release, "github_releases", lambda repository, tag: ([], True))
    monkeypatch.setattr(release, "github_repository", lambda url: "someone/cube-net")
    return repo


def remote_tag_commit(root: Path, tag: str) -> str:
    return git(root, "ls-remote", "origin", f"refs/tags/{tag}^{{}}").split()[0]


def test_fix_moves_the_tag_to_the_fix(released: Path) -> None:
    old = git(released, "rev-list", "-n", "1", "v1.1.0")
    release.fix("1.1.0", dry_run=False, root=released)
    head = git(released, "rev-parse", "HEAD")
    assert head != old
    assert git(released, "rev-list", "-n", "1", "v1.1.0") == head
    assert remote_tag_commit(released, "v1.1.0") == head
    assert git(released, "cat-file", "-t", "v1.1.0") == "tag"  # still an annotated one
    assert git(released, "log", "-1", "--format=%s") == "Fix the build"  # no new commit
    assert git(released, "status", "--porcelain") == ""


def test_fix_dry_run_changes_nothing(released: Path) -> None:
    old = git(released, "rev-list", "-n", "1", "v1.1.0")
    release.fix("1.1.0", dry_run=True, root=released)
    assert git(released, "rev-list", "-n", "1", "v1.1.0") == old == remote_tag_commit(released, "v1.1.0")


def test_fix_needs_the_tag(released: Path) -> None:
    with pytest.raises(ReleaseError, match=re.escape("There's no tag v1.2.0")):
        release.fix("1.2.0", dry_run=False, root=released)


def test_fix_needs_the_tag_on_the_remote(released: Path) -> None:
    git(released, "push", "origin", ":refs/tags/v1.1.0")
    with pytest.raises(ReleaseError, match="not on origin"):
        release.fix("1.1.0", dry_run=False, root=released)


def test_fix_needs_a_tag_the_script_made(released: Path) -> None:
    git(released, "tag", "v1.0.5", "HEAD~1")  # a light tag by hand on the release commit
    git(released, "push", "origin", "v1.0.5")
    with pytest.raises(ReleaseError, match="isn't a tag the release script made"):
        release.fix("1.0.5", dry_run=False, root=released)


def test_fix_needs_something_new(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    release.release("1.1.0", dry_run=False, root=repo, today=DAY)
    monkeypatch.setattr(release, "github_releases", lambda repository, tag: ([], True))
    monkeypatch.setattr(release, "github_repository", lambda url: "someone/cube-net")
    with pytest.raises(ReleaseError, match=re.escape("nothing after v1.1.0")):
        release.fix("1.1.0", dry_run=False, root=repo)


def test_fix_needs_the_same_version_in_the_package(released: Path) -> None:
    init = released / "src/cube_net/__init__.py"
    init.write_text(init.read_text().replace('"1.1.0"', '"1.2.0"'))
    git(released, "commit", "-am", "Next version")
    git(released, "push", "origin", "master")
    with pytest.raises(ReleaseError, match=re.escape("says 1.2.0 now")):
        release.fix("1.1.0", dry_run=False, root=released)


def test_fix_needs_the_versions_notes(released: Path) -> None:
    (released / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n")
    git(released, "commit", "-am", "Notes gone")
    git(released, "push", "origin", "master")
    with pytest.raises(ReleaseError, match=re.escape('no section "## 1.1.0 (...)"')):
        release.fix("1.1.0", dry_run=False, root=released)


def test_fix_only_the_latest_release(released: Path) -> None:
    git(released, "tag", "v1.2.0")
    with pytest.raises(ReleaseError, match=re.escape("v1.2.0 came after v1.1.0")):
        release.fix("1.1.0", dry_run=False, root=released)


def test_never_a_published_release(released: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release, "github_releases", lambda repository, tag: ([{"draft": False}], False))
    with pytest.raises(ReleaseError, match="published on GitHub"):
        release.fix("1.1.0", dry_run=False, root=released)
    assert remote_tag_commit(released, "v1.1.0") != git(released, "rev-parse", "HEAD")


def test_a_draft_must_be_deleted_first(released: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release, "github_releases", lambda repository, tag: ([{"draft": True}], True))
    with pytest.raises(ReleaseError, match=re.escape("draft release of v1.1.0")):
        release.fix("1.1.0", dry_run=False, root=released)


def test_without_a_token_a_reminder_about_drafts(
    released: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(release, "github_releases", lambda repository, tag: ([], False))
    release.fix("1.1.0", dry_run=True, root=released)
    assert "Drafts can't be seen without $GITHUB_TOKEN" in capsys.readouterr().out


def test_fix_on_the_command_line(released: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(release, "fix", lambda text, dry_run: calls.append((text, dry_run)))
    assert release.main(["1.1.0", "--fix", "--dry-run"]) == 0
    assert calls == [("1.1.0", True)]


class TestGitHubReleases:
    """What GitHub is asked, and how its answers are read (its API simulated)."""

    def answer(self, monkeypatch: pytest.MonkeyPatch, replies: dict[str, object]) -> list[str]:
        asked: list[str] = []

        def github(path: str, headers: dict[str, str]) -> object:
            asked.append(path + (" with a token" if "Authorization" in headers else ""))
            return replies.get(path)

        monkeypatch.setattr(release, "_github", github)
        return asked

    def test_without_a_token_the_published_release_of_the_tag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        asked = self.answer(monkeypatch, {"/repos/o/r/releases/tags/v1.1.0": {"tag_name": "v1.1.0", "draft": False}})
        assert release.github_releases("o/r", "v1.1.0") == ([{"tag_name": "v1.1.0", "draft": False}], False)
        assert release.github_releases("o/r", "v2.0.0") == ([], False)  # not found
        assert asked == ["/repos/o/r/releases/tags/v1.1.0", "/repos/o/r/releases/tags/v2.0.0"]

    def test_with_a_token_drafts_too(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "secret")
        draft = {"tag_name": "v1.1.0", "draft": True}
        asked = self.answer(monkeypatch, {"/repos/o/r/releases?per_page=100&page=1": [draft, {"tag_name": "v1.0.0"}]})
        assert release.github_releases("o/r", "v1.1.0") == ([draft], True)
        assert asked == ["/repos/o/r/releases?per_page=100&page=1 with a token"]

    def test_the_repository_from_the_remote(self) -> None:
        assert release.github_repository("git@github.com:Avorthoren/cube-net.git") == "Avorthoren/cube-net"
        assert release.github_repository("https://example.com/a/b") is None
