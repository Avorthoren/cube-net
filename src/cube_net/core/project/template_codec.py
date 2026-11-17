# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""A template file's contents as plain JSON data, and back: the template, its origin, and its history (so that undo
and redo go on after reopening). Like a project's (docs/plan.md, section 5.3): exact numbers as strings, and every
template stored once, in a table, the states referring to it by index.

`{"format_version": 1, "kind": "template", "style": {...}, "templates": [...], "states": [...], "state": i,
"history": {...}}` (no "style": saved before the style belonged to documents)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cube_net.core.body.body import COLOR_PATTERN
from cube_net.core.history import ActionKind, History, HistoryEntry
from cube_net.core.project.codec import read_origin, read_style, read_vec, write_origin, write_style, write_vec
from cube_net.core.project.project import ProjectFileError
from cube_net.core.style import Style
from cube_net.core.template.template import Fold, Label, LoopVertex, Template, TemplateFace
from cube_net.core.template.template_editor import TemplateSnapshot

# Raise it whenever the format changes (and keep reading the older ones, if there's anything worth keeping).
TEMPLATE_FORMAT_VERSION = 1

# What a template file holds (a project is the other kind).
TEMPLATE_KIND = "template"


@dataclass(frozen=True, slots=True)
class TemplateDocument:
    """What a template file keeps: the template being made, its history, and its style."""

    state: TemplateSnapshot
    history: History[TemplateSnapshot]

    # Settings -> Style while the template is made; a project made from it starts with it. None: not chosen yet (a new
    # template, or one saved before the style belonged to documents); the application fills it in.
    style: Style | None = None


def encode_template(document: TemplateDocument) -> dict[str, Any]:
    templates: list[Template] = []
    templates_data: list[dict[str, Any]] = []
    states: dict[TemplateSnapshot, int] = {}
    states_data: list[dict[str, Any]] = []

    def template_index(template: Template) -> int:
        for i, known in enumerate(templates):
            if known is template:
                return i
        templates.append(template)
        templates_data.append(_write_template(template))
        return len(templates) - 1

    def state_index(state: TemplateSnapshot) -> int:
        if state not in states:
            states[state] = len(states_data)
            states_data.append({"template": template_index(state.template), "origin": write_origin(state.origin)})
        return states[state]

    def entry(e: HistoryEntry[TemplateSnapshot]) -> dict[str, Any]:
        return {"kind": e.kind.value, "before": state_index(e.before), "after": state_index(e.after)}

    state = state_index(document.state)
    history = {
        "done": [entry(e) for e in document.history.done_entries()],
        "undone": [entry(e) for e in document.history.undone_entries()],
    }
    return {
        "format_version": TEMPLATE_FORMAT_VERSION,
        "kind": TEMPLATE_KIND,
        "style": write_style(document.style),
        "templates": templates_data,
        "states": states_data,
        "state": state,
        "history": history,
    }


def decode_template(data: object) -> TemplateDocument:
    """The template from `encode_template`'s data. Raises `ProjectFileError` if there's anything wrong with it."""
    if not isinstance(data, dict) or data.get("kind") != TEMPLATE_KIND:
        raise ProjectFileError("It isn't a Cube Net template.")
    version = data.get("format_version")
    if version != TEMPLATE_FORMAT_VERSION:
        if isinstance(version, int) and version > TEMPLATE_FORMAT_VERSION:
            raise ProjectFileError("It was saved by a newer version of the application.")
        raise ProjectFileError("It has an unknown format version: {version}.", version=repr(version))
    try:
        templates = [_read_template(t) for t in data["templates"]]
        states = [TemplateSnapshot(templates[s["template"]], read_origin(s["origin"])) for s in data["states"]]

        def entry(e: dict[str, Any]) -> HistoryEntry[TemplateSnapshot]:
            return HistoryEntry(ActionKind(e["kind"]), states[e["before"]], states[e["after"]])

        history: History[TemplateSnapshot] = History.restored(
            [entry(e) for e in data["history"]["done"]], [entry(e) for e in data["history"]["undone"]]
        )
        return TemplateDocument(states[data["state"]], history, read_style(data.get("style")))
    except (KeyError, IndexError, TypeError, ValueError, AttributeError, ZeroDivisionError) as e:
        raise ProjectFileError("It is damaged ({detail}).", detail=f"{type(e).__name__}: {e}") from e


def _write_template(template: Template) -> dict[str, Any]:
    return {
        "vertices": [
            {
                "id": v.id,
                "at": write_vec(v.position),
                "label": None if v.label is None else [v.label.name, v.label.index],
            }
            for v in template.vertices
        ],
        "closed": template.closed,
        "folds": [[f.start, f.end] for f in template.folds],
        "faces": [{"corners": list(f.corners), "color": f.color} for f in template.faces],
        "next_id": template.next_id,
    }


def _read_template(data: dict[str, Any]) -> Template:
    vertices = tuple(
        LoopVertex(_int(v["id"]), read_vec(v["at"]), None if v["label"] is None else Label(*v["label"]))
        for v in data["vertices"]
    )
    closed = data["closed"]
    if not isinstance(closed, bool):
        raise TypeError(f"expected true or false, got {closed!r}")
    template = Template(
        vertices,
        closed,
        tuple(Fold(_int(start), _int(end)) for start, end in data["folds"]),
        tuple(TemplateFace(tuple(_int(c) for c in f["corners"]), _color(f["color"])) for f in data["faces"]),
        _int(data["next_id"]),
    )
    _check(template)
    return template


def _check(template: Template) -> None:
    """What every template the editor makes is like (a damaged file may say otherwise)."""
    ids = [v.id for v in template.vertices]
    if len(set(ids)) != len(ids) or (ids and template.next_id <= max(ids)):
        raise ValueError("vertex ids aren't distinct and below the next one")
    labels = [v.label for v in template.vertices if v.label is not None]
    if len(set(labels)) != len(labels):
        raise ValueError("two vertices have the same label")
    if not template.closed:
        if template.folds or template.faces:
            raise ValueError("an open loop with folds or faces")
        return
    if len(ids) < 3:
        raise ValueError("a closed loop of fewer than 3 vertices")
    sides = [
        *template.loop_sides(),
        *((f.start, f.end) for f in template.folds),
        *((f.end, f.start) for f in template.folds),
    ]
    for face in template.faces:
        if len(face.corners) < 3 or not set(face.corners) <= set(ids):
            raise ValueError(f"a face with wrong corners: {face.corners}")
    for a, b in sides:
        if sum(face.has_side(a, b) for face in template.faces) != 1:
            raise ValueError(f"the side {a}-{b} isn't on exactly one face")
    if sum(len(face.corners) for face in template.faces) != len(sides):
        raise ValueError("the faces have sides that are neither the loop's nor folds")


def _int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"expected a whole number, got {value!r}")
    return value


def _color(value: object) -> str:
    if not isinstance(value, str) or not COLOR_PATTERN.fullmatch(value):
        raise ValueError(f"expected a colour as #RRGGBB, got {value!r}")
    return value
