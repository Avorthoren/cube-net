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


def test_numbers_hatches_and_the_counter(cross_template: Template) -> None:
    from cube_net.core.geometry import Rigid90

    turned = Rigid90(1, Vec(3, -2))
    template = cross_template.with_face_color(2, "#123456")
    template = template.with_hatches([turned if i == 2 else f.hatch for i, f in enumerate(template.faces)])
    loaded = round_trip(TemplateDocument(TemplateSnapshot(template), History())).state.template
    assert loaded == template
    assert loaded.faces[2].number == template.next_number - 1 and loaded.faces[2].hatch == turned


def test_a_template_saved_before_the_counter(cross_template: Template) -> None:
    data = encode_template(TemplateDocument(TemplateSnapshot(cross_template), History()))
    for face in data["templates"][0]["faces"]:
        face.pop("number", None)
        face.pop("hatch", None)
    del data["templates"][0]["next_number"]
    loaded = decode_template(data).state.template
    assert loaded.next_number == 1 and all(f.number is None and f.hatch.is_identity() for f in loaded.faces)


def test_fold_vertices(cross_template: Template) -> None:
    from fractions import Fraction as F

    from cube_net.core.template import Label

    c1, d1 = (next(v.id for v in cross_template.vertices if str(v.label) == name) for name in ("C1", "D1"))
    template = cross_template.without_fold(next(f for f in cross_template.folds if f.joins(c1, d1)))
    template = template.with_fold_line(c1, [Vec(F(23, 2), F(53, 4))], d1)
    template = template.with_label(template.fold_vertices[0].id, Label("M", 1))
    data = encode_template(TemplateDocument(TemplateSnapshot(template), History()))
    assert len(data["templates"][0]["fold_vertices"]) == 1
    assert round_trip(TemplateDocument(TemplateSnapshot(template), History())).state.template == template
    assert "fold_vertices" not in encode_template(document_of(edited(cross_template)))["templates"][0]
    data = json.loads(json.dumps(data))
    data["templates"][0]["folds"] = [f for f in data["templates"][0]["folds"] if template.fold_vertices[0].id not in f][
        :-1
    ]
    with pytest.raises(ProjectFileError, match="damaged"):
        decode_template(data)


def test_holes(cross_template: Template) -> None:
    from fractions import Fraction as F

    from cube_net.core.template.holes import closed_hole, with_hole_point

    template = cross_template
    for x, y in [(F(45, 4), F(49, 4)), (F(45, 4), F(25, 2)), (F(23, 2), F(25, 2))]:
        template = with_hole_point(template, Vec(x, y))
    closed = closed_hole(template)
    being_drawn = with_hole_point(closed, Vec(F(45, 4), F(53, 4)))
    for t in (template, closed, being_drawn):  # one being drawn, closed, and another being drawn after it
        assert round_trip(TemplateDocument(TemplateSnapshot(t), History())).state.template == t
    data = encode_template(TemplateDocument(TemplateSnapshot(closed), History()))
    assert len(data["templates"][0]["holes"]) == 1 and any("holes" in f for f in data["templates"][0]["faces"])
    data = json.loads(json.dumps(data))
    data["templates"][0]["holes"][0]["closed"] = "yes"
    with pytest.raises(ProjectFileError, match="damaged"):
        decode_template(data)


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
        lambda d: d["templates"][0]["faces"][0].__setitem__("number", 999),  # not below the counter
        lambda d: d["templates"][0]["faces"][0].__setitem__("hatch", {"k": 1}),
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
