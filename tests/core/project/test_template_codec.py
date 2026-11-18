# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest

from cube_net.core.geometry import Vec
from cube_net.core.history import History
from cube_net.core.origin import Origin
from cube_net.core.project import ProjectFileError, TemplateDocument, decode_template, encode_template
from cube_net.core.style import Style
from cube_net.core.template import Template, TemplateEditor, TemplateSnapshot, ValidationStatus


def document_of(editor: TemplateEditor) -> TemplateDocument:
    return TemplateDocument(editor.snapshot(), editor.history)


def round_trip(document: TemplateDocument) -> TemplateDocument:
    """Through the real JSON text."""
    return decode_template(json.loads(json.dumps(encode_template(document))))


def edited(cross_template: Template) -> TemplateEditor:
    """The cross in the editor, with a few actions done and one undone."""
    editor = TemplateEditor(cross_template)
    editor.set_face_color(0, "#123456")
    editor.move_origin(Origin().moved(Vec(11, 10), Vec(0, 0), "A3"))
    editor.delete_fold(editor.template.folds[0])
    editor.undo()
    return editor


def test_the_template_and_its_origin(cross_template: Template) -> None:
    editor = edited(cross_template)
    loaded = round_trip(document_of(editor))
    assert loaded.state == editor.snapshot()


def test_the_history_goes_on(cross_template: Template) -> None:
    loaded = round_trip(document_of(edited(cross_template)))
    again = TemplateEditor()
    again.load(loaded.state, loaded.history)
    assert again.history.done_count == 2 and again.history.undone_count == 1
    assert again.redo() and len(again.template.folds) == 4
    assert again.undo() and again.undo() and again.undo()
    assert again.template.faces[0].color != "#123456" and again.origin == Origin()


def test_the_style(cross_template: Template) -> None:
    style = Style(3, 4, 7, 2.5, 5.0, "#ABCDEF", 0.5)
    document = TemplateDocument(TemplateSnapshot(cross_template), History(), style)
    assert round_trip(document).style == style


@pytest.mark.parametrize("status", list(ValidationStatus))
def test_the_validation_status(cross_template: Template, status: ValidationStatus) -> None:
    document = TemplateDocument(TemplateSnapshot(cross_template), History(), validation=status)
    assert round_trip(document).validation is status


def test_a_template_saved_without_a_status_is_undefined(cross_template: Template) -> None:
    data = encode_template(
        TemplateDocument(TemplateSnapshot(cross_template), History(), validation=ValidationStatus.VALID)
    )
    del data["validation"]
    assert decode_template(data).validation is ValidationStatus.UNDEFINED


def test_a_template_saved_without_a_style_has_none(cross_template: Template) -> None:
    data = json.loads(json.dumps(encode_template(document_of(edited(cross_template)))))
    assert data.pop("style") is None
    assert decode_template(data).style is None


def test_faces_without_a_colour(cross_template: Template) -> None:
    template = replace(cross_template, faces=tuple(replace(face, color=None) for face in cross_template.faces))
    document = TemplateDocument(TemplateSnapshot(template), History())
    assert encode_template(document)["templates"][0]["faces"][0]["color"] is None
    assert round_trip(document).state.template == template


def test_a_template_while_drawing() -> None:
    editor = TemplateEditor()
    for p in (Vec(10, 10), Vec(12, 10)):
        editor.add_point(p)
    loaded = round_trip(document_of(editor))
    assert loaded.state.template == editor.template and not loaded.state.template.closed


def test_templates_are_stored_once(cross_template: Template) -> None:
    editor = TemplateEditor(cross_template)
    editor.move_origin(Origin().moved(Vec(11, 10), Vec(0, 0), None))  # the same template before and after
    data = encode_template(document_of(editor))
    assert (data["kind"], data["format_version"], len(data["templates"])) == ("template", 1, 1)


def test_it_is_plain_json(cross_template: Template) -> None:
    json.dumps(encode_template(document_of(edited(cross_template))))


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["templates"][0]["vertices"][0].__setitem__("id", 1),  # two vertices with one id
        lambda d: d["templates"][0].__setitem__("next_id", 0),
        lambda d: d["templates"][0]["vertices"][0].__setitem__("label", ["a", 1]),
        lambda d: d["templates"][0]["vertices"][1].__setitem__("label", d["templates"][0]["vertices"][0]["label"]),
        lambda d: d["templates"][0]["faces"].pop(),
        lambda d: d["templates"][0]["faces"][0].__setitem__("color", "red"),
        lambda d: d["templates"][0]["folds"].append([0, 99]),
        lambda d: d["templates"][0].__setitem__("closed", "yes"),
        lambda d: d["states"][0].__setitem__("template", 5),
        lambda d: d["history"]["done"][0].__setitem__("kind", "jump"),
        lambda d: d.pop("history"),
        lambda d: d.__setitem__("style", {"edge_width": 4.0}),
        lambda d: d.__setitem__("style", "bold"),
        lambda d: d.__setitem__("validation", "maybe"),
    ],
)
def test_damaged(cross_template: Template, change: Callable[[dict[str, Any]], None]) -> None:
    data = json.loads(json.dumps(encode_template(document_of(edited(cross_template)))))
    change(data)
    with pytest.raises(ProjectFileError, match="damaged"):
        decode_template(data)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.__setitem__("kind", "project"), "isn't a Cube Net template"),
        (lambda d: d.__setitem__("format_version", 2), "newer version"),
        (lambda d: d.__setitem__("format_version", "1"), "unknown format version"),
    ],
)
def test_not_this_kind_or_version(
    cross_template: Template, change: Callable[[dict[str, Any]], None], message: str
) -> None:
    data = encode_template(document_of(edited(cross_template)))
    change(data)
    with pytest.raises(ProjectFileError, match=message):
        decode_template(data)


def test_a_snapshot_is_what_the_editor_has(cross_template: Template) -> None:
    assert TemplateEditor(cross_template).snapshot() == TemplateSnapshot(cross_template)
