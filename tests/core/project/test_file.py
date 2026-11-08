import gzip
import json
import stat
from pathlib import Path

import pytest
from project_checks import after_a_cut, approving, editor_of, named_labels, project_of, state_contents

from cube_net.core.project import (
    PROJECT_SUFFIX,
    ProjectFileError,
    encode_project,
    load_project,
    new_project,
    save_project,
)


def path_in(tmp_path: Path) -> Path:
    return tmp_path / f"cube{PROJECT_SUFFIX}"


def test_save_and_load(tmp_path: Path) -> None:
    project = project_of(after_a_cut())
    path = path_in(tmp_path)
    save_project(project, path)
    loaded = load_project(path)
    assert state_contents(loaded.state) == state_contents(project.state)
    assert editor_of(loaded).undo()


def test_it_is_gzipped_json(tmp_path: Path) -> None:
    project = project_of(approving(), named_labels(approving()))
    path = path_in(tmp_path)
    save_project(project, path)
    assert json.loads(gzip.decompress(path.read_bytes())) == json.loads(json.dumps(encode_project(project)))


def test_saving_again_replaces_it(tmp_path: Path) -> None:
    path = path_in(tmp_path)
    save_project(project_of(approving()), path)
    save_project(project_of(after_a_cut()), path)
    assert load_project(path).state.approved_cuts == 1
    assert [p.name for p in tmp_path.iterdir()] == [path.name]


def test_the_same_project_gives_the_same_file(tmp_path: Path) -> None:
    project = project_of(approving())
    a, b = tmp_path / "a.cubenet", tmp_path / "b.cubenet"
    save_project(project, a)
    save_project(project, b)
    assert a.read_bytes() == b.read_bytes()


def test_a_failure_leaves_the_old_file_as_it_was(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = path_in(tmp_path)
    save_project(project_of(approving()), path)
    before = path.read_bytes()

    def fail(*_: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(ProjectFileError, match="No space left"):
        save_project(project_of(after_a_cut()), path)
    assert path.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == [path.name]


def test_no_such_folder(tmp_path: Path) -> None:
    with pytest.raises(ProjectFileError, match="Can't save"):
        save_project(project_of(approving()), tmp_path / "nowhere" / "cube.cubenet")


def test_a_new_file_is_not_private(tmp_path: Path) -> None:
    path = path_in(tmp_path)
    save_project(project_of(approving()), path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


def test_saving_again_keeps_its_permissions(tmp_path: Path) -> None:
    path = path_in(tmp_path)
    save_project(project_of(approving()), path)
    path.chmod(0o600)
    save_project(project_of(approving()), path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_no_such_file(tmp_path: Path) -> None:
    with pytest.raises(ProjectFileError, match="Can't open"):
        load_project(path_in(tmp_path))


def test_not_a_project_file(tmp_path: Path) -> None:
    path = path_in(tmp_path)
    path.write_text("Hello!")
    with pytest.raises(ProjectFileError, match="isn't a Cube Net project"):
        load_project(path)


def test_a_cut_off_file(tmp_path: Path) -> None:
    path = path_in(tmp_path)
    save_project(project_of(approving()), path)
    path.write_bytes(path.read_bytes()[:200])
    with pytest.raises(ProjectFileError, match="damaged"):
        load_project(path)


def test_gzipped_text_that_is_not_json(tmp_path: Path) -> None:
    path = path_in(tmp_path)
    path.write_bytes(gzip.compress(b"not json"))
    with pytest.raises(ProjectFileError, match="damaged"):
        load_project(path)


def test_gzipped_bytes_that_are_not_text(tmp_path: Path) -> None:
    path = path_in(tmp_path)
    path.write_bytes(gzip.compress(b"\xff\xfe\xfa"))
    with pytest.raises(ProjectFileError, match="damaged"):
        load_project(path)


def test_the_message_names_the_file(tmp_path: Path) -> None:
    path = path_in(tmp_path)
    path.write_bytes(gzip.compress(b'{"format_version": 999}'))
    with pytest.raises(ProjectFileError) as caught:
        load_project(path)
    assert str(path) in str(caught.value)
    assert "newer version" in str(caught.value)


def test_a_new_project(tmp_path: Path) -> None:
    project = new_project()
    assert project.state.points is None and project.state.approved_cuts == 0
    assert not project.history.can_undo and not project.history.can_redo
    assert project.state.net.bounding_box().height == 4
    path = path_in(tmp_path)
    save_project(project, path)
    assert state_contents(load_project(path).state) == state_contents(project.state)
