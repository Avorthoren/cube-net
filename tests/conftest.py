# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from pathlib import Path

import pytest

# Run Qt headless in tests (no window appears), unless explicitly overridden.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def no_save_changes_question(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows with unsaved changes get closed when a test ends, and nobody would answer a real question then."""
    from cube_net.ui.save_changes_dialog import SaveChoice

    monkeypatch.setattr("cube_net.ui.main_window.ask_save_changes", lambda *_: SaveChoice.DISCARD)


@pytest.fixture(autouse=True)
def session_logs_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Session recordings made by tests go to a temporary folder, never to the user's app data folder."""
    directory = tmp_path / "sessions"
    monkeypatch.setattr("cube_net.ui.session.start.session_log_directory", lambda: directory)
    return directory
