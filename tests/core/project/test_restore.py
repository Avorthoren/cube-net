# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Restoring damaged files from their history (`restore.py`)."""

import json
from typing import Any

import pytest
from project_checks import after_a_cut, project_of

from cube_net.core.history import History
from cube_net.core.project import (
    Project,
    ProjectFileError,
    TemplateDocument,
    decode_project,
    decode_template,
    encode_project,
    encode_template,
    restorable,
    restore_document,
    save_project,
)
from cube_net.core.project.restore import can_restore, restore
from cube_net.core.template import Template, TemplateEditor, TemplateSnapshot


def edited_template(cross_template: Template) -> TemplateEditor:
    editor = TemplateEditor(cross_template)
    for face in range(3):
        editor.set_face_color(face, f"#00000{face}")
    return editor


def template_data(editor: TemplateEditor) -> dict[str, Any]:
    data = encode_template(TemplateDocument(editor.snapshot(), editor.history))
    return json.loads(json.dumps(data))


def broken_last_template(data: dict[str, Any]) -> None:
    """The template the file was saved in loses a face: a side is then on no face."""
    data["templates"][data["states"][data["state"]]["template"]]["faces"].pop()


def test_a_template_from_one_action_ago(cross_template: Template) -> None:
    editor = edited_template(cross_template)
    data = template_data(editor)
    broken_last_template(data)
    with pytest.raises(ProjectFileError, match="damaged"):
        decode_template(data)
    restored = restore(data)
    assert restored is not None
    document, actions = restored
    assert actions == 1 and isinstance(document, TemplateDocument)
    editor.undo()
    assert document.state == editor.snapshot()
    assert document.history.done_count == 2 and document.history.undone_count == 0


def test_further_back_when_the_states_before_are_broken_too(cross_template: Template) -> None:
    editor = edited_template(cross_template)
    data = template_data(editor)
    done = data["history"]["done"]
    for entry in done[-2:]:  # the last two actions' results
        data["templates"][data["states"][entry["after"]]["template"]]["faces"][0]["color"] = "red"
    document, actions = restore(data) or (None, 0)
    assert actions == 2 and isinstance(document, TemplateDocument) and document.history.done_count == 1


def test_nothing_to_undo_or_nothing_that_opens(cross_template: Template) -> None:
    fresh = json.loads(json.dumps(encode_template(TemplateDocument(TemplateSnapshot(cross_template), History()))))
    broken_last_template(fresh)
    assert not can_restore(fresh) and restore(fresh) is None
    data = template_data(edited_template(cross_template))
    for template in data["templates"]:
        template["faces"].pop()
    assert can_restore(data) and restore(data) is None
    assert not can_restore("text") and not can_restore({"history": None})


def test_a_project_from_one_action_ago() -> None:
    editor = after_a_cut()
    data = json.loads(json.dumps(encode_project(project_of(editor))))
    data["nets"][data["states"][data["state"]]["net"]]["edges"].pop()
    with pytest.raises(ProjectFileError, match="damaged"):
        decode_project(data)
    restored = restore(data)
    assert restored is not None
    document, actions = restored
    assert isinstance(document, Project) and actions >= 1
    assert document.history.undone_count == 0 and document.history.done_count == editor.history.done_count - actions


def test_from_a_file(tmp_path: Any) -> None:
    path = tmp_path / "cut.cubenet"
    save_project(project_of(after_a_cut()), path)
    assert restorable(path)
    assert restore_document(tmp_path / "missing.cubenet") is None and not restorable(tmp_path / "missing.cubenet")
