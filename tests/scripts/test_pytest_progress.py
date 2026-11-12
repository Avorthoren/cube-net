# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""The progress of the tests, as the release script shows it: real pytest runs of throwaway tests."""

from pathlib import Path

import pytest

from scripts import release


def throwaway_tests(tmp_path: Path, *bodies: str) -> str:
    file = tmp_path / "test_throwaway.py"
    file.write_text("\n\n".join(f"def test_{i}():\n    {body}" for i, body in enumerate(bodies)) + "\n")
    return str(file)


def test_progress_test_by_test_then_how_many_passed(tmp_path: Path) -> None:
    seen: list[str] = []
    release.run_tests(release.ROOT, [throwaway_tests(tmp_path, "pass", "pass", "pass")], show=seen.append)
    assert seen == [
        "Running the tests...",
        "Running the tests... 0 of 3 (0%)",
        "Running the tests... 1 of 3 (33%)",
        "Running the tests... 2 of 3 (66%)",
        "Running the tests... 3 of 3 (100%)",
        "Running the tests... 3 passed",
    ]


def test_a_failure_shows_pytests_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    seen: list[str] = []
    with pytest.raises(release.ReleaseError, match="The tests failed"):
        release.run_tests(release.ROOT, [throwaway_tests(tmp_path, "pass", "assert 1 == 2")], show=seen.append)
    assert seen[-1] == "Running the tests... 2 of 2 (100%)"  # no "passed"
    output = capsys.readouterr().out
    assert "1 failed" in output and "assert 1 == 2" in output


def test_without_the_variable_the_plugin_does_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess
    import sys

    monkeypatch.delenv(release.TEST_PROGRESS_VARIABLE, raising=False)
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "scripts.pytest_progress", throwaway_tests(tmp_path, "pass")],
        cwd=release.ROOT,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(release.ROOT), "PATH": "/usr/bin:/bin"},
    )
    assert done.returncode == 0 and "1 passed" in done.stdout
