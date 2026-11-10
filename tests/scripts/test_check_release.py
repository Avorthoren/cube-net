# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The workflow's check of a pushed tag, in throwaway repositories (a bare one as the remote)."""

import re
import subprocess
from pathlib import Path

import pytest
from scripts.release import ReleaseError

from scripts import check_release

CHANGELOG = """# Changelog

## Unreleased

## 1.1.0 (2026-11-20)

- Ctrl+click deletes a point.

## 1.0.0 (2026-11-01)

- The first release.
"""


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def commit(root: Path, version: str, changelog: str = CHANGELOG, message: str = "Release") -> None:
    package = root / "src" / "cube_net"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text(f'__version__ = "{version}"\n\n__version_date__ = "2026-11-20"\n')
    (root / "CHANGELOG.md").write_text(changelog)
    git(root, "add", ".")
    git(root, "commit", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A clone of a bare origin with v1.0.0 released and 1.1.0 committed on master and pushed (not tagged yet)."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "master", str(origin))
    root = tmp_path / "work"
    git(tmp_path, "clone", str(origin), str(root))
    git(root, "checkout", "-b", "master")
    git(root, "config", "user.name", "Tester")
    git(root, "config", "user.email", "tester@example.com")
    commit(root, "1.0.0", "# Changelog\n\n## Unreleased\n\n## 1.0.0 (2026-11-01)\n\n- The first release.\n")
    git(root, "tag", "-a", "v1.0.0", "-m", "Cube Net 1.0.0")
    commit(root, "1.1.0")
    git(root, "push", "origin", "master", "v1.0.0")
    git(root, "fetch", "origin")
    return root


def test_a_good_tag(repo: Path) -> None:
    git(repo, "tag", "-a", "v1.1.0", "-m", "Cube Net 1.1.0")
    version, notes = check_release.check("v1.1.0", repo)
    assert version.text == "1.1.0" and version.pre is None
    assert notes == "- Ctrl+click deletes a point."


def test_a_pre_release(repo: Path) -> None:
    commit(repo, "1.2.0-beta", CHANGELOG.replace("## 1.1.0 (", "## 1.2.0-beta ("))
    git(repo, "push", "origin", "master")
    git(repo, "fetch", "origin")
    git(repo, "tag", "v1.2.0-beta")
    version, _ = check_release.check("v1.2.0-beta", repo)
    assert version.pre == "beta"


@pytest.mark.parametrize("tag", ["1.1.0", "vX", "v1.1"])
def test_not_a_release_tag(repo: Path, tag: str) -> None:
    git(repo, "tag", tag)
    with pytest.raises(ReleaseError):
        check_release.check(tag, repo)


def test_a_missing_tag(repo: Path) -> None:
    with pytest.raises(ReleaseError, match=re.escape("no tag v9.9.9")):
        check_release.check("v9.9.9", repo)


def test_only_on_master(repo: Path) -> None:
    git(repo, "checkout", "-b", "feature")
    commit(repo, "1.2.0", CHANGELOG.replace("## 1.1.0 (", "## 1.2.0 ("), "Not on master")
    git(repo, "tag", "v1.2.0")
    with pytest.raises(ReleaseError, match="isn't on master"):
        check_release.check("v1.2.0", repo)


def test_the_package_must_say_the_same_version(repo: Path) -> None:
    git(repo, "tag", "v1.1.1")
    with pytest.raises(ReleaseError, match=re.escape("the package says 1.1.0")):
        check_release.check("v1.1.1", repo)


def test_not_lower_than_another_release(repo: Path) -> None:
    git(repo, "tag", "v2.0.0", "v1.0.0")  # a higher release elsewhere
    git(repo, "tag", "v1.1.0")
    with pytest.raises(ReleaseError, match=re.escape("lower than the latest release, 2.0.0")):
        check_release.check("v1.1.0", repo)


def test_the_changelog_needs_the_versions_notes(repo: Path) -> None:
    commit(repo, "1.1.0", "# Changelog\n\n## Unreleased\n\n- Forgot to release them.\n", "No section")
    git(repo, "push", "origin", "master")
    git(repo, "fetch", "origin")
    git(repo, "tag", "v1.1.0")
    with pytest.raises(ReleaseError, match=re.escape('no section "## 1.1.0 (...)"')):
        check_release.check("v1.1.0", repo)


def test_main_writes_the_notes_and_tells_the_workflow(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(repo, "tag", "v1.1.0")
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    notes = tmp_path / "notes.md"
    assert check_release.main(["v1.1.0", str(notes)], root=repo) == 0
    assert notes.read_text() == "- Ctrl+click deletes a point.\n"
    assert output.read_text() == "version=1.1.0\nprerelease=false\n"


def test_main_says_what_failed(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check_release.main(["v9.9.9", str(tmp_path / "notes.md")], root=repo) == 1
    assert "no tag v9.9.9" in capsys.readouterr().err
