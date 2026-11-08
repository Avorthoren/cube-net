from pathlib import Path

import pytest
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication

from cube_net.ui.session.start import (
    STARTED_AT_LAUNCH,
    STOPPED_BY_USER,
    open_session_log_folder,
    start_session_recording,
    stop_session_recording,
)


def lines(path: Path) -> list[str]:
    return path.read_text().splitlines()


def test_creates_log_with_header_and_records(tmp_path: Path, qapp: QApplication) -> None:
    recorder = start_session_recording(qapp, STARTED_AT_LAUNCH, tmp_path)
    try:
        assert list(tmp_path.glob("session-*.log")) == [recorder.log.path]
        header = lines(recorder.log.path)
        assert header[0].startswith("# Cube Net ")
        assert header[1].startswith("# python ")
        assert header[-1] == "# recording started: at app launch"
        recorder.note("hello")
        assert lines(recorder.log.path)[-1].endswith(" hello")
    finally:
        stop_session_recording(qapp, recorder, STOPPED_BY_USER)


def test_stop_ends_the_file(tmp_path: Path, qapp: QApplication) -> None:
    recorder = start_session_recording(qapp, STARTED_AT_LAUNCH, tmp_path)
    stop_session_recording(qapp, recorder, STOPPED_BY_USER)
    assert lines(recorder.log.path)[-1].endswith(" stop turned off by the user")
    assert recorder.log.closed
    recorder.note("after stop")  # ignored
    assert "after stop" not in recorder.log.path.read_text()


def test_default_directory_comes_from_session_log_directory(session_logs_in_tmp: Path, qapp: QApplication) -> None:
    recorder = start_session_recording(qapp, STARTED_AT_LAUNCH)
    try:
        assert recorder.log.path.parent == session_logs_in_tmp
    finally:
        stop_session_recording(qapp, recorder, STOPPED_BY_USER)


def test_open_folder_creates_it_and_asks_the_system(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[QUrl] = []

    def fake_open(url: QUrl) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr("cube_net.ui.session.start.QDesktopServices.openUrl", fake_open)
    folder = tmp_path / "logs"
    assert open_session_log_folder(folder)
    assert folder.is_dir()
    assert opened == [QUrl.fromLocalFile(str(folder))]


def test_open_folder_uses_the_default_location(session_logs_in_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cube_net.ui.session.start.QDesktopServices.openUrl", lambda _url: False)
    assert not open_session_log_folder()
    assert session_logs_in_tmp.is_dir()
