import base64
import subprocess
import sys
from pathlib import Path

import pytest

from cube_net.core.project import load_project, new_project, project_from_bytes, project_to_bytes
from cube_net.core.project_settings import ProjectSettings
from cube_net.ui.session.snapshots import extract_snapshots, main, snapshot_text, snapshots_in


def log_with(tmp_path: Path, *lines: str) -> Path:
    log = tmp_path / "session-1.log"
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log


def test_snapshot_text_is_one_word() -> None:
    assert len(snapshot_text(new_project()).split()) == 1


def test_it_gives_back_the_same_bytes(tmp_path: Path) -> None:
    project = new_project()
    log = log_with(tmp_path, f"0.006 state snapshot {snapshot_text(project)}")
    assert snapshots_in(log) == [project_to_bytes(project)]


def test_only_snapshot_lines_count(tmp_path: Path) -> None:
    text = base64.b64encode(b"x").decode()
    log = log_with(
        tmp_path,
        "# Cube Net session log",
        "# state snapshot abc",
        "0.001 state net default",
        f"0.002 state snapshot {text}",
        "0.003 press L 11.000,12.000",
        "0.004 note state snapshot abc",
        f"0.005 state snapshot {text}",
    )
    assert snapshots_in(log) == [b"x", b"x"]


def test_a_line_cut_off_by_a_crash_does_not_count(tmp_path: Path) -> None:
    good = snapshot_text(new_project())
    log = log_with(tmp_path, f"0.001 state snapshot {good}", f"0.002 state snapshot {good[:101]}")
    assert snapshots_in(log) == [project_to_bytes(new_project())]


def test_none_in_an_old_log(tmp_path: Path) -> None:
    assert snapshots_in(log_with(tmp_path, "0.001 state net default")) == []


def test_extracted_files_open_as_projects(tmp_path: Path) -> None:
    log = log_with(
        tmp_path,
        f"0.001 state snapshot {snapshot_text(new_project())}",
        f"0.002 state snapshot {snapshot_text(new_project())}",
    )
    paths = extract_snapshots(log)
    assert [p.name for p in paths] == ["session-1-1.cubenet", "session-1-2.cubenet"]
    assert load_project(paths[1]).settings == ProjectSettings()


def test_project_bytes_round_trip() -> None:
    assert project_from_bytes(project_to_bytes(new_project())).state.approved_cuts == 0


class TestCommand:
    def test_prints_the_files(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        log = log_with(tmp_path, f"0.001 state snapshot {snapshot_text(new_project())}")
        assert main([str(log)]) == 0
        assert capsys.readouterr().out.strip() == str(tmp_path / "session-1-1.cubenet")

    def test_nothing_found(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main([str(log_with(tmp_path, "0.001 state net default"))]) == 1
        assert "no snapshots" in capsys.readouterr().err

    def test_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main([]) == 2
        assert "usage" in capsys.readouterr().err

    def test_it_runs_on_its_own_without_qt(self, tmp_path: Path) -> None:
        log = log_with(tmp_path, f"0.001 state snapshot {snapshot_text(new_project())}")
        code = (
            "import sys, runpy\n"
            "sys.argv = ['snapshots', sys.argv[1]]\n"
            "try:\n"
            "    runpy.run_module('cube_net.ui.session.snapshots', run_name='__main__')\n"
            "except SystemExit as e:\n"
            "    assert e.code == 0\n"
            "assert not any(name.startswith('PyQt') for name in sys.modules), 'Qt got imported'\n"
        )
        done = subprocess.run([sys.executable, "-c", code, str(log)], capture_output=True, text=True)
        assert done.returncode == 0, done.stderr
        assert (tmp_path / "session-1-1.cubenet").exists()
