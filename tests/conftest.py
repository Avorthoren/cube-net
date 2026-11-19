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


# A template with a slit and faces in two pieces: the torus as it was built in until 2026-11-20 (its purple and green
# faces each in two pieces, glued into rings; the loop going up from S2 to M2 and back down to K2). Tests that need
# those very things use it, not the built-in Cube with a hole, which the author may draw anew at any time.
SLIT_TORUS = Path(__file__).parent / "fixtures" / "torus_with_slit.nettemplate"


@pytest.fixture
def slit_torus() -> object:
    """The template document of `SLIT_TORUS`."""
    from cube_net.core.project import TemplateDocument, load_document

    document = load_document(SLIT_TORUS)
    assert isinstance(document, TemplateDocument)
    return document
