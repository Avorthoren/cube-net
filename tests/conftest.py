import os
from pathlib import Path

import pytest

# Run Qt headless in tests (no window appears), unless explicitly overridden.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def session_logs_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Session recordings made by tests go to a temporary folder, never to the user's app data folder."""
    directory = tmp_path / "sessions"
    monkeypatch.setattr("cube_net.ui.session.start.session_log_directory", lambda: directory)
    return directory
